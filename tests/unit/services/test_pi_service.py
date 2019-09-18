import mock
import pytest
from vnc_api import vnc_api

from cvfm import services
from cvfm.exceptions import VNCPortValidationError


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
    return vnc_api.Node("esxi-1")


@pytest.fixture
def port(node):
    esxi_port_info = vnc_api.ESXIProperties(dvs_name="dvs-1")
    vnc_port = vnc_api.Port("port-1", node, esxi_port_info=esxi_port_info)
    vnc_port.physical_interface_back_refs = [{"uuid": "pi-1-uuid"}]
    return vnc_port


@pytest.fixture
def invalid_port(node):
    esxi_port_info = vnc_api.ESXIProperties()
    return vnc_api.Port("port-2", node, esxi_port_info=esxi_port_info)


@pytest.fixture
def fabric():
    fabric = vnc_api.Fabric("fabric-name")
    fabric.set_uuid("fabric-uuid-1")
    return fabric


@pytest.fixture
def physical_router(fabric):
    pr = vnc_api.PhysicalRouter("qfx-1")
    pr.set_uuid("pr-1-uuid")
    pr.add_fabric(fabric)
    return pr


@pytest.fixture
def physical_interface(physical_router):
    pi = vnc_api.PhysicalInterface("xe-0/0/1", physical_router)
    pi.set_uuid("pi-1-uuid")
    pi.parent_uuid = physical_router.uuid
    return pi


@pytest.fixture
def fabric_1():
    fabric_1 = vnc_api.Fabric(name="fabric_1")
    fabric_1.set_uuid("fabric-uuid-1")
    return fabric_1


@pytest.fixture
def fabric_2():
    fabric_2 = vnc_api.Fabric(name="fabric_2")
    fabric_2.set_uuid("fabric-uuid-2")
    return fabric_2


@pytest.fixture
def physical_router_1(fabric_1):
    pr = vnc_api.PhysicalRouter(name="pr-1-1")
    pr.set_uuid("pr-uuid-1-1")
    pr.add_fabric(fabric_1)
    return pr


@pytest.fixture
def physical_router_2(fabric_1):
    pr = vnc_api.PhysicalRouter(name="pr-1-2")
    pr.set_uuid("pr-uuid-1-2")
    pr.add_fabric(fabric_1)
    return pr


@pytest.fixture
def physical_router_3(fabric_2):
    pr = vnc_api.PhysicalRouter(name="pr-2-1")
    pr.set_uuid("pr-uuid-2-1")
    pr.add_fabric(fabric_2)
    return pr


@pytest.fixture
def physical_router_4():
    pr = vnc_api.PhysicalRouter(name="pr-2-2")
    pr.set_uuid("pr-uuid-2-2")
    return pr


def test_populate_db(
    pi_service,
    vcenter_api_client,
    vnc_api_client,
    database,
    host,
    node,
    port,
    invalid_port,
    physical_interface,
    physical_router,
):
    vcenter_api_client.get_all_hosts.return_value = [host]
    vnc_api_client.get_nodes_by_host_names.return_value = [node]
    vnc_api_client.get_node_ports.return_value = [port, invalid_port]
    vnc_api_client.get_pis_by_port.return_value = [physical_interface]
    vnc_api_client.read_all_physical_routers.return_value = [physical_router]

    pi_service.populate_db_with_pi_models()

    vpg_model = mock.Mock(host_name="esxi-1", dvs_name="dvs-1")
    pi_models = database.get_pi_models_for_vpg(vpg_model)
    assert len(pi_models) == 1
    assert pi_models[0].uuid == "pi-1-uuid"
    assert pi_models[0].fabric_uuid == "fabric-uuid-1"
    assert pi_models[0].host_name == "esxi-1"
    assert pi_models[0].dvs_name == "dvs-1"


def test_validate_vnc_port(port):
    services.validate_vnc_port(port)

    port.esxi_port_info.dvs_name = None
    with pytest.raises(VNCPortValidationError):
        services.validate_vnc_port(port)

    port.esxi_port_info = None
    with pytest.raises(VNCPortValidationError):
        services.validate_vnc_port(port)


def test_validate_port_pi_back_refs(port):
    services.validate_vnc_port(port)

    port.physical_interface_back_refs = None
    with pytest.raises(VNCPortValidationError):
        services.validate_vnc_port(port)


def test_populate_pr_to_fabric(
    pi_service,
    vnc_api_client,
    fabric_1,
    fabric_2,
    physical_router_1,
    physical_router_2,
    physical_router_3,
    physical_router_4,
):
    vnc_api_client.read_all_physical_routers.return_value = [
        physical_router_1,
        physical_router_2,
        physical_router_3,
        physical_router_4,
    ]

    pr_to_fabric = pi_service._populate_pr_to_fabric()

    expected_pr_to_fabric = {
        physical_router_1.uuid: fabric_1.uuid,
        physical_router_2.uuid: fabric_1.uuid,
        physical_router_3.uuid: fabric_2.uuid,
    }
    assert pr_to_fabric == expected_pr_to_fabric
