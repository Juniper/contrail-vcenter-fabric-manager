import mock
import pytest
from pyVmomi import vim
from vnc_api import vnc_api

from cvfm import controllers, models
from tests import utils


@pytest.fixture
def update_handler(vm_service, vmi_service, vpg_service, dpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )
    vm_removed_handler = controllers.VmReconfiguredHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )
    return controllers.UpdateHandler([vm_updated_handler, vm_removed_handler])


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
        {
            "key": "dvportgroup-2",
            "name": "dpg-2",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 6,
        }
    ]
    return utils.create_vm_created_update(
        vm_name="vm-1", vm_host_name="esxi-1", vm_networks=networks
    )


@pytest.fixture
def vmware_dpg():
    dpg = mock.Mock(spec=vim.DistributedVirtualPortgroup)
    dpg.configure_mock(name="dpg-1")
    dpg.key = "dvportgroup-1"
    dpg.config.distributedVirtualSwitch.name = "dvs-1"
    dpg.config.defaultPortConfig.vlan.vlanId = 5
    return dpg


@pytest.fixture
def vmware_vm(vmware_dpg):
    vm = mock.Mock()
    vm.configure_mock(name="vm-1")
    vm.network = [vmware_dpg]
    vm.runtime.host.name = "esxi-1"
    return vm


@pytest.fixture
def vm_reconfigured_update(vmware_vm):
    event = mock.Mock(spec=vim.event.VmReconfiguredEvent())
    device = mock.Mock(spec=vim.vm.device.VirtualPCNet32())
    device_spec = mock.Mock(spec=vim.vm.device.VirtualDeviceSpec())
    device_spec.device = device
    device_spec.operation = 'remove'
    event.configSpec = mock.Mock(spec=vim.vm.ConfigSpec())
    event.configSpec.deviceChange = [device_spec]
    return utils.wrap_into_update_set(event=event)


@pytest.fixture
def fabric_vn_2(vnc_test_client):
    return utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-2", "dvportgroup-2"
    )


def test_last_vm_in_pg(
        minimalistic_topology,
        fabric_vn,
        fabric_vn_2,
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
    vnc_vmi_2 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-2")
    )
    assert vnc_vpg is not None
    assert vnc_vmi_1 is not None
    assert vnc_vmi_2 is not None

    vmware_controller.handle_update(vm_reconfigured_update)

    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi_1 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(
            models.generate_uuid("esxi-1_dvs-1_dpg-2")
        )
    assert vnc_vpg is not None
    assert vnc_vmi_1 is not None
