import mock
import pytest
from pyVmomi import vim

from cvfm import models
from tests import utils
from vnc_api.vnc_api import VirtualNetwork

from cvfm.controllers import UpdateHandler, VmUpdatedHandler, VmwareController
from cvfm import services


@pytest.fixture
def vmi_service(vnc_api_client):
    return services.VirtualMachineInterfaceService(None, vnc_api_client, None)


@pytest.fixture
def dpg_service(vnc_api_client):
    return services.DistributedPortGroupService(None, vnc_api_client, None)


@pytest.fixture
def update_handler(vmi_service, dpg_service):
    vm_updated_handler = VmUpdatedHandler(None, vmi_service, dpg_service)
    return UpdateHandler([vm_updated_handler])


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
def fabric_vn(vnc_test_client):
    project = vnc_test_client.vnc_lib.project_read(
        ["default-domain", vnc_test_client.project_name]
    )
    fab_vn = VirtualNetwork(name="dvs-1_dpg-1", parent_obj=project)
    fab_vn.set_uuid(models.generate_uuid("dvportgroup-1"))
    vnc_test_client.vnc_lib.virtual_network_create(fab_vn)


@pytest.fixture
def vm_created_update():
    portgroups = [
        {
            "key": "dvportgroup-1",
            "name": "dpg-1",
            "dvs-name": "dvs-1",
            "vlan": 5,
        }
    ]
    return utils.create_vm_created_update(
        vm_name="VM1", vm_host_name="esxi-1", vm_portgroups=portgroups
    )


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
def vm_created_update(vmware_vm):
    event = mock.Mock(spec=vim.event.VmCreatedEvent())
    event.vm.vm = vmware_vm
    return utils.wrap_into_update_set(event=event)


def test_vm_created(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vm_created_update,
    fabric_vn,
):
    vmware_controller.handle_update(vm_created_update)

    created_vpg = vnc_test_client.vnc_lib.virtual_port_group_read(
        id=models.generate_uuid("esxi-1_dvs-1")
    )
    created_vmi = vnc_test_client.vnc_lib.virtual_machine_interface_read(
        id=models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )

    assert created_vpg is not None
    utils.verify_vnc_vpg(
        vnc_vpg=created_vpg,
        vpg_name="esxi-1_dvs-1",
        pi_names=["xe-0/0/0"],
        vmi_names=["esxi-1_dvs-1_dpg-1"],
    )

    assert created_vmi is not None
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )
