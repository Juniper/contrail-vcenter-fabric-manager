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


@pytest.mark.parametrize(
    "tested_method_name,vnc_list_method_name,vnc_read_method_name,"
    "vnc_list_name",
    [
        (
            "read_all_vmis",
            "virtual_machine_interfaces_list",
            "virtual_machine_interface_read",
            "virtual-machine-interfaces",
        ),
        (
            "read_all_vpgs",
            "virtual_port_groups_list",
            "virtual_port_group_read",
            "virtual-port-groups",
        ),
    ],
)
def test_read_all(
    vnc_api_client,
    vnc_lib,
    tested_method_name,
    vnc_list_method_name,
    vnc_read_method_name,
    vnc_list_name,
):
    vnc_list_method = getattr(vnc_lib, vnc_list_method_name)
    vnc_read_method = getattr(vnc_lib, vnc_read_method_name)
    tested_method = getattr(vnc_api_client, tested_method_name)
    vcenter_object = mock.Mock(uuid="vcenter-obj-uuid")
    vcenter_object.get_id_perms.return_value = constants.ID_PERMS
    non_vcenter_object = mock.Mock(uuid="non-vcenter-obj-uuid")
    non_vcenter_object.get_id_perms.return_value.get_creator.return_value = (
        "other-creator"
    )

    vnc_list_method.return_value = {
        vnc_list_name: [
            {"uuid": vcenter_object.uuid},
            {"uuid": non_vcenter_object.uuid},
        ]
    }

    vnc_read_method.side_effect = [vcenter_object, non_vcenter_object]

    vmis = tested_method()

    assert vmis == [vcenter_object]
    assert vnc_read_method.call_args_list[0][1]["id"] == vcenter_object.uuid
    assert (
        vnc_read_method.call_args_list[1][1]["id"] == non_vcenter_object.uuid
    )


def test_has_proper_creator():
    proper_creator = mock.Mock()
    proper_creator.get_id_perms.return_value = constants.ID_PERMS
    other_creator = mock.Mock()
    other_creator.get_id_perms.return_value.get_creator.return_value = (
        "other-creator"
    )
    no_creator = mock.Mock()
    no_creator.get_id_perms.return_value = None
    no_id_perms = mock.Mock()
    no_id_perms.get_id_perms.return_value = None

    assert clients.has_proper_creator(proper_creator) is True
    assert clients.has_proper_creator(other_creator) is False
    assert clients.has_proper_creator(no_creator) is False
    assert clients.has_proper_creator(no_id_perms) is False
