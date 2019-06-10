import pytest

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
def vmware_vm_1(vmware_dpg):
    return utils.create_vmware_vm("vm-1", "esxi-1", [vmware_dpg])


@pytest.fixture
def vmware_vm_2(vmware_dpg):
    return utils.create_vmware_vm("vm-2", "esxi-2", [vmware_dpg])


def test_dpg_reconfiguration(
    topology_with_two_nodes,
    vnc_test_client,
    vcenter_api_client,
    vmware_controller,
    vmware_dpg,
    vmware_vm_1,
    vmware_vm_2,
):

    # dpg-1 created in dvs-1 with VLAN 5
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)

    # vm-1 created on host esxi-1 with single interface in (dvs-1, dpg-1)
    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update_1)

    # vm-2 created on host esxi-2 with single interface in (dvs-1, dpg-1)
    vm_created_update_2 = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update_2)

    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 2

    created_vmi = vmis["esxi-1_dvs-1_dpg-1"]
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )

    created_vmi = vmis["esxi-2_dvs-1_dpg-1"]
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-2_dvs-1_dpg-1",
        vpg_name="esxi-2_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )

    # dpg-1 VLAN reconfigured from 5 to 15
    dpg_reconfigured_update = vcenter_api_client.reconfigure_dpg(
        vmware_dpg, 15
    )
    vmware_controller.handle_update(dpg_reconfigured_update)

    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 2

    created_vmi = vmis["esxi-1_dvs-1_dpg-1"]
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=15,
    )

    created_vmi = vmis["esxi-2_dvs-1_dpg-1"]
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-2_dvs-1_dpg-1",
        vpg_name="esxi-2_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=15,
    )
