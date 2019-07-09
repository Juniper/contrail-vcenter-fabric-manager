#!/usr/bin/env python
import logging
import os
import sys

import gevent
from cfgm_common.uve.nodeinfo.ttypes import NodeStatus, NodeStatusUVE
from pysandesh.connection_info import ConnectionState
from cfgm_common.zkclient import ZookeeperClient
from pysandesh.sandesh_base import Sandesh


from cvfm import controllers, services, synchronizers
from cvfm.clients import VCenterAPIClient, VNCAPIClient
from cvfm.database import Database
from cvfm.event_listener import EventListener
from cvfm.monitors import VMwareMonitor
from cvfm.sandesh_handler import SandeshHandler
from cvfm.supervisor import Supervisor
from cvfm.parser import CVFMArgumentParser

gevent.monkey.patch_all()


def build_context(cfg):
    lock = gevent.lock.BoundedSemaphore()
    update_set_queue = gevent.queue.Queue()

    database = Database()
    vcenter_api_client = VCenterAPIClient(cfg["vcenter_config"])
    vnc_api_client = VNCAPIClient(cfg["vnc_config"], cfg.get("auth_config"))

    service_kwargs = {
        "vcenter_api_client": vcenter_api_client,
        "vnc_api_client": vnc_api_client,
        "database": database,
    }
    vm_service = services.VirtualMachineService(**service_kwargs)
    vmi_service = services.VirtualMachineInterfaceService(**service_kwargs)
    dpg_service = services.DistributedPortGroupService(**service_kwargs)
    vpg_service = services.VirtualPortGroupService(**service_kwargs)
    dvs_service = services.DistributedVirtualSwitchService(**service_kwargs)
    pi_service = services.PhysicalInterfaceService(**service_kwargs)

    handler_kwargs = {
        "vm_service": vm_service,
        "vmi_service": vmi_service,
        "dpg_service": dpg_service,
        "vpg_service": vpg_service,
        "pi_service": pi_service,
    }
    vm_updated_handler = controllers.VmUpdatedHandler(**handler_kwargs)
    vm_reconfigured_handler = controllers.VmReconfiguredHandler(
        **handler_kwargs
    )
    vm_removed_handler = controllers.VmRemovedHandler(**handler_kwargs)
    vm_renamed_handler = controllers.VmRenamedHandler(**handler_kwargs)
    vm_host_change_handler = controllers.HostChangeHandler(**handler_kwargs)
    dvportgroup_created_handler = controllers.DVPortgroupCreatedHandler(
        **handler_kwargs
    )
    dvportgroup_reconfigured_handler = controllers.DVPortgroupReconfiguredHandler(
        **handler_kwargs
    )
    dvportgroup_renamed_handler = controllers.DVPortgroupRenamedHandler(
        **handler_kwargs
    )
    dvportgroup_destroyed_handler = controllers.DVPortgroupDestroyedHandler(
        **handler_kwargs
    )

    handlers = [
        vm_updated_handler,
        vm_renamed_handler,
        vm_reconfigured_handler,
        vm_removed_handler,
        vm_host_change_handler,
        dvportgroup_created_handler,
        dvportgroup_reconfigured_handler,
        dvportgroup_renamed_handler,
        dvportgroup_destroyed_handler,
    ]
    update_handler = controllers.UpdateHandler(handlers)

    vm_synchronizer = synchronizers.VirtualMachineSynchronizer(vm_service)
    dpg_synchronizer = synchronizers.DistributedPortGroupSynchronizer(
        dpg_service
    )
    vpg_synchronizer = synchronizers.VirtualPortGroupSynchronizer(
        vm_service, vpg_service, pi_service
    )
    vmi_synchronizer = synchronizers.VirtualMachineInterfaceSynchronizer(
        vm_service, vmi_service
    )
    dvs_synchronizer = synchronizers.DistributedVirtualSwitchSynchronizer(
        dvs_service
    )
    pi_synchronizer = synchronizers.PhysicalInterfaceSynchronizer(pi_service)
    synchronizer = synchronizers.Synchronizer(
        database,
        vm_synchronizer,
        dpg_synchronizer,
        vpg_synchronizer,
        vmi_synchronizer,
        dvs_synchronizer,
        pi_synchronizer,
    )

    vmware_controller = controllers.VmwareController(
        synchronizer, update_handler, lock
    )
    vmware_monitor = VMwareMonitor(vmware_controller, update_set_queue)
    event_listener = EventListener(
        vmware_controller, update_set_queue, vcenter_api_client, database
    )
    supervisor = Supervisor(event_listener, vcenter_api_client)
    zookeeper_client = ZookeeperClient(
        "vcenter-fabric-manager",
        cfg["zookeeper_config"]["zookeeper_servers"],
        cfg["defaults_config"]["host_ip"],
    )
    context = {
        "lock": lock,
        "database": database,
        "vmware_monitor": vmware_monitor,
        "supervisor": supervisor,
        "zookeeper-client": zookeeper_client,
    }
    return context


def run_introspect(cfg, database, lock):
    introspect_config = cfg["introspect_config"]

    sandesh = Sandesh()
    sandesh_handler = SandeshHandler(database, lock)
    sandesh_handler.bind_handlers()
    sandesh.init_generator(
        module="cvfm",
        source=introspect_config["hostname"],
        node_type=introspect_config["node_type_name"],
        instance_id=introspect_config["instance_id"],
        collectors=introspect_config["collectors"],
        client_context="cvfm_context",
        http_port=introspect_config["introspect_port"],
        sandesh_req_uve_pkg_list=["cfgm_common", "cvfm"],
        config=cfg["sandesh_config"],
    )
    sandesh.sandesh_logger().set_logger_params(
        logger=sandesh.logger(),
        enable_local_log=True,
        level=introspect_config["logging_level"],
        file=introspect_config["log_file"],
        enable_syslog=False,
        syslog_facility=None,
    )
    ConnectionState.init(
        sandesh=sandesh,
        hostname=introspect_config["hostname"],
        module_id=introspect_config["name"],
        instance_id=introspect_config["instance_id"],
        conn_status_cb=staticmethod(ConnectionState.get_conn_state_cb),
        uve_type_cls=NodeStatusUVE,
        uve_data_type_cls=NodeStatus,
        table=introspect_config["table"],
    )


def run_vcenter_fabric_manager(supervisor, vmware_monitor):
    greenlets = [
        gevent.spawn(supervisor.supervise),
        gevent.spawn(vmware_monitor.monitor),
    ]
    gevent.joinall(greenlets, raise_error=True)


def main(cfg):
    context = build_context(cfg)
    vmware_monitor = context["vmware_monitor"]
    supervisor = context["supervisor"]
    database = context["database"]
    lock = context["lock"]
    run_introspect(cfg, database, lock)

    zookeeper_client = context["zookeeper-client"]
    logger = logging.getLogger("cvfm")
    logger.info("Waiting to be elected as master...")
    zookeeper_client.master_election(
        "/vcenter-fabric-manager",
        os.getpid(),
        run_vcenter_fabric_manager,
        supervisor,
        vmware_monitor,
    )


if __name__ == "__main__":
    parser = CVFMArgumentParser()
    config = parser.parse_args(sys.argv[1:])
    try:
        main(config)
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        logger = logging.getLogger("cvfm")
        logger.critical("", exc_info=True)
        raise
