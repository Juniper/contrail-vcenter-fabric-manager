import pytest
from pyVmomi import vim

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
def fabric_vn_2(vnc_test_client):
    return utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-2", "dvportgroup-2"
    )


def test_vm_disconnected(
    minimalistic_topology,
    fabric_vn,
    fabric_vn_2,
    vmware_controller,
    vcenter_api_client,
    vm_created_update,
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
