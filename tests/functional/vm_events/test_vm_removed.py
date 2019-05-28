import mock
import pytest
from vnc_api import vnc_api
from pyVmomi import vim

from cvfm import models, controllers
from tests import utils


@pytest.fixture
def update_handler(vm_service, vmi_service, vpg_service, dpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )
    vm_removed_handler = controllers.VmRemovedHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )
    return controllers.UpdateHandler([vm_updated_handler, vm_removed_handler])


@pytest.fixture
def vm_removed_update_1():
    event = mock.Mock(spec=vim.event.VmRemovedEvent())
    event.vm.name = "vm-1"
    event.host.name = "esxi-1"
    event.host.host = mock.Mock(vm=[])
    return utils.wrap_into_update_set(event=event)


@pytest.fixture
def vm_removed_update_2(vmware_vm_2):
    event = mock.Mock(spec=vim.event.VmRemovedEvent())
    event.vm.name = "vm-1"
    event.host.name = "esxi-1"
    event.host.host = mock.Mock(vm=[vmware_vm_2])
    return utils.wrap_into_update_set(event=event)


@pytest.fixture
def vm_removed_update_3(vmware_vm_3):
    event = mock.Mock(spec=vim.event.VmRemovedEvent())
    event.vm.name = "vm-1"
    event.host.name = "esxi-1"
    event.host.host = mock.Mock(vm=[vmware_vm_3])
    return utils.wrap_into_update_set(event=event)


@pytest.fixture
def fabric_vn_2(vnc_test_client):
    utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-2", "dvportgroup-2"
    )


@pytest.fixture
def vmware_vm_1(vmware_dpg_1):
    return mock.Mock(vm=[vmware_dpg_1])


@pytest.fixture
def vmware_vm_2(vmware_dpg_1):
    return mock.Mock(vm=[vmware_dpg_1])


@pytest.fixture
def vmware_vm_3(vmware_dpg_2):
    return mock.Mock(vm=[vmware_dpg_2])


@pytest.fixture
def vmware_dpg_1():
    dpg = mock.Mock()
    dpg.name = "dpg-1"
    dpg.key = "dvportgroup-1"
    dpg.config.defaultPortConfig.vlan.vlanId = 5
    dpg.config.distributedVirtualSwitch.name = "dvs-1"
    dpg.vm = []
    return dpg


@pytest.fixture
def vmware_dpg_2():
    dpg = mock.Mock()
    dpg.name = "dpg-2"
    dpg.key = "dvportgroup-2"
    dpg.config.defaultPortConfig.vlan.vlanId = 5
    dpg.config.distributedVirtualSwitch.name = "dvs-1"
    dpg.vm = []
    return dpg


@pytest.fixture
def vm_created_update_1():
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
def vm_created_update_2():
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
        vm_name="vm-2", vm_host_name="esxi-1", vm_networks=networks
    )


@pytest.fixture
def vm_created_update_3():
    networks = [
        {
            "key": "dvportgroup-2",
            "name": "dpg-2",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 6,
        }
    ]
    return utils.create_vm_created_update(
        vm_name="vm-3", vm_host_name="esxi-1", vm_networks=networks
    )


@pytest.fixture
def vm_created_update_4():
    networks = [
        {
            "key": "dvportgroup-1",
            "name": "dpg-1",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 5,
        },
        {
            "key": "dvportgroup-2",
            "name": "dpg-2",
            "type": vim.DistributedVirtualPortgroup,
            "dvs-name": "dvs-1",
            "vlan": 6,
        }
    ]
    return utils.create_vm_created_update(
        vm_name="vm-1", vm_host_name="esxi-1", vm_networks=networks
    )


def test_last_vm_from_pg(
    minimalistic_topology,
    fabric_vn,
    vmware_controller,
    vcenter_api_client,
    vm_created_update_1,
    vm_removed_update_1,
    vnc_test_client,
):
    vmware_controller.handle_update(vm_created_update_1)
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )

    assert vnc_vpg is not None
    assert vnc_vmi is not None

    vcenter_api_client.get_vms_by_portgroup.return_value = []
    vmware_controller.handle_update(vm_removed_update_1)

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(vnc_vpg.uuid)
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(vnc_vmi.uuid)


def test_vms_remaining_in_pg(
    minimalistic_topology,
    fabric_vn,
    vmware_controller,
    vcenter_api_client,
    vm_created_update_1,
    vm_created_update_2,
    vmware_vm_2,
    vm_removed_update_2,
    vnc_test_client,
):
    vmware_controller.handle_update(vm_created_update_1)
    vmware_controller.handle_update(vm_created_update_2)
    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert vnc_vpg is not None
    assert vnc_vmi is not None

    vcenter_api_client.get_vms_by_portgroup.return_value = [vmware_vm_2]
    vmware_controller.handle_update(vm_removed_update_2)

    vpg = vnc_test_client.read_vpg(vnc_vpg.uuid)
    vmi = vnc_test_client.read_vmi(vnc_vmi.uuid)

    assert vpg is not None
    assert vmi is not None


def test_two_vms_two_pgs(
    minimalistic_topology,
    fabric_vn,
    fabric_vn_2,
    vmware_controller,
    vcenter_api_client,
    vm_created_update_1,
    vm_created_update_3,
    vm_removed_update_3,
    vnc_test_client,
):
    vmware_controller.handle_update(vm_created_update_1)
    vmware_controller.handle_update(vm_created_update_3)
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

    vcenter_api_client.get_vms_by_portgroup.return_value = []
    vmware_controller.handle_update(vm_removed_update_3)

    vpg = vnc_test_client.read_vpg(vnc_vpg.uuid)
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(vnc_vmi_1.uuid)
    vmi_2 = vnc_test_client.read_vmi(vnc_vmi_2.uuid)

    assert vpg is not None
    assert vmi_2 is not None


def test_two_pgs_one_empty(
    minimalistic_topology,
    fabric_vn,
    fabric_vn_2,
    vmware_controller,
    vcenter_api_client,
    vm_created_update_4,
    vm_removed_update_2,
    vmware_vm_2,
    vnc_test_client,
):
    vmware_controller.handle_update(vm_created_update_4)
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

    vcenter_api_client.get_vms_by_portgroup.side_effect = [[], [vmware_vm_2]]
    vmware_controller.handle_update(vm_removed_update_2)

    vnc_vpg = vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
    vnc_vmi_2 = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-2")
    )
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-1"))
    assert vnc_vpg is not None
    assert vnc_vmi_2 is not None
