import pytest

from cvfm import models
from tests.utils import (
    create_vm_created_update,
    verify_vnc_vpg,
    verify_vnc_vmi,
)
from vnc_api.vnc_api import VirtualNetwork

from cvfm.controllers import UpdateHandler, VmUpdatedHandler


@pytest.fixture
def update_handler(dpg_service):
    vm_updated_handler = VmUpdatedHandler(None, None, dpg_service)
    return UpdateHandler([vm_updated_handler])


@pytest.fixture
def fabric_vn(vnc_test_client):
    project = vnc_test_client.vnc_lib.project_read(
        ["default-domain", vnc_test_client.project_name]
    )
    fab_vn = VirtualNetwork(name="dvs-1_dpg-1", parent_obj=project)
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
    return create_vm_created_update(
        vm_name="VM1", vm_host_name="esxi-1", vm_portgroups=portgroups
    )


def test_vm_created(
    minimalistic_topology,
    vnc_test_client,
    vmware_controller,
    vm_created_update,
    fabric_vn,
):
    vmware_controller.handle_update(vm_created_update)

    created_vpg = vnc_test_client.vnc_lib.virtual_port_group_read(
        id=models.key_to_uuid("esxi-1_dvs-1")
    )
    # created_vmi = vnc_test_client.vnc_lib.virtual_machine_interface_read(
    #     id=models.key_to_uuid("esxi-1_dvs-1_dpg-1")
    # )

    assert created_vpg is not None
    verify_vnc_vpg(
        vnc_vpg=created_vpg, vpg_name="esxi-1_dvs-1", pi_names=["xe-0/0/0"]
    )
    # verify_vnc_vpg(
    #     vnc_vpg=created_vpg,
    #     vpg_name="esxi-1_dvs-1",
    #     pi_names=["xe-0/0/0"],
    #     vmi_names=["esxi-1_dvs-1_dpg-1"],
    # )

    # assert created_vmi is not None
    # verify_vnc_vmi(
    #     vnc_vmi=created_vmi,
    #     vmi_name="esxi-1_dvs-1_dpg-1",
    #     vpg_name="esxi-1_dvs-1",
    #     vn_name="dvs-1_dpg-1",
    #     vlan=5,
    # )
