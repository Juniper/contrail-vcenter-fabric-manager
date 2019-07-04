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
        "dvs-name": "dvs-2",
        "vlan": 6,
    }
    return utils.create_vmware_net(net_data)


def test_sync_dvses_dpgs(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_dpg_1,
    vmware_dpg_2,
):
    # minimalistic_topology contains only dvs-1
    # Only this DVS should be supported
    # The list of supported DVSes is created during sync
    vmware_controller.sync()

    # User creates a DPG (dpg-1) in dvs-1
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)

    # dpg-1 is connected to dvs-1, so a VN should be created for it
    created_vn = vnc_test_client.read_vn(models.generate_uuid("dvportgroup-1"))
    assert created_vn is not None

    # User creates a DPG (dpg-2) in dvs-2
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)

    # No VN should be created for dpg-2, since dvs-2 is not supported
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vn(models.generate_uuid("dvportgroup-2"))
