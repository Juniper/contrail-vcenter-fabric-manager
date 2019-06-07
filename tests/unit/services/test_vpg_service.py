import mock
import pytest
from vnc_api import vnc_api

from cvfm import models
from cvfm.services import VirtualPortGroupService


@pytest.fixture
def vpg_service(vnc_api_client, database):
    return VirtualPortGroupService(None, vnc_api_client, database)


@pytest.fixture
def port():
    esxi_port_info = vnc_api.ESXIProperties(dvs_name="dvs-1")
    return vnc_api.Port(esxi_port_info=esxi_port_info)


def test_create_vpg_models(vpg_service, vm_model):
    vpg_models = vpg_service.create_vpg_models(vm_model)

    assert len(vpg_models) == 1
    assert vpg_models[0].uuid == models.generate_uuid("esxi-1_dvs-1")
    assert vpg_models[0].host_name == "esxi-1"
    assert vpg_models[0].dvs_name == "dvs-1"


def test_create_dpg_model_with_vpg_creation_in_vnc(
    vpg_service, vnc_api_client
):
    vnc_api_client.read_vpg.return_value = None
    fabric_mock = mock.Mock()
    fabric_mock.fq_name = ["a", "b"]
    vnc_api_client.get_fabric.return_value = fabric_mock

    vpg_model = models.VirtualPortGroupModel(
        models.generate_uuid("esxi-1_dvs-1"), "esxi-1", "dvs-1"
    )
    vpg_service.create_vpg_in_vnc(vpg_model)

    vnc_api_client.read_vpg.assert_called_once()
    vnc_api_client.create_vpg.assert_called_once()


def test_create_dpg_model_without_vpg_creation_in_vnc(
    vpg_service, vnc_api_client
):
    vnc_api_client.read_vpg.return_value = mock.Mock()

    vpg_model = models.VirtualPortGroupModel(
        models.generate_uuid("esxi-1_dvs-1"), "esxi-1", "dvs-1"
    )
    vpg_service.create_vpg_in_vnc(vpg_model)

    vnc_api_client.read_vpg.assert_called_once()
    vnc_api_client.create_vpg.assert_not_called()


def test_filter_node_ports_by_dvs_name(vpg_service):
    port_1 = vnc_api.Port(name="eth1")
    port_1.esxi_port_info = vnc_api.ESXIProperties(dvs_name="dvs-1")

    port_2 = vnc_api.Port(name="eth2")
    port_2.esxi_port_info = vnc_api.ESXIProperties(dvs_name="dvs-1")

    port_3 = vnc_api.Port(name="eth3")
    port_3.esxi_port_info = vnc_api.ESXIProperties(dvs_name="dvs-2")

    ports = [port_1, port_2, port_3]

    assert vpg_service.filter_node_ports_by_dvs_name(ports, "dvs-1") == [
        port_1,
        port_2,
    ]
    assert vpg_service.filter_node_ports_by_dvs_name(ports, "dvs-2") == [
        port_3
    ]


def test_prune_empty_vpgs(vpg_service, vnc_api_client):
    vpg_1_uuid = models.generate_uuid("esxi-1_dvs-1")
    vpg_1 = mock.Mock(uuid=vpg_1_uuid)
    vpg_1.get_virtual_machine_interface_refs.return_value = [
        {"uuid": "vmi-uuid-1"}
    ]
    vpg_2_uuid = models.generate_uuid("esxi-2_dvs-1")
    vpg_2 = mock.Mock(uuid=vpg_2_uuid)
    vpg_2.get_virtual_machine_interface_refs.return_value = None
    vnc_api_client.read_vpg.side_effect = [vpg_1, vpg_2]

    vpg_service.prune_empty_vpgs([vpg_1_uuid, vpg_2_uuid])

    vnc_api_client.delete_vpg.assert_called_once_with(vpg_2_uuid)


def test_find_affected_vpgs(vpg_service, vnc_api_client):
    vnc_vmi_1 = mock.Mock()
    vnc_vmi_2 = mock.Mock()
    vpg_uuid_1 = models.generate_uuid("esxi-1_dvs-1")
    vpg_uuid_2 = models.generate_uuid("esxi-2_dvs-1")
    vnc_vmi_1.get_virtual_port_group_back_refs.return_value = [
        {"uuid": vpg_uuid_1}
    ]
    vnc_vmi_2.get_virtual_port_group_back_refs.return_value = [
        {"uuid": vpg_uuid_1},
        {"uuid": vpg_uuid_2},
    ]
    vnc_api_client.read_vmi.side_effect = [vnc_vmi_1, vnc_vmi_2]
    vmi_models = [mock.Mock(), mock.Mock()]

    vpg_uuids = vpg_service.find_affected_vpgs(vmi_models)

    assert vpg_uuids == {vpg_uuid_1, vpg_uuid_2}
