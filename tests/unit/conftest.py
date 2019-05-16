import mock
import pytest
from vnc_api import vnc_api


from cvfm import models


@pytest.fixture
def vmware_dpg():
    dpg = mock.Mock()
    dpg.configure_mock(name="dpg-1")
    dpg.key = "dvportgroup-1"
    dpg.config.distributedVirtualSwitch.name = "dvs-1"
    dpg.config.defaultPortConfig.vlan.vlanId = 5
    return dpg


@pytest.fixture
def vmware_vm(vmware_dpg):
    vm = mock.Mock()
    vm.network = [vmware_dpg]
    vm.runtime.host.name = "esxi-1"
    return vm


@pytest.fixture
def project():
    return vnc_api.Project()


@pytest.fixture
def fabric_vn(project):
    vn = vnc_api.VirtualNetwork(name="dvs-1_dpg-1", parent_obj=project)
    vn.set_uuid(models.generate_uuid("dvportgroup-1"))
    return vn


@pytest.fixture
def vnc_api_client(project):
    client = mock.Mock()
    client.get_project.return_value = project
    return client
