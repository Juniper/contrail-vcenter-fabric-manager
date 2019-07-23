import gevent

from cfgm_common.uve.nodeinfo.ttypes import NodeStatus, NodeStatusUVE
from pysandesh import sandesh_base, connection_info

from cvfm import (
    controllers,
    services,
    synchronizers,
    sandesh_handler,
    clients,
    monitors,
)
from cvfm import database as db


class CVFMContext(object):
    def __init__(self, config):
        self.config = config
        self.lock = None
        self.database = None
        self.services = {}
        self.synchronizers = {}
        self.synchronizer = None
        self.update_handler = None
        self.vmware_monitor = None

    def build(self):
        self.lock = gevent.lock.BoundedSemaphore()
        self.database = db.Database()
        self._build_sandesh()
        self._build_clients()
        self._build_services()
        self._build_handlers()
        self._build_synchronizers()
        self._build_monitor()

    def _build_monitor(self):
        vmware_controller = controllers.VMwareController(
            self.synchronizer, self.update_handler, self.lock
        )
        self.vmware_monitor = monitors.VMwareMonitor(
            vmware_controller, self.clients["vcenter_api_client"]
        )

    def _build_sandesh(self):
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
        sandesh.sandesh_logger().set_logger_params(
            logger=sandesh.logger(),
            enable_local_log=True,
            level=introspect_config["logging_level"],
            file=introspect_config["log_file"],
            enable_syslog=False,
            syslog_facility=None,
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
        self.clients = {
            "vcenter_api_client": clients.VCenterAPIClient(vcenter_config),
            "vnc_api_client": clients.VNCAPIClient(vnc_config, auth_config),
        }
