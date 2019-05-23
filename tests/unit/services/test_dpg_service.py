import pytest

from cvfm import models
from cvfm.services import DistributedPortGroupService


@pytest.fixture
def dpg_service(vnc_api_client):
    return DistributedPortGroupService(None, vnc_api_client, None)


def test_create_dpg_model(dpg_service, vmware_dpg):
    dpg_model = dpg_service.create_dpg_model(vmware_dpg)

    assert dpg_model.name == "dpg-1"
    assert dpg_model.uuid == "5a6bd262-1f96-3546-a762-6fa5260e9014"
    assert dpg_model.dvs_name == "dvs-1"
    assert dpg_model.vlan_id == 5


def test_create_fabric_vn(dpg_service, vnc_api_client, project):
    dpg_model = models.DistributedPortGroupModel(
        uuid="5a6bd262-1f96-3546-a762-6fa5260e9014",
        name="dpg-1",
        vlan_id=None,
        dvs_name="dvs-1",
    )

    dpg_service.create_fabric_vn(dpg_model)

    created_vn = vnc_api_client.create_vn.call_args[0][0]
    assert created_vn.name == "dvs-1_dpg-1"
    assert created_vn.uuid == "5a6bd262-1f96-3546-a762-6fa5260e9014"
    assert created_vn.parent_name == project.name


def test_is_vlan_changed(dpg_service, vnc_api_client):
    dpg_model = models.DistributedPortGroupModel(
        uuid="dpg-uuid", name="dpg-1", vlan_id=5, dvs_name="dvs-1"
    )

    vnc_api_client.get_vn_vlan.return_value = 15
    assert dpg_service.is_vlan_changed(dpg_model)

    vnc_api_client.get_vn_vlan.return_value = 5
    assert not dpg_service.is_vlan_changed(dpg_model)

    vnc_api_client.get_vn_vlan.return_value = None
    assert not dpg_service.is_vlan_changed(dpg_model)
