import pytest
from pyVmomi import vim
from vnc_api import vnc_api
from tests import utils

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
        "vlan": 6,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm_1(vmware_dpg_1):
    networks = [vmware_dpg_1]
    return utils.create_vmware_vm("vMotion-vm-1", "esxi-1", networks)


@pytest.fixture
def vmware_vm_2(vmware_dpg_1):
    networks = [vmware_dpg_1]
    return utils.create_vmware_vm("vMotion-vm-2", "esxi-1", networks)


@pytest.fixture
def vmware_vm_3(vmware_dpg_1, vmware_dpg_2):
    networks = [vmware_dpg_1, vmware_dpg_2]
    return utils.create_vmware_vm("vMotion-vm-3", "esxi-1", networks)


@pytest.fixture
def vmware_vm_4(vmware_dpg_2):
    networks = [vmware_dpg_2]
    return utils.create_vmware_vm("local-storage-vm-1", "esxi-1", networks)


@pytest.fixture
def vmware_vm_5(vmware_dpg_2):
    networks = [vmware_dpg_2]
    return utils.create_vmware_vm("local-storage-vm-2", "esxi-1", networks)


def test_esxi_reboot(
    topology_with_two_nodes,
    vmware_dpg_1,
    vmware_dpg_2,
    vmware_vm_1,
    vmware_vm_2,
    vmware_vm_3,
    vmware_vm_4,
    vmware_vm_5,
    vmware_controller,
    vnc_test_client,
    vcenter_api_client,
):
    # User creates a DPG (dpg-1) on dvs-1
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)
    # User creates a DPG (dpg-2) on dvs-1
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)
    # User creates two VMs (vMotion-vm-1, vMotion-vm-2) with one interface connected to dpg-1 on nfs storage
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update)
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update)
    # User creates a VMs (vMotion-vm-3) with two interfaces connected to dpg-1 and dpg-2 on nfs storage
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_3)
    vmware_controller.handle_update(vm_created_update)
    # User creates two VMs (local-storage-vm-1, local-storage-vm-2) with
    # one interface connected to dpg-2 on local storage
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_4)
    vmware_controller.handle_update(vm_created_update)
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_5)
    vmware_controller.handle_update(vm_created_update)

    # VPG was created in VNC for pair: esxi-1, dvs-1
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    assert vnc_vpg is not None

    # A VMI was created in VNC for dpg-1 on dvs-1 on esxi-1
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vmi is not None

    # A VMI was created in VNC for dpg-2 on dvs-1 on esxi-1
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-2")
    )
    assert vnc_vmi is not None

    # At this point there is no VMs on esxi-2
    # esxi-1 was rebooted, VMs with nfs storage were migrated to esxi-2, VMs with local storage left on esxi-1
    host_change_update = vcenter_api_client.change_host(vmware_vm_1, "esxi-2")
    vmware_controller.handle_update(host_change_update)
    host_change_update = vcenter_api_client.change_host(vmware_vm_2, "esxi-2")
    vmware_controller.handle_update(host_change_update)
    host_change_update = vcenter_api_client.change_host(vmware_vm_3, "esxi-2")
    vmware_controller.handle_update(host_change_update)
    # sometimes vCenter triggers VmRemovedEvent with source host attached for migrated VM
    vm_removed_update = vcenter_api_client.remove_vm(
        vmware_vm_3, removed_from_vcenter=False, source_host_name="esxi-1"
    )
    vmware_controller.handle_update(vm_removed_update)

    # VPG was created in VNC for pair: esxi-2, dvs-1
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-2_dvs-1"))
    assert vnc_vpg is not None

    # A VMI was created in VNC for dpg-1 on dvs-1 on esxi-2
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-2_dvs-1_dpg-1")
    )
    assert vnc_vmi is not None

    # A VMI was created VNC for dpg-2 on dvs-1 on esxi-2
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-2_dvs-1_dpg-2")
    )
    assert vnc_vmi is not None

    # A VMI was deleted VNC for dpg-1 on dvs-1 on esxi-1
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-1"))

    # A VMI for dpg-2 on dvs-1 on esxi-1 stil exists in VNC
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-2")
    )
    assert vnc_vmi is not None
