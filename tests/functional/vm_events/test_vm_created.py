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
        "vlan": 0,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_dpg_3():
    net_data = {
        "key": "dvportgroup-3",
        "name": "dpg-3",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 8,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_net_1():
    net_data = {"key": "network-1", "name": "network-1", "type": vim.Network}
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm(vmware_dpg_1, vmware_dpg_2, vmware_dpg_3, vmware_net_1):
    networks = [vmware_dpg_1, vmware_dpg_2, vmware_dpg_3, vmware_net_1]
    return utils.create_vmware_vm("vm-1", "esxi-1", networks)


def test_vm_created(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_vm,
    vmware_dpg_1,
):
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)

    vm_created_update = vcenter_api_client.create_vm(vmware_vm)
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
