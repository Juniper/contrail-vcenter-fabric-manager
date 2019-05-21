import mock
import pytest

from pyVmomi import vim
from tests import utils

from cvfm import controllers


@pytest.fixture
def update_handler(dpg_service, vmi_service, vpg_service):
    vm_updated_handler = controllers.VmUpdatedHandler(
        None, vmi_service, None, vpg_service
    )
    dpg_reconfigured_handler = controllers.DVPortgroupReconfiguredHandler(
        None, None, dpg_service
    )
    return controllers.UpdateHandler(
        [vm_updated_handler, dpg_reconfigured_handler]
    )


@pytest.fixture
def fabric_vn(vnc_test_client):
    utils.create_fabric_network(
        vnc_test_client, "dvs-1_dpg-1", "dvportgroup-1"
    )


@pytest.fixture
def dpg_1():
    return {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 5,
    }


@pytest.fixture
def dpg_1_reconfigured():
    return {
        "key": "dvportgroup-1",
        "name": "dpg-1",
        "type": vim.DistributedVirtualPortgroup,
        "dvs-name": "dvs-1",
        "vlan": 15,
    }


@pytest.fixture
def vm_created_update_1(dpg_1):
    return utils.create_vm_created_update(
        vm_name="VM1", vm_host_name="esxi-1", vm_networks=[dpg_1]
    )


@pytest.fixture
def vm_created_update_2(dpg_1):
    return utils.create_vm_created_update(
        vm_name="VM2", vm_host_name="esxi-2", vm_networks=[dpg_1]
    )


@pytest.fixture
def dpg_reconfigured_update(dpg_1_reconfigured):
    event = mock.Mock(spec=vim.event.DVPortgroupCreatedEvent())
    event.net.network = utils.create_vmware_net(dpg_1_reconfigured)
    return utils.wrap_into_update_set(event=event)


@pytest.mark.skip(reason="Not implement yet")
def test_dpg_reconfiguration(
    topology_with_two_nodes,
    vnc_test_client,
    vmware_controller,
    fabric_vn,
    vm_created_update_1,
    vm_created_update_2,
    dpg_reconfigured_update,
):
    # VM1 created on host esxi-1 with single interface in (dvs-1, dpg-1)
    vmware_controller.handle_update(vm_created_update_1)
    # VM2 created on host esxi-2 with single interface in (dvs-1, dpg-1)
    vmware_controller.handle_update(vm_created_update_2)

    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 2

    created_vmi = vmis["esxi-1_dvs-1_dpg-1"]
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )

    created_vmi = vmis["esxi-2_dvs-1_dpg-1"]
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-2_dvs-1_dpg-1",
        vpg_name="esxi-2_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=5,
    )

    vmware_controller.handle_update(dpg_reconfigured_update)

    vmis = vnc_test_client.read_all_vmis()
    assert len(vmis) == 2

    created_vmi = vmis["esxi-1_dvs-1_dpg-1"]
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-1_dvs-1_dpg-1",
        vpg_name="esxi-1_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=15,
    )

    created_vmi = vmis["esxi-2_dvs-1_dpg-1"]
    utils.verify_vnc_vmi(
        vnc_vmi=created_vmi,
        vmi_name="esxi-2_dvs-1_dpg-1",
        vpg_name="esxi-2_dvs-1",
        vn_name="dvs-1_dpg-1",
        vlan=15,
    )
