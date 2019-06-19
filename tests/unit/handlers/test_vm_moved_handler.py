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
def source_host():
    host = mock.Mock()
    host.configure_mock(name="esxi-1")
    return host


@pytest.fixture(
    params=[
        vim.event.VmMigratedEvent(),
        vim.event.DrsVmMigratedEvent(),
        vim.event.VmRelocatedEvent(),
    ]
)
def vm_moved_change(vmware_vm, source_host, request):
    event = mock.Mock(spec_set=request.param)
    event.vm.vm = vmware_vm
    event.vm.name = vmware_vm.name
    event.host.host = vmware_vm.runtime.host.host
    event.host.name = vmware_vm.runtime.host.name
    event.sourceHost.host = source_host
    event.sourceHost.name = source_host.name
    change = mock.Mock()
    change.configure_mock(name="latestPage")
    change.val = event
    return change


@pytest.fixture
def vm_moved_handler(vm_service, vmi_service, dpg_service, vpg_service):
    return controllers.VmMovedHandler(
        vm_service, vmi_service, dpg_service, vpg_service
    )


def test_vm_moved_handler(
    database,
    dpg_service,
    source_host,
    vm_model,
    vm_moved_change,
    vm_moved_handler,
    vm_service,
    vmi_service,
    vmware_vm,
    vpg_model,
    vpg_service,
):
    vm_service.delete_vm_model.return_value = vm_model
    new_vm_model = mock.Mock()
    vm_service.create_vm_model.return_value = new_vm_model

    old_vmis = [mock.Mock(uuid="vmi-1"), mock.Mock(uuid="vmi-to-delete")]
    new_vmi = mock.Mock(uuid="vmi-3")
    vmi_service.find_affected_vmis.return_value = (old_vmis, [new_vmi])
    dpg_service.filter_out_non_empty_dpgs.return_value = old_vmis[1:]
    vpg_service.create_vpg_models.return_value = [vpg_model]

    # VM is moved
    vm_moved_handler.handle_change(None, vm_moved_change)

    # VM model needs to be recreated
    vm_service.delete_vm_model.assert_called_once_with(vm_model.name)
    vm_service.create_vm_model.assert_called_once_with(vmware_vm)

    # From old VMIs on host, select which are unused after move VM
    dpg_service.filter_out_non_empty_dpgs.assert_called_once_with(
        old_vmis, source_host
    )
    vmi_service.delete_vmi.assert_called_once_with("vmi-to-delete")

    # Create VPG based on new VM model and attach PIs to them
    vpg_service.create_vpg_models.assert_called_once_with(new_vm_model)
    vpg_service.create_vpg_in_vnc.assert_called_once_with(vpg_model)
    vpg_service.attach_pis_to_vpg.assert_called_once_with(vpg_model)

    # Create new VMI and attach to VPG
    vmi_service.create_vmi_in_vnc.assert_called_once_with(new_vmi)
    vmi_service.attach_vmi_to_vpg.assert_called_once_with(new_vmi)
