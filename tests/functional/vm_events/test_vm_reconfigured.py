import mock
import pytest
from pyVmomi import vim
from tests import utils
from vnc_api import vnc_api

from cvfm import controllers, models


@pytest.fixture
def update_handler(vm_service, vmi_service, vpg_service, dpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )
    vm_reconfigured_handler = controllers.VmReconfiguredHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )
    return controllers.UpdateHandler(
        [vm_updated_handler, vm_reconfigured_handler]
    )


@pytest.fixture
def vm_created_update():
    networks = [
        {
            "key": "dvportgroup-1",
            "name": "dpg-1",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 5,
        }
    ]
    return utils.create_vm_created_update(
        vm_name="vm-1", vm_host_name="esxi-1", vm_networks=networks
    )


@pytest.fixture
def fabric_vn_2(vnc_test_client):
    return utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-2", "dvportgroup-2"
    )


@pytest.fixture
def fabric_vn_3(vnc_test_client):
    return utils.create_fabric_network(
        vnc_test_client, "dvs-2_dpg-3", "dvportgroup-3"
    )


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


@pytest.fixture
def vm_reconfigured_update_add(vmware_vm):
    return utils.create_vm_reconfigured_update(vmware_vm, "add")


@pytest.fixture
def vm_reconfigured_update_edit(vmware_vm):
    return utils.create_vm_reconfigured_update(vmware_vm, "edit")


@pytest.fixture
def vm_reconfigured_update_remove(vmware_vm):
    return utils.create_vm_reconfigured_update(vmware_vm, "remove")


def test_vm_reconfigured(
    minimalistic_topology,
    fabric_vn,
    fabric_vn_2,
    fabric_vn_3,
    vmware_vm,
    vmware_dpg_1,
    vmware_dpg_2,
    vmware_dpg_3,
    vm_created_update,
    vm_reconfigured_update_add,
    vm_reconfigured_update_edit,
    vm_reconfigured_update_remove,
    vmware_controller,
    vnc_test_client,
    vcenter_api_client,
):
    # User creates a VM (vm-1) with one interface connected to dpg-1
    vmware_controller.handle_update(vm_created_update)

    # A VMI and VPG is created in VNC for dpg-1 on dvs-1 on esxi-1
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi_1 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg is not None
    assert vnc_vmi_1 is not None

    # User creates a different interface for vm-1 and connects it to dpg-2
    vmware_vm.network = [vmware_dpg_1, vmware_dpg_2]
    vmware_controller.handle_update(vm_reconfigured_update_add)

    # A VMI is created in VNC for dpg-2 on dvs-1 on esxi-1 and is connected
    # to the existing VPG
    vnc_vmi_2 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-2")
    )
    assert vnc_vmi_2 is not None

    # User edits the configuration of the second interface and connects it
    # to dpg-3
    vmware_vm.network = [vmware_dpg_1, vmware_dpg_3]
    vcenter_api_client.get_vms_by_portgroup.side_effect = (
        lambda x: [vmware_vm]
        if x == "dvportgroup-1" or x == "dvportgroup-3"
        else []
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
    vmware_vm.network = [vmware_dpg_1]
    vcenter_api_client.get_vms_by_portgroup.side_effect = (
        lambda x: [vmware_vm] if x == "dvportgroup-1" else []
    )
    vmware_controller.handle_update(vm_reconfigured_update_remove)

    # The VMI and VPG for dpg-3 on dvs-2 are deleted
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-2"))
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-2_dpg-3"))

    # User disconnects another interface from dpg-1
    vmware_vm.network = []
    vcenter_api_client.get_vms_by_portgroup.side_effect = None
    vcenter_api_client.get_vms_by_portgroup.return_value = []
    vmware_controller.handle_update(vm_reconfigured_update_remove)

    # The VMI and VPG for dpg-1 on dvs-1 on esxi-1 are deleted
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-1"))
