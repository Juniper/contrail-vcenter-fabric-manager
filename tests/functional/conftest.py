import mock
import pytest
import yaml
import os

from tests.functional.vnc_api_test_client import VNCAPITestClient

from cvfm.controllers import VmwareController
from cvfm import services
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
    vnc_client = VNCAPIClient(config)
    vnc_client.project_name = "test-vcenter-fabric"
    return vnc_client


@pytest.fixture
def vnc_test_client(config):
    test_client = VNCAPITestClient(config)
    yield test_client
    test_client.tear_down()


@pytest.fixture
def vmi_service(vnc_api_client):
    return services.VirtualMachineInterfaceService(None, vnc_api_client, None)


@pytest.fixture
def vpg_service(vnc_api_client):
    return services.VirtualPortGroupService(None, vnc_api_client, None)


@pytest.fixture
def dpg_service(vnc_api_client):
    return services.DistributedPortGroupService(None, vnc_api_client, None)


@pytest.fixture
def vm_service(vnc_api_client):
    return services.VirtualMachineService(None, vnc_api_client, None)


@pytest.fixture
def vmware_controller(update_handler, lock):
    return VmwareController(
        vm_service=None,
        vmi_service=None,
        dpg_service=None,
        update_handler=update_handler,
        lock=lock,
    )
