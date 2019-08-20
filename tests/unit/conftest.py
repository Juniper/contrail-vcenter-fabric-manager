import mock
import pytest
from pyVmomi import vim
from vnc_api import vnc_api

from cvfm import database as db, synchronizers
from cvfm import models

collect_ignore = []
try:
    import pysandesh
    import sandesh_common
    import cfgm_common
except ImportError:
    collect_ignore.append("parser/test_parser.py")
    collect_ignore.append("context/test_context.py")
    collect_ignore.append("clients/test_vnc_rabbit_client.py")


@pytest.fixture
def vmware_dpg():
    dpg = mock.Mock(spec=vim.DistributedVirtualPortgroup)
    dpg.configure_mock(name="dpg-1")
    dpg.key = "dvportgroup-1"
    dpg.config.distributedVirtualSwitch.name = "dvs-1"
    dpg.config.defaultPortConfig.vlan.vlanId = 5
    return dpg


@pytest.fixture
def vmware_dpg_2():
    dpg = mock.Mock(spec=vim.DistributedVirtualPortgroup)
    dpg.configure_mock(name="dpg-2")
    dpg.key = "dvportgroup-2"
    dpg.config.distributedVirtualSwitch.name = "dvs-1"
    dpg.config.defaultPortConfig.vlan.vlanId = 15
    return dpg


@pytest.fixture
def vmware_network():
    net = mock.Mock(spec=vim.Network)
    net.configure_mock(name="network-1")
    net.key = "network-1"
    return net


@pytest.fixture
def vmware_vm(vmware_dpg, vmware_network):
    vm = mock.Mock()
    vm.configure_mock(name="vm-1")
    vm.config.instanceUuid = "uuid-1"
    vm.network = [vmware_dpg, vmware_network]
    vm.runtime.host.name = "esxi-1"
    return vm


@pytest.fixture
def vmware_vm_2(vmware_dpg_2):
    vm = mock.Mock()
    vm.configure_mock(name="vm-2")
    vm.config.instanceUuid = "uuid-2"
    vm.network = [vmware_dpg_2]
    vm.runtime.host.name = "esxi-1"
    return vm


@pytest.fixture
def dpg_model(vmware_dpg):
    return models.DistributedPortGroupModel.from_vmware_dpg(vmware_dpg)


@pytest.fixture
def dpg_model_2(vmware_dpg_2):
    return models.DistributedPortGroupModel.from_vmware_dpg(vmware_dpg_2)


@pytest.fixture
def vm_model(vmware_vm, dpg_model):
    dpg_models = {dpg_model}
    vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm, dpg_models)
    property_filter = mock.Mock(spec=vim.PropertyFilter)
    vm_model.set_property_filter(property_filter)
    return vm_model


@pytest.fixture
def vm_model_2(vmware_vm_2, dpg_model_2):
    dpg_models = {dpg_model_2}
    vm_model = models.VirtualMachineModel.from_vmware_vm(
        vmware_vm_2, dpg_models
    )
    property_filter = mock.Mock(spec=vim.PropertyFilter)
    vm_model.set_property_filter(property_filter)
    return vm_model


@pytest.fixture
def vpg_model(vm_model):
    return models.VirtualPortGroupModel.from_vm_model(vm_model)[0]


@pytest.fixture
def pi_model():
    return models.PhysicalInterfaceModel(
        uuid="pi-1-uuid",
        fabric_uuid="fabric-uuid-1",
        host_name="esxi-1",
        dvs_name="dvs-1",
    )


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


@pytest.fixture
def vcenter_api_client():
    return mock.Mock()


@pytest.fixture
def database():
    dbase = db.Database()
    dbase.add_supported_dvs("dvs-1")
    return dbase


@pytest.fixture
def dpg_synchronizer(dpg_service):
    return synchronizers.DistributedPortGroupSynchronizer(
        dpg_service=dpg_service
    )


@pytest.fixture
def vpg_synchronizer(vm_service, vpg_service, pi_service):
    return synchronizers.VirtualPortGroupSynchronizer(
        vm_service=vm_service, vpg_service=vpg_service, pi_service=pi_service
    )


@pytest.fixture
def vmi_synchronizer(vm_service, vmi_service):
    return synchronizers.VirtualMachineInterfaceSynchronizer(
        vm_service=vm_service, vmi_service=vmi_service
    )


@pytest.fixture
def vm_synchronizer(vm_service):
    return synchronizers.VirtualMachineSynchronizer(vm_service=vm_service)


@pytest.fixture
def dvs_synchronizer(dvs_service):
    return synchronizers.DistributedVirtualSwitchSynchronizer(
        dvs_service=dvs_service
    )


@pytest.fixture
def pi_synchronizer(pi_service):
    return synchronizers.PhysicalInterfaceSynchronizer(pi_service=pi_service)
