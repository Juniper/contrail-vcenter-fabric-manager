import os

import mock
import pytest
import yaml

from cvfm import services
from cvfm.clients import VNCAPIClient

from cvfm.controllers import VmwareController
from cvfm import database as db

# imports fixtures from sample_topologies.py file
from sample_topologies import *
from tests import utils
from tests.functional.vnc_api_test_client import VNCAPITestClient


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
def fabric_vn(vnc_test_client):
    return utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-1", "dvportgroup-1"
    )


@pytest.fixture
def database():
    return db.Database()


@pytest.fixture
def vcenter_api_client():
    return mock.Mock()


@pytest.fixture
def vmi_service(vcenter_api_client, vnc_api_client, database):
    return services.VirtualMachineInterfaceService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def vpg_service(vcenter_api_client, vnc_api_client, database):
    return services.VirtualPortGroupService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def dpg_service(vcenter_api_client, vnc_api_client, database):
    return services.DistributedPortGroupService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def vm_service(vcenter_api_client, vnc_api_client, database):
    return services.VirtualMachineService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def vmware_controller(update_handler, lock):
    return VmwareController(
        vm_service=None,
        vmi_service=None,
        dpg_service=None,
        update_handler=update_handler,
        lock=lock,
    )
