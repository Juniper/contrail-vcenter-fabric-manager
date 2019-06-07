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
    pi = mock.Mock()
    vpg_service.find_pis_for_vpg.return_value = [pi]

    vpg_synchronizer.sync_create()

    vpg_model = vpg_service.find_pis_for_vpg.call_args[0][0]
    vpg_service.create_vpg_with_pis_in_vnc.assert_called_once_with(
        vpg_model, [pi]
    )
