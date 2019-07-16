import mock
import pytest
from vnc_api import vnc_api

from cvfm import models, constants


@pytest.fixture
def vnc_fabric():
    fabric = vnc_api.Fabric("fabric-name")
    fabric.set_uuid("fabric-uuid-1")
    return fabric


@pytest.fixture
def vpg_service():
    return mock.Mock()


@pytest.fixture
def vm_service():
    return mock.Mock()


@pytest.fixture
def pi_service():
    return mock.Mock()


def test_sync_create(
    vpg_synchronizer, vm_service, vpg_service, vm_model, pi_service
):
    vm_model_2 = models.VirtualMachineModel(
        "vm-2", "uuid-2", "esxi-1", vm_model.dpg_models
    )
    vm_service.get_all_vm_models.return_value = [vm_model, vm_model_2]
    vpg_service.create_vpg_models.side_effect = [
        models.VirtualPortGroupModel.from_vm_model(vm_model),
        models.VirtualPortGroupModel.from_vm_model(vm_model_2),
    ]
    pi_service.get_pi_models_for_vpg.return_value = [mock.Mock()]

    vpg_synchronizer.sync_create()

    vpg_model = vpg_service.create_vpg_in_vnc.call_args[0][0]
    pi_service.get_pi_models_for_vpg.assert_called_once_with(vpg_model)


def test_sync_delete(
    vpg_synchronizer, vm_service, vpg_service, vm_model, vnc_fabric
):
    vm_service.get_all_vm_models.return_value = [vm_model]
    vpg_service.create_vpg_models.return_value = models.VirtualPortGroupModel.from_vm_model(
        vm_model
    )
    vpg_1 = models.VirtualPortGroupModel.from_vm_model(vm_model)[0].to_vnc_vpg(
        vnc_fabric
    )
    vpg_2 = mock.Mock(uuid="vpg-2-uuid")
    vpg_2.get_id_perms.return_value = constants.ID_PERMS
    vpg_service.read_all_vpgs.return_value = [vpg_1, vpg_2]

    vpg_synchronizer.sync_delete()

    vpg_service.delete_vpg.assert_called_once_with(vpg_2.uuid)
