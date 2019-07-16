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


@pytest.fixture
def fabric():
    fabric_mock = mock.Mock()
    fabric_mock.fq_name = ["global-config", "fabric_name"]
    fabric_mock.uuid = "fabric-uuid"
    return fabric_mock


@pytest.fixture
def pi_model():
    return models.PhysicalInterfaceModel(
        "pi-1-uuid", "fabric-uuid", "esxi-1", "dvs-1"
    )


def test_create_vpg_models(vpg_service, vm_model):
    vpg_models = vpg_service.create_vpg_models(vm_model)

    assert len(vpg_models) == 1
    assert vpg_models[0].uuid == models.generate_uuid("esxi-1_dvs-1")
    assert vpg_models[0].host_name == "esxi-1"
    assert vpg_models[0].dvs_name == "dvs-1"


def test_create_dpg_model_with_vpg_creation_in_vnc(
    vpg_service, vnc_api_client, pi_model, fabric
):
    vnc_api_client.read_vpg.return_value = None
    vnc_api_client.read_fabric.return_value = fabric

    vpg_model = models.VirtualPortGroupModel(
        models.generate_uuid("esxi-1_dvs-1"), "esxi-1", "dvs-1"
    )
    vpg_service.create_vpg_in_vnc(vpg_model, [pi_model])

    vnc_api_client.read_vpg.assert_called_once()
    vnc_api_client.read_fabric.assert_called_once_with(pi_model.fabric_uuid)
    vnc_api_client.create_vpg.assert_called_once()


def test_create_dpg_model_without_vpg_creation_in_vnc(
    vpg_service, vnc_api_client, pi_model
):
    vpg_mock = mock.Mock()
    vpg_mock.get_physical_interface_refs.return_value = []
    vnc_api_client.read_vpg.return_value = vpg_mock

    vpg_model = models.VirtualPortGroupModel(
        models.generate_uuid("esxi-1_dvs-1"), "esxi-1", "dvs-1"
    )
    vpg_service.create_vpg_in_vnc(vpg_model, [pi_model])

    vnc_api_client.read_vpg.assert_called_once()
    vnc_api_client.create_vpg.assert_not_called()


def test_update_pis(vpg_service, vnc_api_client, fabric):
    pr = vnc_api.PhysicalRouter("qfx-1")
    pi_1 = vnc_api.PhysicalInterface(name="pi-1", parent_obj=pr)
    pi_2 = vnc_api.PhysicalInterface(name="pi-2", parent_obj=pr)
    pi_3 = vnc_api.PhysicalInterface(name="pi-3", parent_obj=pr)
    pi_1.set_uuid("pi-1-uuid")
    pi_2.set_uuid("pi-2-uuid")
    pi_3.set_uuid("pi-3-uuid")
    previous_vpg = vnc_api.VirtualPortGroup(parent_obj=fabric)
    previous_vpg.add_physical_interface(pi_1)
    previous_vpg.add_physical_interface(pi_2)
    current_pis = [pi_2, pi_3]

    vpg_service.update_pis_for_vpg(previous_vpg, current_pis)

    vnc_api_client.detach_pis_from_vpg.assert_called_once_with(
        previous_vpg, ["pi-1-uuid"]
    )
    vnc_api_client.attach_pis_to_vpg.assert_called_once_with(
        previous_vpg, [pi_3]
    )


def test_update_pis_empty_refs(vpg_service, vnc_api_client, fabric):
    pr = vnc_api.PhysicalRouter("qfx-1")
    pi = vnc_api.PhysicalInterface(name="pi-1", parent_obj=pr)
    pi.set_uuid("pi-1-uuid")
    previous_vpg = vnc_api.VirtualPortGroup(parent_obj=fabric)
    current_pis = [pi]

    vpg_service.update_pis_for_vpg(previous_vpg, current_pis)

    vnc_api_client.detach_pis_from_vpg.assert_called_once_with(
        previous_vpg, []
    )
    vnc_api_client.attach_pis_to_vpg.assert_called_once_with(
        previous_vpg, [pi]
    )


def test_create_vpg_no_pis(vpg_model, vpg_service, vnc_api_client):
    pi_models = []

    vpg_service.create_vpg_in_vnc(vpg_model, pi_models)

    vnc_api_client.create_vpg.assert_not_called()


def test_create_vpg_in_vnc(
    vpg_model, vpg_service, vnc_api_client, database, fabric
):
    pr = vnc_api.PhysicalRouter("qfx-1")
    pi = vnc_api.PhysicalInterface(name="pi-1", parent_obj=pr)
    pi.set_uuid("pi-1-uuid")
    vnc_api_client.read_pi.return_value = pi
    vnc_api_client.read_vpg.return_value = None
    vnc_api_client.read_fabric.return_value = fabric
    pi_model = models.PhysicalInterfaceModel(
        "pi-1-uuid", "fabric-uuid", "esxi-1", "dvs-1"
    )
    database.add_pi_model(pi_model)
    pi_models = [pi_model]

    vpg_service.create_vpg_in_vnc(vpg_model, pi_models)

    vnc_api_client.create_vpg.assert_called_once()
    vnc_api_client.read_fabric.assert_called_once_with(pi_model.fabric_uuid)
    vnc_api_client.read_pi.assert_called_once_with("pi-1-uuid")
