import mock
import pytest

from pyVmomi import vim, vmodl

from cvfm import controllers


@pytest.fixture
def vpg_model():
    return mock.Mock()


@pytest.fixture
def pi_model():
    return mock.Mock()


@pytest.fixture
def host():
    host = mock.Mock()
    host.configure_mock(name="esxi-1")
    return host


@pytest.fixture
def host_change(vmware_vm, host):
    change = mock.Mock(spec_set=vmodl.query.PropertyCollector.Change())
    change.configure_mock(name="runtime.host")
    change.val = host
    return change


@pytest.fixture
def host_change_handler(
    vm_service, vmi_service, dpg_service, vpg_service, pi_service
):
    return controllers.HostChangeHandler(
        vm_service=vm_service,
        vmi_service=vmi_service,
        dpg_service=dpg_service,
        vpg_service=vpg_service,
        pi_service=pi_service,
    )


def test_host_change_handler_no_change(
    dpg_service,
    host_change,
    host_change_handler,
    vm_service,
    vmi_service,
    vmware_vm,
    vpg_service,
    host,
):
    # The VM is not moved
    vm_service.check_vm_moved.return_value = False

    host_change_handler.handle_change(vmware_vm, host_change)

    vm_service.check_vm_moved.assert_called_once_with(vmware_vm.name, host)

    # no changes
    vm_service.delete_vm_model.assert_not_called()
    vm_service.create_vm_model.assert_not_called()

    assert len(vmi_service.method_calls) == 0
    assert len(vpg_service.method_calls) == 0
    assert len(dpg_service.method_calls) == 0


def test_host_change_handler(
    dpg_service,
    host,
    host_change,
    host_change_handler,
    vm_model,
    vm_service,
    vmi_service,
    vmware_vm,
    vpg_model,
    vpg_service,
    pi_service,
    pi_model,
):
    vm_service.check_vm_moved.return_value = True
    source_host = mock.Mock()
    vm_service.get_host_from_vm.return_value = source_host
    vm_service.delete_vm_model.return_value = vm_model
    new_vm_model = mock.Mock()
    vm_service.create_vm_model.return_value = new_vm_model

    pi_models = [pi_model]
    pi_service.get_pi_models_for_vpg.return_value = pi_models

    old_vmis = [mock.Mock(uuid="vmi-1"), mock.Mock(uuid="vmi-to-delete")]
    new_vmi = mock.Mock(uuid="vmi-3")
    vmi_service.create_vmi_models_for_vm.side_effect = [old_vmis, [new_vmi]]
    dpg_service.filter_out_non_empty_dpgs.return_value = old_vmis[1:]
    vpg_service.create_vpg_models.return_value = [vpg_model]

    # VM is moved
    host_change_handler.handle_change(vmware_vm, host_change)

    # Check if VM is moved and get source host details
    vm_service.check_vm_moved.assert_called_once_with(vmware_vm.name, host)
    vm_service.get_host_from_vm.assert_called_once_with(vmware_vm.name)

    # VM model needs to be recreated
    vm_service.delete_vm_model.assert_called_once_with(vm_model.name)
    vm_service.create_vm_model.assert_called_once_with(vmware_vm)

    # Create models for old and new VMIs
    vmi_service.create_vmi_models_for_vm.mock_calls = [
        mock.call(vm_model),
        mock.call(new_vm_model),
    ]

    # From old VMIs on host, select which are unused after move VM
    dpg_service.filter_out_non_empty_dpgs.assert_called_once_with(
        set(old_vmis), source_host
    )
    vmi_service.delete_vmi.assert_called_once_with("vmi-to-delete")

    # Create VPG based on new VM model and attach PIs to them
    vpg_service.create_vpg_models.assert_called_once_with(new_vm_model)
    vpg_service.create_vpg_in_vnc.assert_called_once_with(vpg_model, pi_models)

    # Create new VMI and attach to VPG
    vmi_service.create_vmi_in_vnc.assert_called_once_with(new_vmi)
    vmi_service.attach_vmi_to_vpg.assert_called_once_with(new_vmi)


def test_host_change_handler_source_host_not_exist(
    dpg_service,
    host,
    host_change,
    host_change_handler,
    vm_model,
    vm_service,
    vmi_service,
    vmware_vm,
    vpg_model,
    vpg_service,
    pi_service,
    pi_model,
):
    vm_service.check_vm_moved.return_value = True
    vm_service.get_host_from_vm.return_value = None
    vm_service.delete_vm_model.return_value = vm_model
    new_vm_model = mock.Mock()
    vm_service.create_vm_model.return_value = new_vm_model

    pi_models = [pi_model]
    pi_service.get_pi_models_for_vpg.return_value = pi_models

    old_vmi = mock.Mock(uuid="vmi-to-delete")
    new_vmi = mock.Mock(uuid="vmi-2")
    vmi_service.create_vmi_models_for_vm.side_effect = [[old_vmi], [new_vmi]]
    vpg_service.create_vpg_models.return_value = [vpg_model]

    # VM is moved
    host_change_handler.handle_change(vmware_vm, host_change)

    # Check if VM is moved and get source host details
    vm_service.check_vm_moved.assert_called_once_with(vmware_vm.name, host)
    vm_service.get_host_from_vm.assert_called_once_with(vmware_vm.name)

    # VM model needs to be recreated
    vm_service.delete_vm_model.assert_called_once_with(vm_model.name)
    vm_service.create_vm_model.assert_called_once_with(vmware_vm)

    # Create models for old and new VMIs
    vmi_service.create_vmi_models_for_vm.mock_calls = [
        mock.call(vm_model),
        mock.call(new_vm_model),
    ]

    # Don't try to filter out for not-existing host
    dpg_service.filter_out_non_empty_dpgs.assert_not_called()
    vmi_service.delete_vmi.assert_called_once_with("vmi-to-delete")

    # Create VPG based on new VM model and attach PIs to them
    vpg_service.create_vpg_models.assert_called_once_with(new_vm_model)
    vpg_service.create_vpg_in_vnc.assert_called_once_with(vpg_model, pi_models)

    # Create new VMI and attach to VPG
    vmi_service.create_vmi_in_vnc.assert_called_once_with(new_vmi)
    vmi_service.attach_vmi_to_vpg.assert_called_once_with(new_vmi)
