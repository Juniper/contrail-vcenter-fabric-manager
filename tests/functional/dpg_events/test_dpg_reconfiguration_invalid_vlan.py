import pytest

from tests import utils
from pyVmomi import vim
from vnc_api import vnc_api

from cvfm import models


@pytest.fixture
def vmware_dpg_invalid_vlan():
    net_data = {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 0,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_dpg_valid_vlan():
    net_data = {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 5,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm_1_invalid_dpg(vmware_dpg_invalid_vlan):
    return utils.create_vmware_vm("vm-1", "esxi-1", [vmware_dpg_invalid_vlan])


@pytest.fixture
def vmware_vm_2_invalid_dpg(vmware_dpg_invalid_vlan):
    return utils.create_vmware_vm("vm-2", "esxi-2", [vmware_dpg_invalid_vlan])


@pytest.fixture
def vmware_vm_1_valid_dpg(vmware_dpg_valid_vlan):
    return utils.create_vmware_vm("vm-1", "esxi-1", [vmware_dpg_valid_vlan])


@pytest.fixture
def vmware_vm_2_valid_dpg(vmware_dpg_valid_vlan):
    return utils.create_vmware_vm("vm-2", "esxi-2", [vmware_dpg_valid_vlan])


def test_dpg_reconfiguration_from_invalid_vlan(
    topology_with_two_nodes,
    vnc_test_client,
    vcenter_api_client,
    vmware_controller,
    vmware_dpg_invalid_vlan,
    vmware_vm_1_invalid_dpg,
    vmware_vm_2_invalid_dpg,
):
    # dpg-1 created in dvs-1 with invalid VLAN 0
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_invalid_vlan)
    vmware_controller.handle_update(dpg_created_update)

    # vm-1 created on host esxi-1 with single interface in (dvs-1, dpg-1)
    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm_1_invalid_dpg)
    vmware_controller.handle_update(vm_created_update_1)

    # vm-2 created on host esxi-2 with single interface in (dvs-1, dpg-1)
    vm_created_update_2 = vcenter_api_client.create_vm(vmware_vm_2_invalid_dpg)
    vmware_controller.handle_update(vm_created_update_2)

    # No created objects in VNC API for invalid DPG
    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 0

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vn(models.generate_uuid("dvportgroup-1"))

    # dpg-1 VLAN reconfigured from 0 to 5
    dpg_reconfigured_update = vcenter_api_client.reconfigure_dpg(
        vmware_dpg_invalid_vlan, 5
    )
    vmware_controller.handle_update(dpg_reconfigured_update)

    vnc_vn = vnc_test_client.read_vn(models.generate_uuid("dvportgroup-1"))
    assert vnc_vn.name == "dvs-1_dpg-1"

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


def test_dpg_reconfiguration_to_invalid_vlan(
    topology_with_two_nodes,
    vnc_test_client,
    vcenter_api_client,
    vmware_controller,
    vmware_dpg_valid_vlan,
    vmware_vm_1_valid_dpg,
    vmware_vm_2_valid_dpg,
):
    # dpg-1 created in dvs-1 with invalid VLAN 0
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_valid_vlan)
    vmware_controller.handle_update(dpg_created_update)

    # vm-1 created on host esxi-1 with single interface in (dvs-1, dpg-1)
    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm_1_valid_dpg)
    vmware_controller.handle_update(vm_created_update_1)

    # vm-2 created on host esxi-2 with single interface in (dvs-1, dpg-1)
    vm_created_update_2 = vcenter_api_client.create_vm(vmware_vm_2_valid_dpg)
    vmware_controller.handle_update(vm_created_update_2)

    vnc_vn = vnc_test_client.read_vn(models.generate_uuid("dvportgroup-1"))
    assert vnc_vn.name == "dvs-1_dpg-1"

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

    # dpg-1 VLAN reconfigured from 5 to 0
    dpg_reconfigured_update = vcenter_api_client.reconfigure_dpg(
        vmware_dpg_valid_vlan, 0
    )
    vmware_controller.handle_update(dpg_reconfigured_update)

    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 0

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vn(models.generate_uuid("dvportgroup-1"))
