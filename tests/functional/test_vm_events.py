import pytest
from pyVmomi import vim
from tests import utils

from cvfm import controllers


@pytest.fixture
def update_handler(vm_service, vmi_service, vpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        vm_service, vmi_service, None, vpg_service
    )
    return controllers.UpdateHandler([vm_updated_handler])


@pytest.fixture
def fabric_vn(vnc_test_client):
    utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-1", "dvportgroup-1"
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
        {"key": "network-1", "name": "network-1", "type": vim.Network},
        {
            "key": "dvportgroup-2",
            "name": "dpg-2",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 0,
        },
        {
            "key": "dvportgroup-3",
            "name": "dpg-3",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 8,
        },
    ]
    return utils.create_vm_created_update(
        vm_name="VM1", vm_host_name="esxi-1", vm_networks=networks
    )


def test_vm_created(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vm_created_update,
    fabric_vn,
):
    vmware_controller.handle_update(vm_created_update)

    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 1
    vpgs = vnc_test_client.read_all_vpgs()
    assert len(vpgs) == 1

    created_vpg = vpgs["esxi-1_dvs-1"]
    created_vmi = vmis["esxi-1_dvs-1_dpg-1"]

    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg,
        vpg_name="esxi-1_dvs-1",
        pi_names=["xe-0/0/0"],
        vmi_names=["esxi-1_dvs-1_dpg-1"],
    )

    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )
