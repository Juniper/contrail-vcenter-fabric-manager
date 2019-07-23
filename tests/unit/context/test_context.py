import mock
import pytest

from cvfm.context import CVFMContext


@pytest.fixture
def config():
    return {
        "introspect_config": {
            "id": 36,
            "hostname": "cvfm_host",
            "table": "ObjectContrailvCenterFabricManagerNode",
            "instance_id": "0",
            "introspect_port": 9099,
            "name": "contrail-vcenter-fabric-manager",
            "node_type": 6,
            "node_type_name": "Compute",
            "collectors": ["10.10.10.10:8086"],
            "logging_level": "SYS_INFO",
            "log_file": "cvfm.log",
        },
        "sandesh_config": mock.Mock(),
        "vnc_config": {},
        "vcenter_config": {},
        "auth_config": {},
    }


@pytest.fixture()
def database():
    return mock.Mock()


@mock.patch("gevent.lock.BoundedSemaphore")
@mock.patch("cvfm.database.Database")
@mock.patch("cvfm.sandesh_handler.SandeshHandler")
@mock.patch("pysandesh.sandesh_base.Sandesh")
@mock.patch("pysandesh.connection_info.ConnectionState")
@mock.patch("cvfm.context.clients")
@mock.patch("cvfm.context.services")
@mock.patch("cvfm.context.controllers")
@mock.patch("cvfm.context.synchronizers")
@mock.patch("cvfm.context.monitors")
def test_context_build(
    monitors,
    synchronizers,
    controllers,
    services,
    clients,
    conn_state,
    sandesh,
    sandesh_handler,
    database,
    lock,
    config,
):
    introspect_config = config["introspect_config"]

    context = CVFMContext()
    context.build(config)

    assert context.lock == lock()
    assert context.database == database()
    assert context.sandesh == sandesh()
    sandesh_handler.assert_called_once_with(database(), lock())
    assert context.sandesh_handler == sandesh_handler()
    context.sandesh_handler.bind_handlers.assert_called_once()

    sandesh().init_generator.assert_called_once_with(
        **{
            "module": "cvfm",
            "source": introspect_config["hostname"],
            "node_type": introspect_config["node_type_name"],
            "instance_id": introspect_config["instance_id"],
            "collectors": introspect_config["collectors"],
            "client_context": "cvfm_context",
            "http_port": introspect_config["introspect_port"],
            "sandesh_req_uve_pkg_list": ["cfgm_common", "cvfm"],
            "config": config["sandesh_config"],
        }
    )
    sandesh().sandesh_logger().set_logger_params.assert_called_once_with(
        **{
            "logger": sandesh().logger(),
            "enable_local_log": True,
            "level": introspect_config["logging_level"],
            "file": introspect_config["log_file"],
            "enable_syslog": False,
            "syslog_facility": None,
        }
    )
    conn_state.init.assert_called_once_with(
        **{
            "sandesh": sandesh(),
            "hostname": introspect_config["hostname"],
            "module_id": introspect_config["name"],
            "instance_id": introspect_config["instance_id"],
            "conn_status_cb": mock.ANY,
            "uve_type_cls": mock.ANY,
            "uve_data_type_cls": mock.ANY,
            "table": introspect_config["table"],
        }
    )

    service_kwargs = {
        "vcenter_api_client": context.clients["vcenter_api_client"],
        "vnc_api_client": context.clients["vnc_api_client"],
        "database": context.database,
    }
    services.VirtualMachineService.assert_called_once_with(**service_kwargs)
    services.VirtualMachineInterfaceService.assert_called_once_with(
        **service_kwargs
    )
    services.DistributedPortGroupService.assert_called_once_with(
        **service_kwargs
    )
    services.VirtualPortGroupService.assert_called_once_with(**service_kwargs)
    services.DistributedVirtualSwitchService.assert_called_once_with(
        **service_kwargs
    )
    services.PhysicalInterfaceService.assert_called_once_with(**service_kwargs)

    assert context.services == {
        "vm_service": services.VirtualMachineService(),
        "vmi_service": services.VirtualMachineInterfaceService(),
        "dpg_service": services.DistributedPortGroupService(),
        "vpg_service": services.VirtualPortGroupService(),
        "dvs_service": services.DistributedVirtualSwitchService(),
        "pi_service": services.PhysicalInterfaceService(),
    }

    controllers.VmUpdatedHandler.assert_called_once_with(**context.services)
    controllers.VmReconfiguredHandler.assert_called_once_with(
        **context.services
    )
    controllers.VmRemovedHandler.assert_called_once_with(**context.services)
    controllers.VmRenamedHandler.assert_called_once_with(**context.services)
    controllers.HostChangeHandler.assert_called_once_with(**context.services)
    controllers.DVPortgroupCreatedHandler.assert_called_once_with(
        **context.services
    )
    controllers.DVPortgroupReconfiguredHandler.assert_called_once_with(
        **context.services
    )
    controllers.DVPortgroupRenamedHandler.assert_called_once_with(
        **context.services
    )
    controllers.DVPortgroupDestroyedHandler.assert_called_once_with(
        **context.services
    )

    handlers = [
        controllers.VmUpdatedHandler(),
        controllers.VmReconfiguredHandler(),
        controllers.VmRemovedHandler(),
        controllers.VmRenamedHandler(),
        controllers.HostChangeHandler(),
        controllers.DVPortgroupCreatedHandler(),
        controllers.DVPortgroupReconfiguredHandler(),
        controllers.DVPortgroupRenamedHandler(),
        controllers.DVPortgroupDestroyedHandler(),
    ]
    controllers.UpdateHandler.assert_called_once_with(handlers)

    synchronizers.VirtualMachineSynchronizer.assert_called_once_with(
        **context.services
    )
    synchronizers.DistributedPortGroupSynchronizer.assert_called_once_with(
        **context.services
    )
    synchronizers.VirtualPortGroupSynchronizer.assert_called_once_with(
        **context.services
    )
    synchronizers.VirtualMachineInterfaceSynchronizer.assert_called_once_with(
        **context.services
    )
    synchronizers.DistributedVirtualSwitchSynchronizer.assert_called_once_with(
        **context.services
    )
    synchronizers.PhysicalInterfaceSynchronizer.assert_called_once_with(
        **context.services
    )

    synchronizers.CVFMSynchronizer.assert_called_once_with(
        database(), **context.synchronizers
    )
    assert context.synchronizer == synchronizers.CVFMSynchronizer()

    controllers.VmwareController.assert_called_once_with(
        context.synchronizer, context.update_handler, context.lock
    )

    monitors.VMwareMonitor.assert_called_once_with(
        controllers.VmwareController(), clients.VCenterAPIClient()
    )
    assert context.vmware_monitor == monitors.VMwareMonitor()


@mock.patch("cvfm.context.clients")
def test_context_clients(clients, config):
    vcenter_api_client = mock.Mock()
    vnc_api_client = mock.Mock()
    clients.VCenterAPIClient.return_value = vcenter_api_client
    clients.VNCAPIClient.return_value = vnc_api_client

    context = CVFMContext()

    context.build(config)

    clients.VCenterAPIClient.assert_called_once_with(config["vcenter_config"])
    clients.VNCAPIClient.assert_called_once_with(
        config["vnc_config"], config["auth_config"]
    )
    assert context.clients == {
        "vcenter_api_client": vcenter_api_client,
        "vnc_api_client": vnc_api_client,
    }
