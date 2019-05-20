import mock
import pytest
from vnc_api import vnc_api
from pyVmomi import vim

from cvfm import models


@pytest.fixture
def vnc_vmi(vnc_api_client, fabric_vn):
    project = vnc_api_client.get_project()
    vmi = vnc_api.VirtualMachineInterface(
        name="esxi-1_dvs-1_dpg-1", parent_obj=project
    )
    vmip = vnc_api.VirtualMachineInterfacePropertiesType(
        sub_interface_vlan_tag=5
    )
    vmi.set_virtual_machine_interface_properties(vmip)
    vmi.add_virtual_network(fabric_vn)
    vmi.set_uuid(models.generate_uuid(vmi.name))
    vnc_api_client.create_vmi(vmi)
    return vnc_api_client.read_vmi(vmi.uuid)


@pytest.fixture
def vnc_vpg(vnc_api_client, vnc_vmi):
    vpg = vnc_api.VirtualPortGroup(name="esxi-1_dvs-1")
    vpg.set_virtual_machine_interface(vnc_vmi)
    vnc_api_client.create_vpg(vpg)
    return vnc_api_client.read_vpg(vpg.uuid)


@pytest.fixture
def vm_removed_event():
    event = mock.Mock(spec=vim.event.VmRemovedEvent())
    event.vm.name = "vm-1"
    event.host.name = "esxi-1"


def test_last_vm_from_pg(
    minimalistic_topology,
    fabric_vn,
    vnc_vpg,
    vnc_vmi,
    vm_removed_event,
    vnc_test_client,
):
    pi = vnc_test_client.vnc_lib.physical_interface_read(
        ["default-global-system-config", "qfx-1", "xe-0/0/0"]
    )
    vnc_vpg.set_physical_interface(pi)
    # TODO: Remove these asserts, finish the test
    assert (
        vnc_test_client.vnc_lib.virtual_machine_interface_read(id=vnc_vmi.uuid)
        is not None
    )
    assert (
        vnc_test_client.vnc_lib.virtual_port_group_read(id=vnc_vpg.uuid)
        is not None
    )


def test_last_vm_on_host(
    minimalistic_topology, fabric_vn, vnc_vpg, vnc_vmi, vm_removed_event
):
    pass


def test_vms_remaining_in_pg(
    minimalistic_topology, fabric_vn, vnc_vpg, vnc_vmi, vm_removed_event
):
    pass
