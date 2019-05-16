import mock
import pytest
import yaml
import os

from tests.functional.vnc_api_test_client import VNCAPITestClient

from cvfm.controllers import VmwareController
from cvfm.services import DistributedPortGroupService
from cvfm.clients import VNCAPIClient

# imports fixtures from sample_topologies.py file
from sample_topologies import *


@pytest.fixture
def config():
    current_path = os.path.realpath(__file__)
    current_dir = os.path.dirname(current_path)
    config_path = os.path.join(current_dir, "config.yaml")
    with open(config_path, "r") as ymlfile:
        return yaml.load(ymlfile)["vnc"]


@pytest.fixture
def lock():
    semaphore = mock.Mock()
    semaphore.__enter__ = mock.Mock()
    semaphore.__exit__ = mock.Mock()
    return semaphore


@pytest.fixture
def vnc_api_client(config):
    return VNCAPIClient(config)


@pytest.fixture
def vnc_test_client(config):
    test_client = VNCAPITestClient(config)
    yield test_client
    test_client.tear_down()


@pytest.fixture
def dpg_service(vnc_api_client):
    return DistributedPortGroupService(None, vnc_api_client, None)


@pytest.fixture
def vmware_controller(update_handler, lock):
    return VmwareController(
        vm_service=None,
        vmi_service=None,
        dpg_service=None,
        update_handler=update_handler,
        lock=lock,
    )


@pytest.fixture
def minimalistic_topology(vnc_test_client):
    """
    Topology:
        esxi-1:port-1:dvs-1:pi-1:pr-1

        esxi-1:
            name: esxi-1
            ip: 10.10.10.11
        port-1:
            name: eth0
            mac_address: 11:22:33:44:55:01
        dvs-1:
            name: dvs-1
        pi-1:
            name: xe-0/0/0
            mac_address: 11:22:33:44:55:02
        pr-1:
            name: qfx-1
    """
    pr = vnc_test_client.create_physical_router("qfx-1")
    pi = vnc_test_client.create_physical_interface(
        "xe-0/0/0", "11:22:33:44:55:02", pr
    )
    node = vnc_test_client.create_node("esxi-1", "10.10.10.11")
    port = vnc_test_client.create_port(
        "eth0", "11:22:33:44:55:01", node, ["dvs-1"]
    )
    vnc_test_client.add_port_to_physical_interface(pi, port)
