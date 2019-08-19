import pytest
from pyVmomi import vim
from tests import utils


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
def vmware_vm_1(vmware_dpg_1):
    return utils.create_vmware_vm("vm-1", "esxi-1", [vmware_dpg_1])


@pytest.fixture
def vmware_vm_2(vmware_dpg_1, vmware_dpg_3):
    return utils.create_vmware_vm(
        "vm-2", "esxi-2", [vmware_dpg_1, vmware_dpg_3]
    )


@pytest.fixture
def vmware_vm_3(vmware_dpg_1, vmware_dpg_3):
    return utils.create_vmware_vm(
        "vm-3", "esxi-1", [vmware_dpg_1, vmware_dpg_3]
    )


@pytest.fixture
def vmware_vm_4(vmware_dpg_2):
    return utils.create_vmware_vm("vm-4", "esxi-1", [vmware_dpg_2])


@pytest.fixture
def vmware_vm_5(vmware_dpg_2):
    return utils.create_vmware_vm("vm-5", "esxi-2", [vmware_dpg_2])


def test_vm_created_on_two_nodes(
    topology_with_spine_switch,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_vm_1,
    vmware_vm_2,
    vmware_vm_3,
    vmware_vm_4,
    vmware_vm_5,
    vmware_dpg_1,
    vmware_dpg_2,
    vmware_dpg_3,
):
    # dpg-1 created on dvs-1
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)
    # dpg-2 created on dvs-1
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)
    # dpg-3 created on dvs-2
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_3)
    vmware_controller.handle_update(dpg_created_update)

    # vm-1 created on host esxi-1 with single interface in (dvs-1, dpg-1)
    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update_1)

    # vm-2 created on host esxi-2 with two interfaces in (dvs-1, dpg-1) and (
    # dvs-2, dpg-3)
    vm_created_update_2 = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update_2)

    # vm-3 created on host esxi-1 with two interfaces in (dvs-1, dpg-1) and (
    # dvs-2, dpg-3)
    vm_created_update_3 = vcenter_api_client.create_vm(vmware_vm_3)
    vmware_controller.handle_update(vm_created_update_3)

    # VM4 created on host esxi-1 with one interface in (dvs-1, dpg-2)
    vm_created_update_4 = vcenter_api_client.create_vm(vmware_vm_4)
    vmware_controller.handle_update(vm_created_update_4)

    # VM5 created on host esxi-2 with one interface in (dvs-1, dpg-2)
    vm_created_update_5 = vcenter_api_client.create_vm(vmware_vm_5)
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

    for vmi in list(vmis.values()):
        if "dpg-1" in vmi.name:
            expected_vlan = 5
        elif "dpg-2" in vmi.name:
            expected_vlan = 6
        elif "dpg-3" in vmi.name:
            expected_vlan = 7
        utils.verify_vnc_vmi(vnc_vmi=vmi, vlan=expected_vlan)
