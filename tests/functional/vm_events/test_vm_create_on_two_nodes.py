import pytest
from pyVmomi import vim
from tests import utils

from cvfm import controllers


@pytest.fixture
def update_handler(vmi_service, vpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        None, vmi_service, None, vpg_service
    )
    return controllers.UpdateHandler([vm_updated_handler])


@pytest.fixture
def fabric_vn_1(vnc_test_client):
    utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-1", "dvportgroup-1"
    )


@pytest.fixture
def fabric_vn_2(vnc_test_client):
    utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-2", "dvportgroup-2"
    )


@pytest.fixture
def fabric_vn_3(vnc_test_client):
    utils.create_fabric_network(
        vnc_test_client, "dvs-2_dpg-3", "dvportgroup-3"
    )


@pytest.fixture
def dpg_1():
    return {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 5,
    }


@pytest.fixture
def dpg_2():
    return {
        "key": "dvportgroup-2",
        "name": "dpg-2",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 6,
    }


@pytest.fixture
def dpg_3():
    return {
        "key": "dvportgroup-3",
        "name": "dpg-3",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-2",
        "vlan": 7,
    }


@pytest.fixture
def vm_created_update_1(dpg_1):
    return utils.create_vm_created_update(
        vm_name="VM1", vm_host_name="esxi-1", vm_networks=[dpg_1]
    )


@pytest.fixture
def vm_created_update_2(dpg_1, dpg_3):
    return utils.create_vm_created_update(
        vm_name="VM2", vm_host_name="esxi-2", vm_networks=[dpg_1, dpg_3]
    )


@pytest.fixture
def vm_created_update_3(dpg_1, dpg_3):
    return utils.create_vm_created_update(
        vm_name="VM3", vm_host_name="esxi-1", vm_networks=[dpg_1, dpg_3]
    )


@pytest.fixture
def vm_created_update_4(dpg_2):
    return utils.create_vm_created_update(
        vm_name="VM4", vm_host_name="esxi-1", vm_networks=[dpg_2]
    )


@pytest.fixture
def vm_created_update_5(dpg_2):
    return utils.create_vm_created_update(
        vm_name="VM5", vm_host_name="esxi-2", vm_networks=[dpg_2]
    )


def test_vm_created_on_two_nodes(
    topology_with_spine_switch,
    vnc_test_client,
    vmware_controller,
    vm_created_update_1,
    vm_created_update_2,
    vm_created_update_3,
    vm_created_update_4,
    vm_created_update_5,
    fabric_vn_1,
    fabric_vn_2,
    fabric_vn_3,
):
    # VM1 created on host esxi-1 with single interface in (dvs-1, dpg-1)
    vmware_controller.handle_update(vm_created_update_1)
    # VM2 created on host esxi-2 with two interfaces in (dvs-1, dpg-1) and (dvs-2, dpg-3)
    vmware_controller.handle_update(vm_created_update_2)
    # VM3 created on host esxi-1 with two interfaces in (dvs-1, dpg-1) and (dvs-2, dpg-3)
    vmware_controller.handle_update(vm_created_update_3)
    # VM4 created on host esxi-1 with one interface in (dvs-1, dpg-2)
    vmware_controller.handle_update(vm_created_update_4)
    # VM5 created on host esxi-2 with one interface in (dvs-1, dpg-2)
    vmware_controller.handle_update(vm_created_update_5)

    vpgs = vnc_test_client.read_all_vpgs()
    assert len(vpgs) == 4

    created_vpg = vpgs["esxi-1_dvs-1"]
    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg,
        vpg_name="esxi-1_dvs-1",
        pi_names=["xe-0/0/1", "xe-0/0/5"],
        vmi_names=["esxi-1_dvs-1_dpg-1", "esxi-1_dvs-1_dpg-2"],
    )

    created_vpg = vpgs["esxi-1_dvs-2"]
    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg,
        vpg_name="esxi-1_dvs-2",
        pi_names=["xe-0/0/2", "xe-0/0/6"],
        vmi_names=["esxi-1_dvs-2_dpg-3"],
    )

    created_vpg = vpgs["esxi-2_dvs-1"]
    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg,
        vpg_name="esxi-2_dvs-1",
        pi_names=["xe-0/0/3", "xe-0/0/7"],
        vmi_names=["esxi-2_dvs-1_dpg-1", "esxi-2_dvs-1_dpg-2"],
    )

    created_vpg = vpgs["esxi-2_dvs-2"]
    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg,
        vpg_name="esxi-2_dvs-2",
        pi_names=["xe-0/0/4", "xe-0/0/8"],
        vmi_names=["esxi-2_dvs-2_dpg-3"],
    )

    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 6

    for vmi in vmis.values():
        if "dpg-1" in vmi.name:
            expected_vlan = 5
        elif "dpg-2" in vmi.name:
            expected_vlan = 6
        elif "dpg-3" in vmi.name:
            expected_vlan = 7
        utils.verify_vnc_vmi(vnc_vmi=vmi, vlan=expected_vlan)
