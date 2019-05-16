import mock
import yaml
import pytest
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
