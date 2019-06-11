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
        "dvs-name": "dvs-1",
        "vlan": 6,
    }
    return utils.create_vmware_net(net_data)


@pytest.fixture
def vmware_vm(vmware_dpg):
    networks = [vmware_dpg]
    return utils.create_vmware_vm("vm-1", "esxi-1", networks)


def test_vmi_sync_create(
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
    # VMI (esxi-1_dvs-1_dpg-1) should be created in VNC and should be
    # attached to VPG (esxi-1_dvs-1)
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


def test_vmi_exists(
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

    # VMI (esxi-1_dvs-1_dpg-1) should be created in VNC
    previous_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert previous_vmi is not None

    # CVFM shuts down
    # Nothing is changed in vCenter
    # CVFM starts up - sync
    vmware_controller.sync()

    # VMI should still be in VNC (not modified)
    current_vmi = vnc_test_client.read_vmi(previous_vmi.uuid)
    assert utils.not_touched_in_vnc(previous_vmi, current_vmi)


def test_update_vlan(
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

    # VMI (esxi-1_dvs-1_dpg-1) should be created in VNC
    previous_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert previous_vmi is not None

    # CVFM shuts down
    # User changes the VLAN ID of dpg-1 and the event is not handled
    vcenter_api_client.reconfigure_dpg(vmware_dpg, 6)

    # CVFM starts up - sync
    vmware_controller.sync()

    # VMI's VLAN ID should be updated in VNC
    current_vmi = vnc_test_client.read_vmi(previous_vmi.uuid)
    utils.verify_vnc_vmi(current_vmi, vlan=6)


def test_vpg_exists(
    minimalistic_topology,
    vmware_controller,
    vcenter_api_client,
    vnc_test_client,
    vmware_vm,
    vmware_dpg,
    vmware_dpg_2,
):
    # User creates a DPG (dpg-1) and the event is properly handled
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg)
    vmware_controller.handle_update(dpg_created_update)

    # User creates DPG (dpg-2) and the event is properly handled
    dpg_created_update = vcenter_api_client.create_dpg(vmware_dpg_2)
    vmware_controller.handle_update(dpg_created_update)

    # User creates a VM (vm-1) in dpg-1 and the event properly handled
    vm_created_update = vcenter_api_client.create_vm(vmware_vm)
    vmware_controller.handle_update(vm_created_update)

    # VMI (esxi-1_dvs-1_dpg-1) should be created in VNC
    previous_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert previous_vmi is not None

    previous_vpg = vnc_test_client.read_vpg(
        models.generate_uuid("esxi-1_dvs-1")
    )
    assert previous_vpg

    # CVFM shuts down

    # User connects vm-1 to dpg-2
    vcenter_api_client.add_interface(vmware_vm, vmware_dpg_2)

    # CVFM starts up - sync
    vmware_controller.sync()

    # VPG (esxi-1_dvs-1) should stay the same in VNC
    current_vpg = vnc_test_client.read_vpg(
        models.generate_uuid("esxi-1_dvs-1")
    )
    assert utils.not_deleted_from_vnc(previous_vpg, current_vpg)

    # VMI (esxi-1_dvs-1_dpg-2) should be created in VNC and should be
    # attached to VPG (esxi-1_dvs-1)
    created_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-2")
    )
    utils.verify_vnc_vmi(
        created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-2",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-2",
        vlan=6,
    )


def test_sync_delete(
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

    # User creates a VM (vm-1) in dpg-1 and the event is properly handled
    vm_created_update = vcenter_api_client.create_vm(vmware_vm)
    vmware_controller.handle_update(vm_created_update)

    created_vmi = vnc_test_client.read_vmi(
        models.generate_uuid("esxi-1_dvs-1_dpg-1")
    )
    assert created_vmi is not None

    # CVFM shuts down

    # Users deletes the VM (vm-1) and the event is not handled
    vcenter_api_client.remove_vm(vmware_vm)

    # CVFM starts up - sync
    vmware_controller.sync()

    # VMI (esxi-1_dvs-1_dpg-1) should be deleted from VNC
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vmi(models.generate_uuid("esxi-1_dvs-1_dpg-1"))

    # VPG (esxi-1_dvs-1) should also be deleted from VNC
    with pytest.raises(vnc_api.NoIdError):
        vnc_test_client.read_vpg(models.generate_uuid("esxi-1_dvs-1"))
