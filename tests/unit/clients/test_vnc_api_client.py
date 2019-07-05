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
def vpg_1():
    vpg = vnc_api.VirtualPortGroup(name="esxi-1_dvs-1")
    vpg.set_uuid(models.generate_uuid(vpg.name))
    vpg.set_id_perms(constants.ID_PERMS)
    return vpg


@pytest.fixture
def vcenter_object():
    obj = mock.Mock(uuid="vcenter-obj-uuid")
    obj.get_id_perms.return_value = constants.ID_PERMS
    return obj


@pytest.fixture
def non_vcenter_object(project):
    obj = mock.Mock(uuid="non-vcenter-obj-uuid")
    obj.get_id_perms.return_value.get_creator.return_value = "other-creator"
    return obj


def test_detach_last_vmi_from_vpg(vnc_api_client, vnc_lib, vmi_1, vpg_1):
    vnc_lib.virtual_machine_interface_read.return_value = vmi_1
    vpg_1.add_virtual_machine_interface(vmi_1)
    vmi_1.virtual_port_group_back_refs = [{"uuid": vpg_1.uuid}]
    vnc_lib.virtual_port_group_read.return_value = vpg_1

    vnc_api_client.detach_vmi_from_vpg(vmi_1.uuid)

    vnc_lib.virtual_port_group_update.assert_called_once_with(vpg_1)
    vnc_lib.virtual_port_group_delete.assert_called_once_with(id=vpg_1.uuid)
    utils.verify_vnc_vpg(vpg_1, vmi_names=[])


def test_detach_not_exist_vmi_from_vpg(vnc_api_client, vnc_lib, vmi_1):
    vnc_lib.virtual_machine_interface_read.return_value = None

    vnc_api_client.detach_vmi_from_vpg(vmi_1.uuid)

    vnc_lib.virtual_port_group_update.assert_not_called()
    vnc_lib.virtual_port_group_delete.assert_not_called()


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


def test_read_all_vmis(
    vnc_api_client, vnc_lib, vcenter_object, non_vcenter_object
):
    vnc_lib.virtual_machine_interfaces_list.return_value = {
        "virtual-machine-interfaces": [
            {"uuid": vcenter_object.uuid},
            {"uuid": non_vcenter_object.uuid},
        ]
    }
    vnc_lib.virtual_machine_interface_read.side_effect = [
        vcenter_object,
        non_vcenter_object,
    ]

    vmis = vnc_api_client.read_all_vmis()

    assert vmis == [vcenter_object]


def test_read_all_vpgs(
    vnc_api_client, vnc_lib, vcenter_object, non_vcenter_object
):
    vnc_lib.virtual_port_groups_list.return_value = {
        "virtual-port-groups": [
            {"uuid": vcenter_object.uuid},
            {"uuid": non_vcenter_object.uuid},
        ]
    }
    vnc_lib.virtual_port_group_read.side_effect = [
        vcenter_object,
        non_vcenter_object,
    ]

    vpgs = vnc_api_client.read_all_vpgs()

    assert vpgs == [vcenter_object]


def test_read_all(vnc_api_client, vnc_lib, vcenter_object, non_vcenter_object):
    vnc_lib.virtual_networks_list.return_value = {
        "virtual-networks": [
            {"uuid": vcenter_object.uuid},
            {"uuid": non_vcenter_object.uuid},
        ]
    }
    vnc_lib.virtual_network_read.side_effect = [
        vcenter_object,
        non_vcenter_object,
    ]

    vns = vnc_api_client.read_all_vns()

    assert vns == [vcenter_object]


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


def test_read_nodes_by_host_names(vnc_api_client):
    node_1 = vnc_api.Node(
        name="node-1", esxi_info=vnc_api.ESXIHostInfo(esxi_name="esxi-1")
    )
    node_2 = vnc_api.Node(name="node-2", esxi_info=vnc_api.ESXIHostInfo())
    node_3 = vnc_api.Node(name="node-3")
    node_4 = vnc_api.Node(
        name="node-4", esxi_info=vnc_api.ESXIHostInfo(esxi_name="esxi-1")
    )
    node_5 = vnc_api.Node(
        name="node-5", esxi_info=vnc_api.ESXIHostInfo(esxi_name="esxi-2")
    )
    nodes = [node_1, node_2, node_3, node_4, node_5]

    with mock.patch(
        "cvfm.clients.VNCAPIClient._read_all_nodes"
    ) as read_all_nodes_mock:
        read_all_nodes_mock.return_value = nodes
        result = vnc_api_client.get_nodes_by_host_names(["esxi-1", "esxi-2"])

    assert len(result) == 3
    assert node_1 in result
    assert node_4 in result
    assert node_5 in result
