import os

import mock
import pytest

from cvfm import services, controllers, clients, synchronizers, parser
from cvfm import database as db

# imports fixtures from sample_topologies.py file
from sample_topologies import *
from tests.functional.vcenter_api_mock_client import VCenterAPIMockClient
from tests.functional.vnc_api_test_client import VNCAPITestClient


@pytest.fixture
def config():
    current_path = os.path.realpath(__file__)
    current_dir = os.path.dirname(current_path)
    config_path = os.path.join(current_dir, "cvfm.conf")
    config_parser = parser.CVFMArgumentParser()
    return config_parser.parse_args(["-c", config_path])["vnc_config"]


@pytest.fixture
def lock():
    semaphore = mock.Mock()
    semaphore.__enter__ = mock.Mock()
    semaphore.__exit__ = mock.Mock()
    return semaphore


@pytest.fixture
def vnc_api_client(config):
    vnc_client = clients.VNCAPIClient(config)
    vnc_client.project_name = "test-vcenter-fabric"
    return vnc_client


@pytest.fixture
def vnc_test_client(config):
    test_client = VNCAPITestClient(config)
    yield test_client
    test_client.tear_down()


@pytest.fixture
def database():
    return db.Database()


@pytest.fixture
def vcenter_api_client():
    return VCenterAPIMockClient()


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
def dvs_service(vcenter_api_client, vnc_api_client, database):
    return services.DistributedVirtualSwitchService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def pi_service(vcenter_api_client, vnc_api_client, database):
    return services.PhysicalInterfaceService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def update_handler(
    vm_service, vmi_service, dpg_service, vpg_service, pi_service
):
    dpg_created_handler = controllers.DVPortgroupCreatedHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    dpg_reconfigured_handler = controllers.DVPortgroupReconfiguredHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    dpg_renamed_handler = controllers.DVPortgroupRenamedHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    dpg_destroyed_handler = controllers.DVPortgroupDestroyedHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    vm_updated_handler = controllers.VmUpdatedHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    vm_reconfigured_handler = controllers.VmReconfiguredHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    vm_renamed_handler = controllers.VmRenamedHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    vm_removed_handler = controllers.VmRemovedHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    host_change_handler = controllers.HostChangeHandler(
        vm_service, vmi_service, dpg_service, vpg_service, pi_service
    )
    handlers = [
        dpg_created_handler,
        dpg_reconfigured_handler,
        dpg_renamed_handler,
        dpg_destroyed_handler,
        vm_updated_handler,
        vm_reconfigured_handler,
        vm_renamed_handler,
        vm_removed_handler,
        host_change_handler,
    ]
    return controllers.UpdateHandler(handlers)


@pytest.fixture
def dpg_synchronizer(dpg_service):
    return synchronizers.DistributedPortGroupSynchronizer(dpg_service)


@pytest.fixture
def vpg_synchronizer(vm_service, vpg_service, pi_service):
    return synchronizers.VirtualPortGroupSynchronizer(
        vm_service, vpg_service, pi_service
    )


@pytest.fixture
def vm_synchronizer(vm_service):
    return synchronizers.VirtualMachineSynchronizer(vm_service)


@pytest.fixture
def vmi_synchronizer(vm_service, vmi_service):
    return synchronizers.VirtualMachineInterfaceSynchronizer(
        vm_service, vmi_service
    )


@pytest.fixture
def dvs_synchronizer(dvs_service):
    return synchronizers.DistributedVirtualSwitchSynchronizer(dvs_service)


@pytest.fixture
def pi_synchronizer(pi_service):
    return synchronizers.PhysicalInterfaceSynchronizer(pi_service)


@pytest.fixture
def synchronizer(
    database,
    vm_synchronizer,
    dpg_synchronizer,
    vpg_synchronizer,
    vmi_synchronizer,
    dvs_synchronizer,
    pi_synchronizer,
):
    return synchronizers.CVFMSynchronizer(
        database,
        vm_synchronizer,
        dpg_synchronizer,
        vpg_synchronizer,
        vmi_synchronizer,
        dvs_synchronizer,
        pi_synchronizer,
    )


@pytest.fixture
def vmware_controller(synchronizer, update_handler, lock):
    controller = controllers.VmwareController(
        synchronizer=synchronizer, update_handler=update_handler, lock=lock
    )
    controller.sync()
    return controller
