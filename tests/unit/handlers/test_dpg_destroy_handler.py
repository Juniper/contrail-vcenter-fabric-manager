import mock
import pytest

from pyVmomi import vim

from cvfm import controllers
from tests import utils


@pytest.fixture
def vm_service():
    return mock.Mock()


@pytest.fixture
def vmi_service():
    return mock.Mock()


@pytest.fixture
def vpg_service():
    return mock.Mock()


@pytest.fixture
def dpg_service():
    return mock.Mock()


@pytest.fixture
def vpg_destroyed_update():
    event = mock.Mock(spec=vim.event.DVPortgroupDestroyedEvent())
    event.net.name = "dpg-1"
    event.dvs.name = "dvs-1"
    change = mock.Mock()
    change.configure_mock(name="latestPage")
    change.val = event
    return change


@pytest.fixture
def dpg_destroyed_handler(vm_service, vmi_service, dpg_service, vpg_service):
    return controllers.DVPortgroupDestroyedHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )


def test_handle_dpg_destroyed(
    dpg_destroyed_handler, dpg_service, vpg_service, vpg_destroyed_update
):
    dpg_service.clean_fabric_vn.return_value = ["vpg-1", "vpg-2"]

    dpg_destroyed_handler.handle_change(None, vpg_destroyed_update)

    assert dpg_service.delete_dpg_model.call_args[0] == ("dpg-1",)
    assert dpg_service.clean_fabric_vn.call_args[0] == ("dvs-1", "dpg-1")
    assert vpg_service.prune_empty_vpgs.call_args[0] == (["vpg-1", "vpg-2"],)
    assert dpg_service.delete_fabric_vn.call_args[0] == ("dvs-1", "dpg-1")
