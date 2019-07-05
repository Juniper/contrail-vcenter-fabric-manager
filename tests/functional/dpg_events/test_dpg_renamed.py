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


def test_dpg_renamed(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_dpg,
):
    # dpg-1 created in dvs-1
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)

    created_vn = vnc_test_client.read_vn(models.generate_uuid(vmware_dpg.key))
    assert created_vn.name == "dvs-1_dpg-1"

    # dpg-1 renamed to renamed-dpg-1
    dpg_renamed_update = vcenter_api_client.rename_dpg(
        vmware_dpg, "renamed-dpg-1"
    )
    vmware_controller.handle_update(dpg_renamed_update)
    assert vmware_dpg.name == "renamed-dpg-1"

    current_vn = vnc_test_client.read_vn(models.generate_uuid(vmware_dpg.key))
    assert utils.not_touched_in_vnc(created_vn, current_vn)

    # renamed-dpg-1 deleted from dvs-1
    dpg_destroyed_update = vcenter_api_client.destroy_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_destroyed_update)

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vn(models.generate_uuid(vmware_dpg.key))
