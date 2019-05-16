import mock
import pytest
from pyVmomi import vim, vmodl  # pylint: disable=no-name-in-module

from tests.utils import wrap_into_update_set

from cvfm.controllers import (
    DVPortgroupCreatedHandler,
    DVPortgroupDestroyedHandler,
    UpdateHandler,
)
from cvfm.models import key_to_uuid


@pytest.fixture
def update_handler(dpg_service):
    dpg_created_handler = DVPortgroupCreatedHandler(None, None, dpg_service)
    dpg_destroyed_handler = DVPortgroupDestroyedHandler(
        None, None, dpg_service
    )
    return UpdateHandler([dpg_created_handler, dpg_destroyed_handler])


@pytest.fixture
def dpg_created_update():
    event = mock.Mock(spec=vim.event.DVPortgroupCreatedEvent())
    event.net.network.name = "DPG1"
    event.net.network.key = "dvportgroup-1"
    event.net.network.config.distributedVirtualSwitch.name = "DSwitch"
    event.net.network.config.defaultPortConfig.vlan.vlanId = 5
    return wrap_into_update_set(event=event)


def test_dpg_created(vnc_test_client, vmware_controller, dpg_created_update):
    vmware_controller.handle_update(dpg_created_update)

    created_vn = vnc_test_client.vnc_lib.virtual_network_read(
        id=key_to_uuid("dvportgroup-1")
    )

    assert created_vn is not None
    assert created_vn.name == "DSwitch_DPG1"
