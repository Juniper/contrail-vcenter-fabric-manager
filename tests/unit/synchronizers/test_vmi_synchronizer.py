import mock
import pytest

from cvfm import models


@pytest.fixture
def vmi_service():
    return mock.Mock()


@pytest.fixture
def vm_service():
    return mock.Mock()


def test_sync_create(vmi_synchronizer, vm_service, vmi_service, vm_model):
    vm_model_2 = models.VirtualMachineModel(
        "vm-2", "uuid-2", "esxi-1", vm_model.dpg_models
    )
    vm_service.get_all_vm_models.return_value = [vm_model, vm_model_2]
    vmi_service.create_vmi_models_for_vm.side_effect = [
        models.VirtualMachineInterfaceModel.from_vm_model(vm_model),
        models.VirtualMachineInterfaceModel.from_vm_model(vm_model_2),
    ]

    vmi_synchronizer.sync_create()

    vmi_service.create_vmi_in_vnc.assert_called_once()
    vmi_service.attach_vmi_to_vpg.assert_called_once()
    vpg_model = vmi_service.create_vmi_in_vnc.call_args[0][0]
    vmi_service.attach_vmi_to_vpg.assert_called_with(vpg_model)


def test_sync_delete(vmi_synchronizer, vm_service, vmi_service, vm_model):
    vm_service.get_all_vm_models.return_value = [vm_model]
    vmi_service.read_all_vmis.return_value = [
        mock.Mock(uuid="non-existent-vmi-uuid"),
        mock.Mock(uuid=models.generate_uuid("esxi-1_dvs-1_dpg-1")),
    ]
    vmi_model = models.VirtualMachineInterfaceModel.from_vm_model(vm_model)
    vmi_service.create_vmi_models_for_vm.return_value = vmi_model

    vmi_synchronizer.sync_delete()

    vmi_service.delete_vmi.assert_called_once_with("non-existent-vmi-uuid")
