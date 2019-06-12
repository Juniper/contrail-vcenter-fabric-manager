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


def test_dpg_sync_create(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_dpg_1,
    vmware_dpg_2,
):
    # User creates a DPG (dpg-1) and the event is properly handled
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)
    previous_vn_1 = vnc_test_client.read_vn(
        models.generate_uuid(vmware_dpg_1.key)
    )

    # CVFM shuts down
    # User creates a DPG (dpg-2) and the event is not handled
    vcenter_api_client.create_dpg(vmware_dpg_2)

    # CVFM starts up - sync
    vmware_controller.sync()

    # dpg-2 should be created in VNC
    created_vn = vnc_test_client.read_vn(
        models.generate_uuid(vmware_dpg_2.key)
    )
    assert created_vn is not None

    # dpg-1 should not be touched in VNC
    current_vn_1 = vnc_test_client.read_vn(
        models.generate_uuid(vmware_dpg_1.key)
    )
    assert utils.not_touched_in_vnc(previous_vn_1, current_vn_1)


def test_dpg_sync_delete(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_dpg_1,
):
    # User creates a DPG (dpg-1) and the event is properly handled
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_1)
    vmware_controller.handle_update(dpg_created_update)

    # CVFM shuts down
    # User deletes dpg-2 and the event is not handled
    vcenter_api_client.destroy_dpg(vmware_dpg_1)

    # CVFM starts up - sync
    vmware_controller.sync()

    # dpg-1 should be deleted in VNC
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vn(models.generate_uuid(vmware_dpg_1.key))
