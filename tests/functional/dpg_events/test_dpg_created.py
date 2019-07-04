import pytest
from pyVmomi import vim
from tests import utils

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


def test_dpg_created(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vcenter_api_client,
    vmware_dpg,
):
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)

    vmware_controller.handle_update(dpg_created_update)

    created_vn = vnc_test_client.read_vn(models.generate_uuid("dvportgroup-1"))

    assert created_vn is not None
    assert created_vn.name == "dvs-1_dpg-1"
