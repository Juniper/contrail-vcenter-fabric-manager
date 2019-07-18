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
def vmware_vm(vmware_dpg_1):
    vm = mock.Mock()
    vm.configure_mock(name="vm-1")
    vm.network = [vmware_dpg_1]
    vm.runtime.host.name = "esxi-1"
    return vm


def test_esxi_changed_with_rename(
    topology_with_two_nodes,
    vmware_vm,
    vmware_dpg_1,
    vmware_dpg_2,
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

    # User creates a VM (vm-1) with one interface connected to dpg-1
    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm)
    vmware_controller.handle_update(vm_created_update_1)

    # A VMI and VPG is created in VNC for dpg-1 on dvs-1 on esxi-1
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg is not None
    assert vnc_vmi is not None

    # The first VM (vm-1) is moved to esxi-2, where no other VM exists
    vm_moved_update = vcenter_api_client.change_host(vmware_vm, "esxi-2")
    vmware_controller.handle_update(vm_moved_update)

    # But sometimes vCenter triggers such VM rename event for migrated VM
    new_name = "/vmfs/volumes/5326168a-6dd1d607/vm-1/vm-1.vmx"
    vm_renamed_update = vcenter_api_client.rename_vm(vmware_vm, new_name)
    vmware_controller.handle_update(vm_renamed_update)

    # and VM removed event as well
    vm_removed_update = vcenter_api_client.remove_vm(
        vmware_vm, removed_from_vcenter=False, source_host_name="esxi-1"
    )
    vmware_controller.handle_update(vm_removed_update)

    # VMI and VPG regarding esxi-1 should be deleted
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-1"))

    # VMI and VPG regarding esxi-2 should be created
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-2_dvs-1"))
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-2_dvs-1_dpg-1")
    )
    assert vnc_vpg is not None
    assert vnc_vmi is not None

    # After VM migration process completion events come with old VM name (vm-1 in this case)
    # VM vm-1 gained network adapter connected to dpg-2
    vmware_vm.name = "vm-1"
    vm_reconfigured_update_add = vcenter_api_client.add_interface(
        vmware_vm, vmware_dpg_2
    )
    vmware_controller.handle_update(vm_reconfigured_update_add)

    # VMI for dpg-2 on esxi-2 should be created
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-2_dvs-1_dpg-2")
    )
    assert vnc_vmi is not None
