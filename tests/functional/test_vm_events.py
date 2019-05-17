import pytest
from pyVmomi import vim
from tests import utils
from vnc_api.vnc_api import VirtualNetwork

from cvfm import controllers, models


@pytest.fixture
def update_handler(vmi_service, vpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        None, vmi_service, None, vpg_service
    )
    return controllers.UpdateHandler([vm_updated_handler])


@pytest.fixture
def fabric_vn(vnc_test_client):
    project = vnc_test_client.vnc_lib.project_read(
        ["default-domain", vnc_test_client.project_name]
    )
    fab_vn = VirtualNetwork(name="dvs-1_dpg-1", parent_obj=project)
    fab_vn.set_uuid(models.generate_uuid("dvportgroup-1"))
    vnc_test_client.vnc_lib.virtual_network_create(fab_vn)


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
            "vlan": 0
        },
        {
            "key": "dvportgroup-3",
            "name": "dpg-3",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 8
        }
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

    vmi_list = vnc_test_client.vnc_lib.virtual_machine_interfaces_list()[
        "virtual-machine-interfaces"
    ]
    assert len(vmi_list) == 1
    vpg_list = vnc_test_client.vnc_lib.virtual_port_groups_list()[
        "virtual-port-groups"
    ]
    assert len(vpg_list) == 1

    created_vpg = vnc_test_client.vnc_lib.virtual_port_group_read(
        id=models.generate_uuid("esxi-1_dvs-1")
    )
    created_vmi = vnc_test_client.vnc_lib.virtual_machine_interface_read(
        id=models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )

    assert created_vpg is not None
    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg,
        vpg_name="esxi-1_dvs-1",
        pi_names=["xe-0/0/0"],
        vmi_names=["esxi-1_dvs-1_dpg-1"],
    )

    assert created_vmi is not None
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )
