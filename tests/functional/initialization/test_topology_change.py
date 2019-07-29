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
def vmware_dpg_2():
    net_data = {
        "key": "dvportgroup-2",
        "name": "dpg-2",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-2",
        "vlan": 6,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm(vmware_dpg):
    networks = [vmware_dpg]
    return utils.create_vmware_vm("vm-1", "esxi-1", networks)


@pytest.fixture
def vmware_vm_2(vmware_dpg_2):
    networks = [vmware_dpg_2]
    return utils.create_vmware_vm("vm-2", "esxi-1", networks)


def test_update_pis(
    topology_with_two_nodes,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_dpg,
    vmware_dpg_2,
    vmware_vm,
    vmware_vm_2,
):
    # User creates a DPG (dpg-1 under dvs-1) and the event is properly handled
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)

    # dpg-1 should be created in VNC
    created_vn = vnc_test_client.read_vn(models.generate_uuid(vmware_dpg.key))
    assert created_vn is not None

    # User creates a VM (vm-1) in dpg-1 and the event properly handled
    vm_created_update = vcenter_api_client.create_vm(vmware_vm)
    vmware_controller.handle_update(vm_created_update)

    # VPG (esxi-1_dvs-1) should be created in VNC and connected to the
    # existing PI
    previous_vpg = vnc_test_client.read_vpg(
        models.generate_uuid("esxi-1_dvs-1")
    )
    utils.verify_vnc_vpg(previous_vpg, pi_names=["xe-0/0/0"])

    # CVFM shuts down
    # The topology changes - existing PI's port is now connected to dvs-2
    # Another PI and Port is created for esxi-1 - dvs-1 connection
    port = vnc_test_client.read_port(fq_name=["default-global-system-config", "esxi-1", "eth1"])
    pi = vnc_test_client.read_physical_interface(fq_name=["default-global-system-config", "qfx-1", "xe-0/0/1"])
    vnc_test_client.update_ports_dvs_name(port.uuid, "dvs-2")
    pr = vnc_test_client.read_physical_router(pi.parent_uuid)
    new_pi = vnc_test_client.create_physical_interface(
        "xe-0/0/10", "11:22:33:44:55:04", pr
    )
    node = vnc_test_client.read_node(port.parent_uuid)
    new_port = vnc_test_client.create_port(
        "eth10", "11:22:33:44:55:03", node, "dvs-1"
    )
    vnc_test_client.add_port_to_physical_interface(new_pi, new_port)

    # CVFM starts up - sync
    vmware_controller.sync()

    # VPG should be updated in VNC with the new PI
    current_vpg = vnc_test_client.read_vpg(previous_vpg.uuid)
    utils.verify_vnc_vpg(current_vpg, pi_names=["xe-0/0/10"])

    # User creates a DPG (dpg-2 under dvs-2) and the event is properly handled
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)

    # User creates a VM (vm-2) in dpg-2 and the event properly handled
    vm_created_update = vcenter_api_client.create_vm(vmware_vm_2)
    vmware_controller.handle_update(vm_created_update)

    # VPG esxi-1_dvs-2 and VMI esxi-1_dvs-2_dpg-2 should be created in VNC
    vnc_vpg = vnc_test_client.read_vpg(
        models.generate_uuid("esxi-1_dvs-2")
    )
    utils.verify_vnc_vpg(vnc_vpg, pi_names=["xe-0/0/1"], vmi_names=['esxi-1_dvs-2_dpg-2'])
    vnc_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-2_dpg-2")
    )
    assert vnc_vmi is not None

    # CVFM shuts down
    # The topology changes - esxi-1 has no longer ports for dvs-1 connection
    # eth10 port now is connected to dvs-2
    port = vnc_test_client.read_port(fq_name=["default-global-system-config", "esxi-1", "eth10"])
    vnc_test_client.update_ports_dvs_name(port.uuid, "dvs-2")

    # CVFM starts up - sync
    vmware_controller.sync()

    # VPG esxi-1_dvs-1 should be deleted from VNC
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))

    # VMI esxi-1_dvs-1_dpg-1 should be deleted from VNC
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-1"))
