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
def vmware_net():
    net_data = {"key": "network-1", "name": "network-1", "type": vim.Network}
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm(vmware_dpg, vmware_net):
    networks = [vmware_dpg, vmware_net]
    return utils.create_vmware_vm("vm-1", "esxi-1", networks)


def test_empty_dpg_destroyed(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_dpg,
):
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)
    vn_uuid = models.generate_uuid("dvportgroup-1")
    assert vnc_test_client.read_vn(vn_uuid) is not None

    dpg_destroyed_update = vcenter_api_client.destroy_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_destroyed_update)

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vn(vn_uuid)


def test_not_empty_dpg_destroyed(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_dpg,
    vmware_vm,
):
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)
    vm_created_update = vcenter_api_client.create_vm(vmware_vm)
    vmware_controller.handle_update(vm_created_update)
    vn_uuid = models.generate_uuid("dvportgroup-1")
    assert len(vnc_test_client.read_all_vmis()) == 1
    assert len(vnc_test_client.read_all_vpgs()) == 1
    assert vnc_test_client.read_vn(vn_uuid) is not None

    dpg_destroyed_update = vcenter_api_client.destroy_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_destroyed_update)

    assert len(vnc_test_client.read_all_vmis()) == 0
    assert len(vnc_test_client.read_all_vpgs()) == 0
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vn(vn_uuid)
