import mock
import pytest
from vnc_api import vnc_api

from cvfm import clients, models, constants
from tests import utils


@pytest.fixture
def vnc_lib():
    return mock.Mock()


@pytest.fixture
def vnc_api_client(vnc_lib):
    with mock.patch("cvfm.clients.vnc_api.VncApi") as vnc_lib_mock:
        vnc_lib_mock.return_value = vnc_lib
        return clients.VNCAPIClient(
            {
                "api_server_host": "10.10.10.10",
                "auth_host": "10.10.10.10",
                "project_name": "project",
                "fabric_name": "fabric",
            }
        )


@pytest.fixture
def vmi_1(project):
    vmi = vnc_api.VirtualMachineInterface(
        name="esxi-1_dvs-1_dpg-1", parent_obj=project
    )
    vmi.set_uuid(models.generate_uuid(vmi.name))
    vmi.set_id_perms(constants.ID_PERMS)
    return vmi


@pytest.fixture
def vmi_2(project):
    vmi = vnc_api.VirtualMachineInterface(
        name="esxi-1_dvs-1_dpg-2", parent_obj=project
    )
    vmi.set_uuid(models.generate_uuid(vmi.name))
    vmi.set_id_perms(constants.ID_PERMS)
    return vmi


@pytest.fixture
def vmi_3(project):
    vmi = vnc_api.VirtualMachineInterface(
        name="non-vcenter-vmi", parent_obj=project
    )
    vmi.set_uuid(models.generate_uuid(vmi.name))
    id_perms = vnc_api.IdPermsType(creator="other-creator")
    vmi.set_id_perms(id_perms)
    return vmi


@pytest.fixture
def vpg_1():
    vpg = vnc_api.VirtualPortGroup(name="esxi-1_dvs-1")
    vpg.set_uuid(models.generate_uuid(vpg.name))
    return vpg


def test_detach_last_vmi_from_vpg(vnc_api_client, vnc_lib, vmi_1, vpg_1):
    vnc_lib.virtual_machine_interface_read.return_value = vmi_1
    vpg_1.add_virtual_machine_interface(vmi_1)
    vmi_1.virtual_port_group_back_refs = [{"uuid": vpg_1.uuid}]
    vnc_lib.virtual_port_group_read.return_value = vpg_1

    vnc_api_client.detach_vmi_from_vpg(vmi_1.uuid)

    vnc_lib.virtual_port_group_update.assert_called_once_with(vpg_1)
    vnc_lib.virtual_port_group_delete.assert_called_once_with(id=vpg_1.uuid)
    utils.verify_vnc_vpg(vpg_1, vmi_names=[])


def test_detach_vmi_from_vpg(vnc_api_client, vnc_lib, vmi_1, vmi_2, vpg_1):
    vnc_lib.virtual_machine_interface_read.side_effect = [vmi_1, vmi_2]
    vpg_1.add_virtual_machine_interface(vmi_1)
    vpg_1.add_virtual_machine_interface(vmi_2)
    vmi_1.virtual_port_group_back_refs = [{"uuid": vpg_1.uuid}]
    vmi_2.virtual_port_group_back_refs = [{"uuid": vpg_1.uuid}]
    vnc_lib.virtual_port_group_read.return_value = vpg_1

    vnc_api_client.detach_vmi_from_vpg(vmi_1.uuid)

    vnc_lib.virtual_port_group_update.assert_called_once_with(vpg_1)
    vnc_lib.virtual_port_group_delete.assert_not_called()
    utils.verify_vnc_vpg(vpg_1, vmi_names=["esxi-1_dvs-1_dpg-2"])


def test_read_all_vmis(vnc_api_client, vnc_lib, vmi_1, vmi_3):
    vnc_lib.virtual_machine_interfaces_list.return_value = {
        "virtual-machine-interfaces": [
            {"uuid": vmi_1.uuid},
            {"uuid": vmi_3.uuid},
        ]
    }
    vnc_lib.virtual_machine_interface_read.side_effect = [vmi_1, vmi_3]

    vmis = vnc_api_client.read_all_vmis()

    assert vmis == [vmi_1]
    assert (
        vnc_lib.virtual_machine_interface_read.call_args_list[0][1]["id"]
        == vmi_1.uuid
    )
    assert (
        vnc_lib.virtual_machine_interface_read.call_args_list[1][1]["id"]
        == vmi_3.uuid
    )
