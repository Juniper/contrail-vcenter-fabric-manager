import mock
import pytest
from vnc_api import vnc_api


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
