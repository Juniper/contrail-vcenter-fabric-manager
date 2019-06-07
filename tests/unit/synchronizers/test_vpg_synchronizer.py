import mock
import pytest

from cvfm import models


@pytest.fixture
def vpg_service():
    return mock.Mock()


@pytest.fixture
def vm_service():
    return mock.Mock()


def test_sync_create(vpg_synchronizer, vm_service, vpg_service, vm_model):
    vm_model_2 = models.VirtualMachineModel(
        "vm-2", "esxi-1", vm_model.dpg_models
    )
    vm_service.get_all_vm_models.return_value = [vm_model, vm_model_2]
    vpg_service.create_vpg_models.side_effect = [
        models.VirtualPortGroupModel.from_vm_model(vm_model),
        models.VirtualPortGroupModel.from_vm_model(vm_model_2),
    ]

    vpg_synchronizer.sync_create()

    vpg_service.create_vpg_in_vnc.assert_called_once()
    vpg_model = vpg_service.create_vpg_in_vnc.call_args[0][0]
    vpg_service.attach_pis_to_vpg.assert_called_with(vpg_model)
