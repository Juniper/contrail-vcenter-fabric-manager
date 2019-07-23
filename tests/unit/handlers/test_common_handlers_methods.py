import mock
import pytest

from cvfm import controllers


@pytest.fixture
def vpg_model():
    return mock.Mock()


@pytest.fixture
def vmi_model():
    return mock.Mock()


@pytest.fixture
def pi_model():
    return mock.Mock()


@pytest.fixture
def abstract_handler(
    vm_service, vmi_service, vpg_service, dpg_service, pi_service
):
    class TestHandler(controllers.AbstractEventHandler):
        def _handle_change(self, obj, property_change):
            pass

        def _handle_event(self, event):
            pass

    return TestHandler(
        vm_service=vm_service,
        vmi_service=vmi_service,
        dpg_service=dpg_service,
        vpg_service=vpg_service,
        pi_service=pi_service,
    )


def test_delete_vmis(abstract_handler, vmi_service):
    vmis = [mock.Mock(uuid="vmi-1"), mock.Mock(uuid="vmi-2")]

    abstract_handler._delete_vmis(vmis)

    assert vmi_service.delete_vmi.mock_calls == [
        mock.call("vmi-1"),
        mock.call("vmi-2"),
    ]


def test_create_vmis(
    abstract_handler,
    vmi_service,
    vpg_service,
    pi_service,
    vm_model,
    vpg_model,
    vmi_model,
    pi_model,
):
    pi_models = [pi_model]
    vpg_service.create_vpg_models.return_value = [vpg_model]
    pi_service.get_pi_models_for_vpg.return_value = pi_models

    abstract_handler._create_vmis(vm_model, [vmi_model])

    vpg_service.create_vpg_models.assert_called_once_with(vm_model)
    vpg_service.create_vpg_in_vnc.assert_called_once_with(vpg_model, pi_models)

    vmi_service.create_vmi_in_vnc.assert_called_once_with(vmi_model)
    vmi_service.attach_vmi_to_vpg.assert_called_once_with(vmi_model)


def test_is_tmp_vm_name(abstract_handler):
    tmp_vm_name = "/vmfs/volumes/5326168a-6dd1d607/yellow-133/yellow-133.vmx"
    assert abstract_handler._is_tmp_vm_name(tmp_vm_name)

    not_tmp_vm_name = "yellow-133"
    assert not abstract_handler._is_tmp_vm_name(not_tmp_vm_name)


def test_get_vm_name_from_tmp_name(abstract_handler):
    tmp_vm_name = "/vmfs/volumes/5326168a-6dd1d607/yellow-133/yellow-133.vmx"
    assert (
        abstract_handler._get_vm_name_from_tmp_name(tmp_vm_name)
        == "yellow-133"
    )
