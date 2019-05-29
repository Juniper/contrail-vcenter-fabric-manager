import mock
import pytest
from pyVmomi import vim
from tests import utils
from vnc_api import vnc_api

from cvfm import controllers, models


@pytest.fixture
def update_handler(vm_service, vmi_service, vpg_service, dpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )
    vm_reconfigured_handler = controllers.VmReconfiguredHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )
    return controllers.UpdateHandler(
        [vm_updated_handler, vm_reconfigured_handler]
    )


@pytest.fixture
def vm_created_update():
    networks = [
        {
            "key": "dvportgroup-1",
            "name": "dpg-1",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 5,
        },
    ]
    return utils.create_vm_created_update(
        vm_name="vm-1", vm_host_name="esxi-1", vm_networks=networks
    )


@pytest.fixture
def vmware_dpg_1():
    net_data = {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 5,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_dpg_2():
    net_data = {
        "key": "dvportgroup-2",
        "name": "dpg-2",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 6,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_dpg_3():
    net_data = {
        "key": "dvportgroup-3",
        "name": "dpg-3",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-2",
        "vlan": 7,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm(vmware_dpg_1):
    vm = mock.Mock()
    vm.configure_mock(name="vm-1")
    vm.network = [vmware_dpg_1]
    vm.runtime.host.name = "esxi-1"
    return vm


@pytest.fixture
def vm_reconfigured_update(vmware_vm):
    event = mock.Mock(spec=vim.event.VmReconfiguredEvent())
    device = mock.Mock(spec=vim.vm.device.VirtualPCNet32())
    device_spec = mock.Mock(spec=vim.vm.device.VirtualDeviceSpec())
    device_spec.device = device
    device_spec.operation = "add"
    event.configSpec = mock.Mock(spec=vim.vm.ConfigSpec())
    event.configSpec.deviceChange = [device_spec]
    event.vm.vm = vmware_vm
    event.vm.name = "vm-1"
    event.host.host = mock.Mock(vm=[vmware_vm])
    return utils.wrap_into_update_set(event=event)


@pytest.fixture
def fabric_vn_2(vnc_test_client):
    return utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-2", "dvportgroup-2"
    )


def test_existing_dvs(
    minimalistic_topology,
    fabric_vn,
    fabric_vn_2,
    vmware_vm,
    vmware_dpg_1,
    vmware_dpg_2,
    vmware_controller,
    vcenter_api_client,
    vm_created_update,
    vm_reconfigured_update,
    vnc_test_client,
):
    vmware_controller.handle_update(vm_created_update)
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi_1 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg is not None
    assert vnc_vmi_1 is not None

    vmware_vm.network = [vmware_dpg_1, vmware_dpg_2]
    vmware_controller.handle_update(vm_reconfigured_update)

    vnc_vmi_2 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-2")
    )
    assert vnc_vmi_2 is not None
