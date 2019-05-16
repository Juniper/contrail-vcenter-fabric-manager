import mock
import pytest

from vnc_api import vnc_api

from cvfm import models
from cvfm.services import DistributedPortGroupService
from cvfm import constants as const

from tests.utils import prepare_annotations


@pytest.fixture
def vnc_api_client(project):
    client = mock.Mock()
    client.get_project.return_value = project
    return client


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
    dpg_model = models.DistributePortGroupModel(
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


def test_create_dpg_model_with_vpg_creation_in_vnc(
    dpg_service, vnc_api_client
):
    vnc_api_client.read_vpg.return_value = None

    vpg_model = models.VirtualPortGroupModel(
        models.generate_uuid("esxi-1_dvs-1"), "esxi-1", "dvs-1"
    )
    dpg_service.create_vpg_in_vnc(vpg_model)

    vnc_api_client.read_vpg.assert_called_once()
    vnc_api_client.create_vpg.assert_called_once()


def test_create_dpg_model_without_vpg_creation_in_vnc(
    dpg_service, vnc_api_client
):
    vnc_api_client.read_vpg.return_value = mock.Mock()

    vpg_model = models.VirtualPortGroupModel(
        models.generate_uuid("esxi-1_dvs-1"), "esxi-1", "dvs-1"
    )
    dpg_service.create_vpg_in_vnc(vpg_model)

    vnc_api_client.read_vpg.assert_called_once()
    vnc_api_client.create_vpg.assert_not_called()


def test_is_dvs_in_port_annotations(dpg_service):
    port = vnc_api.Port(name="eth0")
    raw_annotations = {
        "DVS1": const.DVS_ANNOTATION,
        "DVS2": const.DVS_ANNOTATION,
        "DVS3": "different_" + const.DVS_ANNOTATION,
    }
    port.annotations = prepare_annotations(raw_annotations)
    assert dpg_service.is_dvs_in_port_annotations(port, "DVS1")
    assert dpg_service.is_dvs_in_port_annotations(port, "DVS2")
    assert not dpg_service.is_dvs_in_port_annotations(port, "DVS3")


def test_filter_node_ports_by_dvs_name(dpg_service):
    port_1 = vnc_api.Port(name="eth1")
    port_1_raw_annotations = {
        "DVS1": const.DVS_ANNOTATION,
        "DVS2": const.DVS_ANNOTATION,
    }
    port_1.annotations = prepare_annotations(port_1_raw_annotations)
    port_2 = vnc_api.Port(name="eth2")
    port_2_raw_annotations = {
        "DVS2": const.DVS_ANNOTATION,
        "DVS3": const.DVS_ANNOTATION,
    }
    port_2.annotations = prepare_annotations(port_2_raw_annotations)
    port_3 = vnc_api.Port(name="eth3")
    port_3_raw_annotations = {"DVS1": const.DVS_ANNOTATION}
    port_3.annotations = prepare_annotations(port_3_raw_annotations)
    ports = [port_1, port_2, port_3]

    assert dpg_service.filter_node_ports_by_dvs_name(ports, "DVS1") == [
        port_1,
        port_3,
    ]
    assert dpg_service.filter_node_ports_by_dvs_name(ports, "DVS2") == [
        port_1,
        port_2,
    ]
    assert dpg_service.filter_node_ports_by_dvs_name(ports, "DVS3") == [port_2]
    assert dpg_service.filter_node_ports_by_dvs_name(ports, "DVS4") == []
