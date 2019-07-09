import mock
import pytest

from pyVmomi import vim

from cvfm import controllers


@pytest.fixture
def vm_reconfigured_change():
    event = mock.Mock(spec=vim.event.VmReconfiguredEvent())
    device = mock.Mock(spec=vim.vm.device.VirtualPCNet32())
    device_spec = mock.Mock(spec=vim.vm.device.VirtualDeviceSpec())
    device_spec.device = device
    device_spec.operation = "remove"
    event.configSpec = mock.Mock(spec=vim.vm.ConfigSpec())
    event.configSpec.deviceChange = [device_spec]
    change = mock.Mock()
    change.configure_mock(name="latestPage")
    change.val = event
    return change


@pytest.fixture
def vm_reconfigured_handler(
    vm_service, vmi_service, dpg_service, vpg_service, pi_service
):
    return controllers.VmReconfiguredHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )


def test_device_type(
    vm_reconfigured_handler, vm_service, vm_reconfigured_change
):

    vm_reconfigured_handler.handle_change(None, vm_reconfigured_change)

    vm_service.delete_vm_model.assert_called_once()

    vm_reconfigured_change.val.configSpec.deviceChange[0].device = mock.Mock(
        spec=vim.vm.device.VirtualCdrom()
    )
    vm_reconfigured_handler.handle_change(None, vm_reconfigured_change)

    vm_service.delete_vm_model.assert_called_once()
