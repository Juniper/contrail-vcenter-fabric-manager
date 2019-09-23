import collections

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
        "rabbit_config": {},
        "auth_config": {},
    }


@pytest.fixture
def patched_libs(
    monitors_lib,
    controllers_lib,
    synchronizers_lib,
    services_lib,
    clients_lib,
    rabbit_lib,
    sandesh,
    sandesh_handler,
    connection_state,
):
    return {
        "monitors_lib": monitors_lib,
        "controllers_lib": controllers_lib,
        "synchronizers_lib": synchronizers_lib,
        "services_lib": services_lib,
        "clients_lib": clients_lib,
        "rabbit_lib": rabbit_lib,
        "sandesh": sandesh,
        "sandesh_handler": sandesh_handler,
        "connection_state": connection_state,
    }


@pytest.fixture
def clients():
    return {
        "vcenter_api_client": mock.Mock(),
        "vnc_api_client": mock.Mock(),
        "vnc_rabbit_client": mock.Mock(),
    }


@pytest.fixture
def clients_lib(clients):
    with mock.patch("cvfm.context.clients") as c_mock:
        c_mock.VCenterAPIClient.return_value = clients["vcenter_api_client"]
        c_mock.VNCAPIClient.return_value = clients["vnc_api_client"]
        yield c_mock


@pytest.fixture
def rabbit_lib(clients):
    with mock.patch("cvfm.context.vnc_rabbit") as r_mock:
        r_mock.VNCRabbitClient.return_value = clients["vnc_rabbit_client"]
        yield r_mock


@pytest.fixture
def services():
    return {
        "vm_service": mock.Mock(),
        "vmi_service": mock.Mock(),
        "dpg_service": mock.Mock(),
        "vpg_service": mock.Mock(),
        "dvs_service": mock.Mock(),
        "pi_service": mock.Mock(),
    }


@pytest.fixture
def services_lib(services):
    with mock.patch("cvfm.context.services") as s_mock:
        s_mock.VirtualMachineService.return_value = services["vm_service"]
        s_mock.VirtualMachineInterfaceService.return_value = services[
            "vmi_service"
        ]
        s_mock.DistributedPortGroupService.return_value = services[
            "dpg_service"
        ]
        s_mock.VirtualPortGroupService.return_value = services["vpg_service"]
        s_mock.DistributedVirtualSwitchService.return_value = services[
            "dvs_service"
        ]
        s_mock.PhysicalInterfaceService.return_value = services["pi_service"]
        yield s_mock


@pytest.fixture
def synchronizers():
    return {
        "vm_synchronizer": mock.Mock(),
        "dpg_synchronizer": mock.Mock(),
        "vpg_synchronizer": mock.Mock(),
        "vmi_synchronizer": mock.Mock(),
        "dvs_synchronizer": mock.Mock(),
        "pi_synchronizer": mock.Mock(),
    }


@pytest.fixture
def cvfm_synchronizer():
    return mock.Mock()


@pytest.fixture
def synchronizers_lib(synchronizers, cvfm_synchronizer):
    with mock.patch("cvfm.context.synchronizers") as s_mock:

        s_mock.VirtualMachineSynchronizer.return_value = synchronizers[
            "vm_synchronizer"
        ]
        s_mock.DistributedPortGroupSynchronizer.return_value = synchronizers[
            "dpg_synchronizer"
        ]
        s_mock.VirtualPortGroupSynchronizer.return_value = synchronizers[
            "vpg_synchronizer"
        ]
        s_mock.VirtualMachineInterfaceSynchronizer.return_value = synchronizers[
            "vmi_synchronizer"
        ]
        s_mock.DistributedVirtualSwitchSynchronizer.return_value = synchronizers[
            "dvs_synchronizer"
        ]
        s_mock.PhysicalInterfaceSynchronizer.return_value = synchronizers[
            "pi_synchronizer"
        ]
        s_mock.CVFMSynchronizer.return_value = cvfm_synchronizer
        yield s_mock


