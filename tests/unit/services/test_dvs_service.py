import pytest

from vnc_api import vnc_api

from cvfm import services


@pytest.fixture
def dvs_service(vcenter_api_client, vnc_api_client, database):
    return services.DistributedVirtualSwitchService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def port_1():
    port = vnc_api.Port("port-1")
    esxi_port_info = vnc_api.ESXIProperties(dvs_name="dvs-1")
    port.set_esxi_port_info(esxi_port_info)
    return port


@pytest.fixture
def port_2():
    port = vnc_api.Port("port-2")
    esxi_port_info = vnc_api.ESXIProperties(dvs_name="dvs-2")
    port.set_esxi_port_info(esxi_port_info)
    return port


@pytest.fixture
def port_3():
    port = vnc_api.Port("port-2")
    esxi_port_info = vnc_api.ESXIProperties()
    port.set_esxi_port_info(esxi_port_info)
    return port


@pytest.fixture
def port_4():
    return vnc_api.Port("port-4")


def test_populate_db(
    dvs_service, database, vnc_api_client, port_1, port_2, port_3, port_4
):
    database.clear_database()
    vnc_api_client.read_all_ports.return_value = [
        port_1,
        port_2,
        port_3,
        port_4,
    ]

    dvs_service.populate_db_with_supported_dvses()

    assert database.is_dvs_supported("dvs-1") is True
    assert database.is_dvs_supported("dvs-2") is True
    assert database.is_dvs_supported("dvs-3") is False
