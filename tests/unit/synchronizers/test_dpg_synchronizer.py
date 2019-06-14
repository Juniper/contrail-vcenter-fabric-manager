import mock
import pytest

from cvfm import models


@pytest.fixture
def dpg_service():
    return mock.Mock()


def test_sync_create(dpg_synchronizer, dpg_service, vmware_dpg):
    dpg_model = models.DistributedPortGroupModel.from_vmware_dpg(vmware_dpg)
    dpg_service.get_all_dpg_models.return_value = [dpg_model]
    dpg_service.get_all_fabric_vns.return_value = []

    dpg_synchronizer.sync_create()

    dpg_service.create_fabric_vn.assert_called_once_with(dpg_model)
    dpg_service.populate_db_with_dpgs.assert_called_once()


def test_sync_delete(dpg_synchronizer, dpg_service, fabric_vn):
    dpg_service.get_all_dpg_models.return_value = []
    dpg_service.get_all_fabric_vns.return_value = [fabric_vn]

    dpg_synchronizer.sync_delete()

    dpg_service.delete_fabric_vn.assert_called_once_with(fabric_vn.uuid)