@pytest.fixture
def handlers():
    return collections.OrderedDict(
        [
            ("vm_updated_handler", mock.Mock()),
            ("vm_reconfigured_handler", mock.Mock()),
            ("vm_removed_handler", mock.Mock()),
            ("vm_renamed_handler", mock.Mock()),
            ("host_change_handler", mock.Mock()),
            ("dpg_created_handler", mock.Mock()),
            ("dpg_reconfigured_handler", mock.Mock()),
            ("dpg_renamed_handler", mock.Mock()),
            ("dpg_destroyed_handler", mock.Mock()),
        ]
    )


@pytest.fixture
def update_handler():
    return mock.Mock()


@pytest.fixture
def controller():
    return mock.Mock()


@pytest.fixture
def controllers_lib(handlers, update_handler, controller):
    with mock.patch("cvfm.context.controllers") as c_mock:
        c_mock.VmUpdatedHandler.return_value = handlers["vm_updated_handler"]
        c_mock.VmReconfiguredHandler.return_value = handlers[
            "vm_reconfigured_handler"
        ]
        c_mock.VmRemovedHandler.return_value = handlers["vm_removed_handler"]
        c_mock.VmRenamedHandler.return_value = handlers["vm_renamed_handler"]
        c_mock.HostChangeHandler.return_value = handlers["host_change_handler"]
        c_mock.DVPortgroupCreatedHandler.return_value = handlers[
            "dpg_created_handler"
        ]
        c_mock.DVPortgroupReconfiguredHandler.return_value = handlers[
            "dpg_reconfigured_handler"
        ]
        c_mock.DVPortgroupRenamedHandler.return_value = handlers[
            "dpg_renamed_handler"
        ]
        c_mock.DVPortgroupDestroyedHandler.return_value = handlers[
            "dpg_destroyed_handler"
        ]
        c_mock.UpdateHandler.return_value = update_handler
        c_mock.VMwareController.return_value = controller
        yield c_mock


@pytest.fixture
def monitors():
    return {"vmware_monitor": mock.Mock(), "vnc_monitor": mock.Mock()}


@pytest.fixture
def monitors_lib(monitors):
    with mock.patch("cvfm.context.monitors") as m_lib:
        m_lib.VMwareMonitor.return_value = monitors["vmware_monitor"]
        m_lib.VNCMonitor.return_value = monitors["vnc_monitor"]
        yield m_lib


@pytest.fixture
def sandesh():
    s = mock.Mock()
    with mock.patch("cvfm.context.sandesh_base") as snd_base:
        snd_base.Sandesh.return_value = s
        yield s


@pytest.fixture
def sandesh_handler():
    handler = mock.Mock()
    with mock.patch("cvfm.context.sandesh_handler") as sh_mock:
        sh_mock.SandeshHandler.return_value = handler
        yield handler


@pytest.fixture
def connection_state():
    conn_state = mock.Mock()
    with mock.patch("cvfm.context.connection_info") as conn_info:
        conn_info.ConnectionState = conn_state
        yield conn_state


def test_context_monitors(
    monitors, controller, clients, update_handler, patched_libs, config
):
    context = CVFMContext(config)
    context.build()

    controllers_lib = patched_libs["controllers_lib"]
    controllers_lib.VMwareController.assert_called_once_with(
        context.synchronizer, update_handler, context.lock
    )
    monitors_lib = patched_libs["monitors_lib"]
    monitors_lib.VMwareMonitor.assert_called_once_with(
        controller, clients["vcenter_api_client"]
    )
    monitors_lib.VNCMonitor.assert_called_once_with(
        controller, clients["vnc_rabbit_client"]
    )
    assert context.monitors == {
        "vmware_monitor": monitors["vmware_monitor"],
        "vnc_monitor": monitors["vnc_monitor"],
    }


def test_context_clients(clients, patched_libs, config):
    context = CVFMContext(config)
    context.build()

    clients_lib = patched_libs["clients_lib"]
    clients_lib.VCenterAPIClient.assert_called_once_with(
        config["vcenter_config"]
    )
    clients_lib.VNCAPIClient.assert_called_once_with(
        config["vnc_config"], config["auth_config"]
    )

    rabbit_lib = patched_libs["rabbit_lib"]
    rabbit_lib.VNCRabbitClient.assert_called_once_with(config["rabbit_config"])
    assert context.clients == {
        "vcenter_api_client": clients["vcenter_api_client"],
        "vnc_api_client": clients["vnc_api_client"],
        "vnc_rabbit_client": clients["vnc_rabbit_client"],
    }


