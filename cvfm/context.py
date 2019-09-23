from builtins import object
import logging
import sys

import gevent
from cfgm_common import zkclient
from cfgm_common.uve.nodeinfo.ttypes import NodeStatus, NodeStatusUVE
from pysandesh import connection_info, sandesh_base, sandesh_logger

from cvfm.clients import rabbit as vnc_rabbit
from cvfm import (
    clients,
    controllers,
    services,
    synchronizers,
    sandesh_handler,
    monitors,
)
from cvfm import database as db

logger = logging.getLogger("cvfm")


def zookeeper_connection_lost():
    logger.error("Connection to Zookeeper lost.")
    sys.exit(1)


class CVFMContext(object):
    def __init__(self, config):
        self.config = config
        self.lock = None
        self.database = None
        self.services = {}
        self.synchronizers = {}
        self.monitors = {}
        self.synchronizer = None
        self.update_handler = None

    def build(self):
        self.lock = gevent.lock.BoundedSemaphore()
        self.database = db.Database()
        self._build_clients()
        self._build_services()
        self._build_handlers()
        self._build_synchronizers()
        self._build_monitors()

    def start_vmware_monitor(self):
        self.monitors["vmware_monitor"].start()

    def start_vnc_monitor(self):
        self.monitors["vnc_monitor"].start()

    def run_sandesh(self):
        introspect_config = self.config["introspect_config"]
        sandesh = sandesh_base.Sandesh()
        s_handler = sandesh_handler.SandeshHandler(self.database, self.lock)
        s_handler.bind_handlers()
        sandesh.init_generator(
            module="cvfm",
            source=introspect_config["hostname"],
            node_type=introspect_config["node_type_name"],
            instance_id=introspect_config["instance_id"],
            collectors=introspect_config["collectors"],
            client_context="cvfm_context",
            http_port=introspect_config["introspect_port"],
            sandesh_req_uve_pkg_list=["cfgm_common", "cvfm"],
            config=self.config["sandesh_config"],
        )
        connection_info.ConnectionState.init(
            sandesh=sandesh,
            hostname=introspect_config["hostname"],
            module_id=introspect_config["name"],
            instance_id=introspect_config["instance_id"],
            conn_status_cb=staticmethod(
                connection_info.ConnectionState.get_conn_state_cb
            ),
            uve_type_cls=NodeStatusUVE,
            uve_data_type_cls=NodeStatus,
            table=introspect_config["table"],
        )

    def _build_monitors(self):
        vmware_controller = controllers.VMwareController(
            self.synchronizer, self.update_handler, self.lock
        )
        self.monitors["vmware_monitor"] = monitors.VMwareMonitor(
            vmware_controller, self.clients["vcenter_api_client"]
        )
        self.monitors["vnc_monitor"] = monitors.VNCMonitor(
            vmware_controller, self.clients["vnc_rabbit_client"]
        )

    def _build_handlers(self):
        handlers = [
            controllers.VmUpdatedHandler(**self.services),
            controllers.VmReconfiguredHandler(**self.services),
            controllers.VmRemovedHandler(**self.services),
            controllers.VmRenamedHandler(**self.services),
            controllers.HostChangeHandler(**self.services),
            controllers.DVPortgroupCreatedHandler(**self.services),
            controllers.DVPortgroupReconfiguredHandler(**self.services),
            controllers.DVPortgroupRenamedHandler(**self.services),
            controllers.DVPortgroupDestroyedHandler(**self.services),
        ]
        self.update_handler = controllers.UpdateHandler(handlers)

    def _build_services(self):
        service_kwargs = {
            "vcenter_api_client": self.clients["vcenter_api_client"],
            "vnc_api_client": self.clients["vnc_api_client"],
            "database": self.database,
        }
        self.services = {
            "vm_service": services.VirtualMachineService(**service_kwargs),
            "vmi_service": services.VirtualMachineInterfaceService(
                **service_kwargs
            ),
            "dpg_service": services.DistributedPortGroupService(
                **service_kwargs
            ),
            "vpg_service": services.VirtualPortGroupService(**service_kwargs),
            "dvs_service": services.DistributedVirtualSwitchService(
                **service_kwargs
            ),
            "pi_service": services.PhysicalInterfaceService(**service_kwargs),
        }

    def _build_synchronizers(self):
        self.synchronizers = {
            "vm_synchronizer": synchronizers.VirtualMachineSynchronizer(
                **self.services
            ),
            "dpg_synchronizer": synchronizers.DistributedPortGroupSynchronizer(
                **self.services
            ),
            "vpg_synchronizer": synchronizers.VirtualPortGroupSynchronizer(
                **self.services
            ),
            "vmi_synchronizer": synchronizers.VirtualMachineInterfaceSynchronizer(
                **self.services
            ),
            "dvs_synchronizer": synchronizers.DistributedVirtualSwitchSynchronizer(
                **self.services
            ),
            "pi_synchronizer": synchronizers.PhysicalInterfaceSynchronizer(
                **self.services
            ),
        }
        self.synchronizer = synchronizers.CVFMSynchronizer(
            self.database, **self.synchronizers
        )

    def _build_clients(self):
        vcenter_config = self.config["vcenter_config"]
        vnc_config = self.config["vnc_config"]
        auth_config = self.config.get("auth_config")
        rabbit_config = self.config["rabbit_config"]
        self.clients = {
            "vcenter_api_client": clients.VCenterAPIClient(vcenter_config),
            "vnc_api_client": clients.VNCAPIClient(vnc_config, auth_config),
            "vnc_rabbit_client": vnc_rabbit.VNCRabbitClient(rabbit_config),
        }

    def configure_logger(self):
        introspect_config = self.config["introspect_config"]
        s_logger = sandesh_logger.SandeshLogger("cvfm")
        sandesh_logger.SandeshLogger.set_logger_params(
            logger=s_logger.logger(),
            enable_local_log=True,
            level=introspect_config["logging_level"],
            file=introspect_config["log_file"],
            enable_syslog=False,
            syslog_facility=None,
        )

    def build_zookeeper_client(self):
        logger.info("Connecting to zookeeper...")
        # Below, we use a different module name than for SandeshLogger,
        # since we want to keep zk logs in a separate log file
        zookeeper_client = zkclient.ZookeeperClient(
            "vcenter-fabric-manager",
            self.config["zookeeper_config"]["zookeeper_servers"],
            self.config["defaults_config"]["host_ip"],
        )
        zookeeper_client.set_lost_cb(zookeeper_connection_lost)
        return zookeeper_client
