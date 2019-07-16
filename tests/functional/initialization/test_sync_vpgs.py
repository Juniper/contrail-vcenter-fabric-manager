import pytest
from pyVmomi import vim
from vnc_api import vnc_api

from tests import utils

from cvfm import models, constants


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
def vnc_vpg(vnc_test_client):
    vpg = vnc_api.VirtualPortGroup(
        name="esxi-1_dvs-1", parent_obj=vnc_test_client.fabric
    )
    vpg.set_uuid(models.generate_uuid(vpg.name))
    vpg.set_id_perms(constants.ID_PERMS)
    return vpg


@pytest.fixture
def vmware_vm(vmware_dpg):
    networks = [vmware_dpg]
    return utils.create_vmware_vm("vm-1", "esxi-1", networks)


def test_vpg_sync_create(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_dpg,
    vmware_vm,
):
    # User creates a DPG (dpg-1) and the event is properly handled
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)

    # CVFM shuts down
    # User creates a VM (vm-1) in dpg-1 and the event is not handled
    vcenter_api_client.create_vm(vmware_vm)

    # CVFM starts up - sync
    vmware_controller.sync()

    # VPG (esxi-1_dvs-1) should be created in VNC
    created_vpg = vnc_test_client.read_vpg(
        models.generate_uuid("esxi-1_dvs-1")
    )
    assert created_vpg is not None


def test_vpg_exists(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_dpg,
    vmware_vm,
):
    # User creates a DPG (dpg-1) and the event is properly handled
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)

    # dpg-1 should be created in VNC
    created_vn = vnc_test_client.read_vn(models.generate_uuid(vmware_dpg.key))
    assert created_vn is not None

    # User creates a VM (vm-1) in dpg-1 and the event properly handled
    vm_created_update = vcenter_api_client.create_vm(vmware_vm)
    vmware_controller.handle_update(vm_created_update)

    # VPG (esxi-1_dvs-1) should be created in VNC
    previous_vpg = vnc_test_client.read_vpg(
        models.generate_uuid("esxi-1_dvs-1")
    )
    assert previous_vpg is not None

    # CVFM shuts down
    # Nothing is changed in vCenter
    # CVFM starts up - sync
    vmware_controller.sync()

    # VPG should still be in VNC (not modified)
    current_vpg = vnc_test_client.read_vpg(previous_vpg.uuid)
    assert utils.not_touched_in_vnc(previous_vpg, current_vpg)


def test_update_pis(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_dpg,
    vmware_vm,
):
    # User creates a DPG (dpg-1) and the event is properly handled
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
    existing_pi_uuid = vnc_test_client.read_all_physical_interface_uuids()[0]
    existing_pi = vnc_test_client.read_physical_interface(existing_pi_uuid)
    existing_port_uuid = existing_pi.get_port_refs()[0]["uuid"]
    vnc_test_client.update_ports_dvs_name(existing_port_uuid, "dvs-2")
    pr = vnc_test_client.read_physical_router(existing_pi.parent_uuid)
    new_pi = vnc_test_client.create_physical_interface(
        "xe-0/0/1", "11:22:33:44:55:04", pr
    )
    existing_port = vnc_test_client.read_port(existing_port_uuid)
    node = vnc_test_client.read_node(existing_port.parent_uuid)
    new_port = vnc_test_client.create_port(
        "eth1", "11:22:33:44:55:03", node, "dvs-1"
    )
    vnc_test_client.add_port_to_physical_interface(new_pi, new_port)

    # CVFM starts up - sync
    vmware_controller.sync()

    # VPG should be updated in VNC with the new PI
    current_vpg = vnc_test_client.read_vpg(previous_vpg.uuid)
    utils.verify_vnc_vpg(current_vpg, pi_names=["xe-0/0/1"])


def test_sync_delete(
    minimalistic_topology, vmware_controller, vnc_test_client, vnc_vpg
):
    # CVFM shuts down
    # Someone created VPG (esxi-1_dvs-1) in VNC
    vnc_test_client.create_vpg(vnc_vpg)

    # CVFM starts up - sync
    vmware_controller.sync()

    # Since there are no VMs or DPGs in vCenter, the VPG should be deleted
    # from VNC
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(vnc_vpg.uuid)
