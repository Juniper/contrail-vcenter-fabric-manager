import pytest
from vnc_api import vnc_api
from pyVmomi import vim

from tests import utils


@pytest.fixture
def vmware_dpg():
    net_data = {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 5,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm(vmware_dpg):
    return utils.create_vmware_vm("vm-1", "esxi-1", [vmware_dpg])


def test_vm_renamed(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_vm,
    vmware_dpg,
):
    # User creates a DPG (dpg-1)
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)

    # User creates a VM (vm-1)
    vm_created_update = vcenter_api_client.create_vm(vmware_vm)
    vmware_controller.handle_update(vm_created_update)

    # A VPG (esxi-1_dvs-1) and a VMI (esxi-1_dvs-1_dpg-1) should be created
    # in VNC
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

    # User renames vm-1 to vm-1-renamed
    vm_renamed_update = vcenter_api_client.rename_vm(vmware_vm, "vm-1-renamed")
    vmware_controller.handle_update(vm_renamed_update)

    # User removes vm-1-renamed from vCenter
    vm_removed_update = vcenter_api_client.remove_vm(vmware_vm)
    vmware_controller.handle_update(vm_removed_update)

    # esxi-1_dvs-1 and esxi-1_dvs-1_dpg-1 should be deleted from VNC
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(created_vpg.uuid)
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(created_vmi.uuid)
