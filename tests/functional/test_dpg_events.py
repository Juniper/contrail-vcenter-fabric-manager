import mock
import pytest
from pyVmomi import vim
from tests.utils import wrap_into_update_set

from cvfm import controllers, models


@pytest.fixture
def update_handler(dpg_service):
    dpg_created_handler = controllers.DVPortgroupCreatedHandler(
        None, None, dpg_service
    )
    return controllers.UpdateHandler([dpg_created_handler])


@pytest.fixture
def vmware_dpg():
    dpg = mock.Mock(spec=vim.DistributedVirtualPortgroup)
    dpg.configure_mock(name="dpg-1")
    dpg.key = "dvportgroup-1"
    dpg.config.distributedVirtualSwitch.name = "dvs-1"
    dpg.config.defaultPortConfig.vlan.vlanId = 5
    return dpg


@pytest.fixture
def dpg_created_update(vmware_dpg):
    event = mock.Mock(spec=vim.event.DVPortgroupCreatedEvent())
    event.net.network = vmware_dpg
    return wrap_into_update_set(event=event)


def test_dpg_created(vnc_test_client, vmware_controller, dpg_created_update):
    vmware_controller.handle_update(dpg_created_update)

    created_vn = vnc_test_client.vnc_lib.virtual_network_read(
        id=models.generate_uuid("dvportgroup-1")
    )

    assert created_vn is not None
    assert created_vn.name == "dvs-1_dpg-1"
