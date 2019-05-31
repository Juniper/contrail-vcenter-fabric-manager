import pytest
from vnc_api import vnc_api
from pyVmomi import vim

from cvfm import models
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
def vmware_vm_1(vmware_dpg_1):
    return utils.create_vmware_vm("vm-1", "esxi-1", [vmware_dpg_1])


@pytest.fixture
def vmware_vm_2(vmware_dpg_1):
    return utils.create_vmware_vm("vm-2", "esxi-1", [vmware_dpg_1])


@pytest.fixture
def vmware_vm_3(vmware_dpg_2):
    return utils.create_vmware_vm("vm-3", "esxi-1", [vmware_dpg_2])


@pytest.fixture
def vmware_vm_4(vmware_dpg_1, vmware_dpg_2):
    return utils.create_vmware_vm(
        "vm-4", "esxi-1", [vmware_dpg_1, vmware_dpg_2]
    )


def test_last_vm_from_pg(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_vm_1,
    vmware_dpg_1,
):
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)

    vm_created_update = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update)
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )

    assert vnc_vpg is not None
    assert vnc_vmi is not None

    vm_removed_update = vcenter_api_client.remove_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_removed_update)

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(vnc_vpg.uuid)
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(vnc_vmi.uuid)


def test_vms_remaining_in_pg(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_vm_1,
    vmware_vm_2,
    vmware_dpg_1,
):
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)

    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update_1)
    vm_created_update_2 = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update_2)
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg is not None
    assert vnc_vmi is not None

    vm_removed_update = vcenter_api_client.remove_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_removed_update)

    vpg = vnc_test_client.read_vpg(vnc_vpg.uuid)
    vmi = vnc_test_client.read_vmi(vnc_vmi.uuid)

    assert vpg is not None
    assert vmi is not None


def test_two_vms_two_pgs(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_vm_1,
    vmware_vm_3,
    vmware_dpg_1,
    vmware_dpg_2,
):
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)

    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update_1)
    vm_created_update_2 = vcenter_api_client.create_vm(vmware_vm_3)
    vmware_controller.handle_update(vm_created_update_2)
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

    vm_removed_update = vcenter_api_client.remove_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_removed_update)

    vpg = vnc_test_client.read_vpg(vnc_vpg.uuid)
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(vnc_vmi_1.uuid)
    vmi_2 = vnc_test_client.read_vmi(vnc_vmi_2.uuid)

    assert vpg is not None
    assert vmi_2 is not None


def test_two_pgs_one_empty(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_vm_2,
    vmware_vm_4,
    vmware_dpg_1,
    vmware_dpg_2,
):
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)

    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm_4)
    vmware_controller.handle_update(vm_created_update_1)
    vm_created_update_2 = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update_2)
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

    vm_removed_update = vcenter_api_client.remove_vm(vmware_vm_4)
    vmware_controller.handle_update(vm_removed_update)

    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi_2 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-2"))
    assert vnc_vpg is not None
    assert vnc_vmi_2 is not None
