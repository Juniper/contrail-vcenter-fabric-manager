import pytest
from pyVmomi import vim
from tests import utils
from vnc_api import vnc_api

from cvfm import models


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
def vmware_dpg_4():
    net_data = {
        "key": "dvportgroup-4",
        "name": "dpg-4",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-2",
        "vlan": 10,
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


@pytest.fixture
def vmware_vm_2(vmware_dpg_4):
    return utils.create_vmware_vm("vm-2", "esxi-1", [vmware_dpg_4])


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


def test_vm_created_no_pis(
    dvs_per_esxi_topology,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_vm_2,
    vmware_dpg_4,
):
    # User creates a DPG (dpg-4) on dvs-2 (dvs-2 is supported on esxi-2,
    # so a VN will be created in VNC)
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_4)
    vmware_controller.handle_update(dpg_created_update)

    created_vn = vnc_test_client.read_vn(models.generate_uuid("dvportgroup-4"))
    assert created_vn is not None

    # User creates a VM (vm-1) with one interface connected to dpg-4
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update)

    # No VPGs are created in VNC, since there are no PIs for esxi-1_dvs-2
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-2"))

    # No VMIs are created in VNC, since there are no VPGs for esxi-1_dvs-2
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-2_dpg-4"))
