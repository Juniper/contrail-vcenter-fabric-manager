import mock
import pytest
from pyVmomi import vim
from tests import utils
from vnc_api import vnc_api

from cvfm import models


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
    vm = mock.Mock()
    vm.configure_mock(name="vm-1")
    vm.network = [vmware_dpg]
    vm.runtime.host.name = "esxi-1"
    return vm


@pytest.fixture
def vmware_vm_2(vmware_dpg):
    vm = mock.Mock()
    vm.configure_mock(name="vm-2")
    vm.network = [vmware_dpg]
    vm.runtime.host.name = "esxi-1"
    return vm


def test_esxi_changed(
    topology_with_two_nodes,
    vmware_vm_1,
    vmware_vm_2,
    vmware_dpg,
    vmware_controller,
    vnc_test_client,
    vcenter_api_client,
):
    # User creates a DPG (dpg-1) on dvs-1
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)

    # User creates a VM (vm-1) with one interface connected to dpg-1
    vm_created_update_1 = vcenter_api_client.create_vm(vmware_vm_1)
    vmware_controller.handle_update(vm_created_update_1)

    # A VMI and VPG is created in VNC for dpg-1 on dvs-1 on esxi-1
    vnc_vpg_1 = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi_1 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg_1 is not None
    assert vnc_vmi_1 is not None

    # User creates a second VM (vm-2) with one interface connected to dpg-1
    vm_created_update_2 = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update_2)

    # The first VM (vm-1) is moved to esxi-2, where no other VM exists
    vm_moved_update = vcenter_api_client.change_host(vmware_vm_1, "esxi-2")
    vmware_controller.handle_update(vm_moved_update)

    # A VMI is created in VNC for dpg-1 on dvs-1 on esxi-2
    # and is connected to a new VPG for dvs-1 on esxi-2
    vnc_vpg_2 = vnc_test_client.read_vpg(models.generate_uuid("esxi-2_dvs-1"))
    vnc_vmi_2 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-2_dvs-1_dpg-1")
    )
    assert vnc_vpg_2 is not None
    assert vnc_vmi_2 is not None

    # The old VMI and VPG on esxi-1 still exists due to vm-2 existing on esxi-1
    vnc_vpg_1 = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi_1 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg_1 is not None
    assert vnc_vmi_1 is not None

    # The second VM (vm-2) is moved to esxi-2
    vm_moved_update = vcenter_api_client.change_host(vmware_vm_2, "esxi-2")
    vmware_controller.handle_update(vm_moved_update)

    # esxi-1 is empty, so the old VMI and VPG are removed
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-1"))
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
