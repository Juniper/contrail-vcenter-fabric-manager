import pytest
from pyVmomi import vim
from vnc_api import vnc_api

from tests import utils

from cvfm import models


@pytest.fixture
def vmware_dpg():
    net_data = {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 5,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm_1(vmware_dpg):
    networks = [vmware_dpg]
    return utils.create_vmware_vm("vm-1", "esxi-1", networks)


@pytest.fixture
def vmware_vm_2(vmware_dpg):
    networks = [vmware_dpg]
    return utils.create_vmware_vm("vm-2", "esxi-2", networks)


def test_pi_no_port_conn(
    topology_with_two_nodes,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_vm_1,
    vmware_vm_2,
    vmware_dpg,
):
    # There is a portgroup in vCenter (dpg-1)
    vcenter_api_client.create_dpg(vmware_dpg)

    # There are two VMs on two different ESXis (vm-1 and vm-2), connected to
    # dpg-1
    vcenter_api_client.create_vm(vmware_vm_1)
    vcenter_api_client.create_vm(vmware_vm_2)

    # PI of esxi-2 is not connected to the port
    pi = [
        pi
        for pi in vnc_test_client.read_all_physical_interfaces()
        if pi.name == "xe-0/0/2"
    ][0]
    vnc_test_client.remove_ports_from_physical_interface(pi)

    # Synchronization starts
    vmware_controller.sync()

    # The sync process should be successful for vm-1 and unsuccessful for vm-2
    created_vpg = vnc_test_client.read_vpg(
        models.generate_uuid("esxi-1_dvs-1")
    )
    assert created_vpg is not None
    created_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    utils.verify_vnc_vmi(
        created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-2_dvs-1"))

    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-2_dvs-1-dpg-1"))
