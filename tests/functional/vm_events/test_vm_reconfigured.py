import mock
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
def vmware_vm(vmware_dpg_1):
    vm = mock.Mock()
    vm.configure_mock(name="vm-1")
    vm.network = [vmware_dpg_1]
    vm.runtime.host.name = "esxi-1"
    return vm


def test_vm_reconfigured(
    topology_with_spine_switch,
    vmware_vm,
    vmware_dpg_1,
    vmware_dpg_2,
    vmware_dpg_3,
    vmware_controller,
    vnc_test_client,
    vcenter_api_client,
):
    # User creates a DPG (dpg-1) on dvs-1
    dpg_created_update_1 = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update_1)

    # User creates another DPG (dpg-2) on dvs-1
    dpg_created_update_2 = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update_2)

    # User creates a DPG (dpg-3) on dvs-2
    dpg_created_update_3 = vcenter_api_client.create_dpg(vmware_dpg_3)
    vmware_controller.handle_update(dpg_created_update_3)

    # User creates a VM (vm-1) with one interface connected to dpg-1
    vm_created_update = vcenter_api_client.create_vm(vmware_vm)
    vmware_controller.handle_update(vm_created_update)

    # A VMI and VPG is created in VNC for dpg-1 on dvs-1 on esxi-1
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi_1 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg is not None
    assert vnc_vmi_1 is not None

    # User creates a different interface for vm-1 and connects it to dpg-2
    vm_reconfigured_update_add = vcenter_api_client.add_interface(
        vmware_vm, vmware_dpg_2
    )
    vmware_controller.handle_update(vm_reconfigured_update_add)

    # A VMI is created in VNC for dpg-2 on dvs-1 on esxi-1 and is connected
    # to the existing VPG
    vnc_vmi_2 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-2")
    )
    assert vnc_vmi_2 is not None

    # User edits the configuration of the second interface and connects it
    # to dpg-3
    vm_reconfigured_update_edit = vcenter_api_client.edit_interface(
        vmware_vm, vmware_dpg_2, vmware_dpg_3
    )
    vmware_controller.handle_update(vm_reconfigured_update_edit)

    # A new VMI and VPG is created for dpg-3 on dvs-2 on esxi-1
    vnc_vpg_2 = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-2"))
    vnc_vmi_3 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-2_dpg-3")
    )
    assert vnc_vpg_2 is not None
    assert vnc_vmi_3 is not None

    # The VMI for dpg-2 is removed from VNC
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-2"))

    # User disconnects one interface from dpg-3
    vm_reconfigured_update_remove = vcenter_api_client.remove_interface(
        vmware_vm, vmware_dpg_3
    )
    vmware_controller.handle_update(vm_reconfigured_update_remove)

    # The VMI and VPG for dpg-3 on dvs-2 are deleted
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-2"))
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-2_dpg-3"))

    # User disconnects another interface from dpg-1
    vm_reconfigured_update_remove = vcenter_api_client.remove_interface(
        vmware_vm, vmware_dpg_1
    )
    vmware_controller.handle_update(vm_reconfigured_update_remove)

    # The VMI and VPG for dpg-1 on dvs-1 on esxi-1 are deleted
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-1"))
