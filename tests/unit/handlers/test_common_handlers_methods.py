import mock
import pytest

from pyVmomi import vim

from cvfm import controllers


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
def vpg_model():
    return mock.Mock()


@pytest.fixture
def vmi_model():
    return mock.Mock()


@pytest.fixture
def abstract_handler(vm_service, vmi_service, vpg_service, dpg_service):
    class TestHandler(controllers.AbstractEventHandler):
        def _handle_event(self, event):
            pass

    return TestHandler(vm_service, vmi_service, dpg_service, vpg_service)


def test_delete_vmis(abstract_handler, vmi_service):
    vmis = [mock.Mock(uuid="vmi-1"), mock.Mock(uuid="vmi-2")]

    abstract_handler._delete_vmis(vmis)

    assert vmi_service.delete_vmi.mock_calls == [
        mock.call("vmi-1"),
        mock.call("vmi-2"),
    ]


def test_create_vmis(
    abstract_handler, vmi_service, vpg_service, vm_model, vpg_model, vmi_model
):
    vpg_service.create_vpg_models.return_value = [vpg_model]

    abstract_handler._create_vmis(vm_model, [vmi_model])

    vpg_service.create_vpg_models.assert_called_once_with(vm_model)
    vpg_service.create_vpg_in_vnc.assert_called_once_with(vpg_model)
    vpg_service.attach_pis_to_vpg.assert_called_once_with(vpg_model)

    vmi_service.create_vmi_in_vnc.assert_called_once_with(vmi_model)
    vmi_service.attach_vmi_to_vpg.assert_called_once_with(vmi_model)