def test_context_services(services, patched_libs, config):
    context = CVFMContext(config)
    context.build()

    s_lib = patched_libs["services_lib"]
    s_kwargs = {
        "vcenter_api_client": context.clients["vcenter_api_client"],
        "vnc_api_client": context.clients["vnc_api_client"],
        "database": context.database,
    }
    s_lib.VirtualMachineService.assert_called_once_with(**s_kwargs)
    s_lib.VirtualMachineInterfaceService.assert_called_once_with(**s_kwargs)
    s_lib.DistributedPortGroupService.assert_called_once_with(**s_kwargs)
    s_lib.VirtualPortGroupService.assert_called_once_with(**s_kwargs)
    s_lib.DistributedVirtualSwitchService.assert_called_once_with(**s_kwargs)
    s_lib.PhysicalInterfaceService.assert_called_once_with(**s_kwargs)

    assert context.services == services


def test_context_synchronizers(
    synchronizers, cvfm_synchronizer, services, patched_libs, config
):
    context = CVFMContext(config)
    context.build()

    s_lib = patched_libs["synchronizers_lib"]
    s_lib.VirtualMachineSynchronizer.assert_called_once_with(**services)
    s_lib.DistributedPortGroupSynchronizer.assert_called_once_with(**services)
    s_lib.VirtualPortGroupSynchronizer.assert_called_once_with(**services)
    s_lib.VirtualMachineInterfaceSynchronizer.assert_called_once_with(
        **services
    )
    s_lib.DistributedVirtualSwitchSynchronizer.assert_called_once_with(
        **services
    )
    s_lib.PhysicalInterfaceSynchronizer.assert_called_once_with(**services)

    s_lib.CVFMSynchronizer.assert_called_once_with(
        context.database, **synchronizers
    )
    assert context.synchronizer == cvfm_synchronizer


def test_context_handlers(handlers, services, patched_libs, config):
    context = CVFMContext(config)
    context.build()

    c_lib = patched_libs["controllers_lib"]
    c_lib.VmUpdatedHandler.assert_called_once_with(**services)
    c_lib.VmReconfiguredHandler.assert_called_once_with(**services)
    c_lib.VmRemovedHandler.assert_called_once_with(**services)
    c_lib.VmRenamedHandler.assert_called_once_with(**services)
    c_lib.HostChangeHandler.assert_called_once_with(**services)
    c_lib.DVPortgroupCreatedHandler.assert_called_once_with(**services)
    c_lib.DVPortgroupReconfiguredHandler.assert_called_once_with(**services)
    c_lib.DVPortgroupRenamedHandler.assert_called_once_with(**services)
    c_lib.DVPortgroupDestroyedHandler.assert_called_once_with(**services)

    c_lib.UpdateHandler.assert_called_once_with(list(handlers.values()))


def test_run_sandesh(
    sandesh, sandesh_handler, connection_state, patched_libs, config
):
    context = CVFMContext(config)
    context.build()

    context.run_sandesh()

    sandesh_handler.bind_handlers.assert_called_once()

    introspect_config = config["introspect_config"]
    sandesh.init_generator.assert_called_once_with(
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

    connection_state.init.assert_called_once_with(
        sandesh=sandesh,
        hostname=introspect_config["hostname"],
        module_id=introspect_config["name"],
        instance_id=introspect_config["instance_id"],
        conn_status_cb=mock.ANY,
        uve_type_cls=mock.ANY,
        uve_data_type_cls=mock.ANY,
        table=introspect_config["table"],
    )


def test_context_start(monitors, patched_libs, config):
    context = CVFMContext(config)
    context.build()

    context.start_vmware_monitor()
    context.start_vnc_monitor()

    monitors["vmware_monitor"].start.assert_called_once()
    monitors["vnc_monitor"].start.assert_called_once()
