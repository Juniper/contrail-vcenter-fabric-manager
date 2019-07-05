import mock
import pytest
from vnc_api import vnc_api

from cvfm import services
from cvfm.exceptions import (
    VNCPortValidationException,
    VNCNodeValidationException,
)


@pytest.fixture
def pi_service(vcenter_api_client, vnc_api_client, database):
    return services.PhysicalInterfaceService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def host():
    h = mock.Mock()
    h.configure_mock(name="esxi-1")
    return h


@pytest.fixture
def node():
    esxi_info = vnc_api.ESXIHostInfo(esxi_name="esxi-1")
    return vnc_api.Node("node-1", esxi_info=esxi_info)


@pytest.fixture
def port(node):
    esxi_port_info = vnc_api.ESXIProperties(dvs_name="dvs-1")
    return vnc_api.Port("port-1", node, esxi_port_info=esxi_port_info)


@pytest.fixture
def physical_router():
    vnc_api.PhysicalRouter("qfx-1")


@pytest.fixture
def physical_interface(physical_router):
    pi = vnc_api.PhysicalInterface("xe-0/0/1", physical_router)
    pi.set_uuid("pi-1-uuid")
    return pi


def test_populate_db(
    pi_service,
    vcenter_api_client,
    vnc_api_client,
    database,
    host,
    node,
    port,
    physical_interface,
):
    vcenter_api_client.get_all_hosts.return_value = [host]
    vnc_api_client.get_nodes_by_host_names.return_value = [node]
    vnc_api_client.get_node_ports.return_value = [port]
    vnc_api_client.get_pis_by_port.return_value = [physical_interface]

    pi_service.populate_db_with_pi_models()

    vpg_model = mock.Mock(host_name="esxi-1", dvs_name="dvs-1")
    pi_models = database.get_pi_models_for_vpg(vpg_model)
    assert len(pi_models) == 1
    assert pi_models[0].uuid == "pi-1-uuid"
    assert pi_models[0].host_name == "esxi-1"
    assert pi_models[0].dvs_name == "dvs-1"


def test_validate_vnc_port(port):
    services.validate_vnc_port(port)

    port.esxi_port_info.dvs_name = None
    with pytest.raises(VNCPortValidationException):
        services.validate_vnc_port(port)

    port.esxi_port_info = None
    with pytest.raises(VNCPortValidationException):
        services.validate_vnc_port(port)
