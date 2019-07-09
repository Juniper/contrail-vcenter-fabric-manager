import mock
import pytest

from pyVmomi import vim

from cvfm import controllers


@pytest.fixture
def dpg_renamed_update():
    event = mock.Mock(spec=vim.event.DVPortgroupRenamedEvent())
    event.net.name = "dpg-1"
    event.dvs.name = "dvs-1"
    event.oldName = "dpg-1"
    event.newName = "dpg-new-name"
    change = mock.Mock()
    change.configure_mock(name="latestPage")
    change.val = event
    return change


@pytest.fixture
def dpg_renamed_handler(
    vm_service, vmi_service, dpg_service, vpg_service, pi_service
):
    return controllers.DVPortgroupRenamedHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )


def test_handle_dpg_renamed(
    dpg_renamed_handler, dpg_service, dpg_renamed_update
):
    dpg_renamed_handler.handle_change(None, dpg_renamed_update)

    assert dpg_service.rename_dpg.call_args[0] == ("dpg-1", "dpg-new-name")
