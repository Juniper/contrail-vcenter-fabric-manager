import mock
import pytest
from vnc_api import vnc_api

from cvfm import clients, models, constants, exceptions
from tests import utils


@pytest.fixture
def vnc_lib():
    return mock.Mock()


@pytest.fixture
def vnc_api_client(vnc_lib):
    with mock.patch("cvfm.clients.vnc.vnc_api.VncApi") as vnc_lib_mock:
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
def fabric():
    fabric = vnc_api.Fabric("fabric-name")
    fabric.set_uuid("fabric-uuid-1")
    return fabric


@pytest.fixture
def vmi_1(project):
    vmi = vnc_api.VirtualMachineInterface(
        name="esxi-1_dvs-1_dpg-1", parent_obj=project
    )
    vmi.set_uuid(models.generate_uuid(vmi.name))
    vmi.set_id_perms(constants.ID_PERMS)
    vmi_properties = vnc_api.VirtualMachineInterfacePropertiesType(
        sub_interface_vlan_tag=5
    )
    vmi.set_virtual_machine_interface_properties(vmi_properties)
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
def vpg_1(fabric):
    vpg = vnc_api.VirtualPortGroup(name="esxi-1_dvs-1", parent_obj=fabric)
    vpg.set_uuid(models.generate_uuid(vpg.name))
    vpg.set_id_perms(constants.ID_PERMS)
    return vpg


@pytest.fixture
def vn(project, vmi_1):
    vn = vnc_api.VirtualNetwork(name="dvs-1_dpg-1", parent_obj=project)
    vn.set_uuid(models.generate_uuid("dvportgroup-1"))
    vn.set_id_perms(constants.ID_PERMS)
    vn.virtual_machine_interface_back_refs = [{"uuid": vmi_1.uuid}]
    return vn


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


def test_read_nodes_by_host_names(vnc_api_client, vnc_lib):
    node_1 = vnc_api.Node(name="esxi-1")
    node_2 = vnc_api.Node(name="esxi-2")
    node_3 = vnc_api.Node(name="esxi-3")
    vnc_lib.nodes_list.return_value = {
        "nodes": [
            {"uuid": "node-1-uuid"},
            {"uuid": "node-2-uuid"},
            {"uuid": "node-3-uuid"},
            {"uuid": "node-4-uuid"},
        ]
    }
    vnc_lib.node_read.side_effect = [
        node_1,
        node_2,
        node_3,
        vnc_api.NoIdError("node-4-uuid"),
    ]

    result = vnc_api_client.get_nodes_by_host_names(["esxi-1", "esxi-2"])

    assert len(result) == 2
    assert node_1 in result
    assert node_2 in result


def test_connection_lost(vnc_api_client, vnc_lib):
    vnc_lib.virtual_networks_list.side_effect = vnc_api.ConnectionError

    with pytest.raises(exceptions.VNCConnectionLostError):
        vnc_api_client.read_all_vns()


def test_create_vn(vnc_api_client, vnc_lib):
    vn = mock.Mock()
    vnc_lib.virtual_network_create.side_effect = [None, vnc_api.RefsExistError]

    vnc_api_client.create_vn(vn)
    vnc_lib.virtual_network_create.assert_called_once_with(vn)

    vnc_api_client.create_vn(vn)
    assert vnc_lib.virtual_network_create.call_count == 2


def test_create_vpg(vnc_api_client, vnc_lib):
    vpg = mock.Mock()
    vnc_lib.virtual_port_group_create.side_effect = [
        None,
        vnc_api.RefsExistError,
    ]

    vnc_api_client.create_vpg(vpg)
    vnc_lib.virtual_port_group_create.assert_called_once_with(vpg)

    vnc_api_client.create_vpg(vpg)
    assert vnc_lib.virtual_port_group_create.call_count == 2


def test_create_vmi(vnc_api_client, vnc_lib):
    vmi = mock.Mock()
    vnc_lib.virtual_machine_interface_create.side_effect = [
        None,
        vnc_api.RefsExistError,
    ]

    vnc_api_client.create_vmi(vmi)
    vnc_lib.virtual_machine_interface_create.assert_called_once_with(vmi)

    vnc_api_client.create_vmi(vmi)
    assert vnc_lib.virtual_machine_interface_create.call_count == 2


def test_delete_vn_no_id(vnc_api_client, vnc_lib, vn, vmi_1):
    vnc_lib.virtual_network_read.return_value = vn
    vnc_lib.virtual_machine_interface_read.return_value = vmi_1
    vnc_lib.virtual_network_delete.side_effect = vnc_api.NoIdError(vn.uuid)

    vnc_api_client.delete_vn(vn.uuid)

    vnc_lib.virtual_network_delete.assert_called_once_with(id=vn.uuid)


def test_delete_vpg_no_id(vnc_api_client, vnc_lib):
    vnc_lib.virtual_port_group_delete.side_effect = vnc_api.NoIdError(
        "vpg-uuid"
    )

    vnc_api_client.delete_vpg("vpg-uuid")

    vnc_lib.virtual_port_group_delete.assert_called_once_with(id="vpg-uuid")


def test_delete_vmi(vnc_api_client, vnc_lib):
    vnc_lib.virtual_machine_interface_delete.side_effect = vnc_api.NoIdError(
        "vmi-uuid"
    )

    with mock.patch.object(vnc_api_client, "detach_vmi_from_vpg"):
        vnc_api_client.delete_vmi("vmi-uuid")

    vnc_lib.virtual_machine_interface_delete.assert_called_once_with(
        id="vmi-uuid"
    )


def test_recreate_vmi(vnc_api_client, vmi_1, vn, vnc_lib, project):
    vpg = mock.Mock()
    vmi_1.virtual_port_group_back_refs = [{"uuid": vpg.uuid}]
    vnc_lib.virtual_port_group_read.return_value = vpg
    vnc_lib.project_read.return_value = project

    vnc_api_client.recreate_vmi_with_new_vlan(vmi_1, vn, 10)

    # detach from vpg
    vpg.del_virtual_machine_interface.assert_called_with(vmi_1)

    # update vpg
    assert vnc_lib.virtual_port_group_update.call_args_list[0] == mock.call(
        vpg
    )

    # delete vmi
    vnc_lib.virtual_machine_interface_delete.assert_called_once_with(
        id=vmi_1.uuid
    )

    # create new vmi
    created_vmi = vnc_lib.virtual_machine_interface_create.call_args[0][0]
    utils.verify_vnc_vmi(created_vmi, vn_name="dvs-1_dpg-1", vlan=10)

    # attach vmi to vpg
    vpg.add_virtual_machine_interface.assert_called_once_with(created_vmi)

    # update vpg
    assert vnc_lib.virtual_port_group_update.call_args_list[1] == mock.call(
        vpg
    )


def test_attach_pis_to_vpg(vnc_api_client, vnc_lib):
    vpg = mock.Mock()
    pi_1 = mock.Mock(fq_name=["1", "2", "3"])
    pi_2 = mock.Mock(fq_name=["4", "5", "6"])
    pis = [pi_1, pi_2]

    vnc_api_client.attach_pis_to_vpg(vpg, pis)

    calls = [mock.call(pi_1), mock.call(pi_2)]
    vpg.add_physical_interface.assert_has_calls(calls)
    assert vpg.add_physical_interface.call_count == 2
    vnc_lib.virtual_port_group_update.assert_called_once_with(vpg)


def test_detach_pis_to_vpg(vnc_api_client, vnc_lib):
    vpg = mock.Mock()
    pi_1 = mock.Mock(fq_name=["1", "2", "3"])
    pi_2 = mock.Mock(fq_name=["4", "5", "6"])
    pi_uuids = ["pi-1-uuid", "pi-2-uuid"]
    vnc_lib.physical_interface_read.side_effect = [pi_1, pi_2]

    vnc_api_client.detach_pis_from_vpg(vpg, pi_uuids)

    calls = [mock.call(pi_1), mock.call(pi_2)]
    vpg.del_physical_interface.assert_has_calls(calls)
    assert vpg.del_physical_interface.call_count == 2
    vnc_lib.virtual_port_group_update.assert_called_once_with(vpg)


def test_get_vn_vlan(vnc_api_client, vnc_lib, vn, vmi_1):
    vnc_lib.virtual_machine_interface_read.return_value = vmi_1

    vlan_id = vnc_api_client.get_vn_vlan(vn)

    assert vlan_id == 5


def test_get_project_no_id(vnc_api_client, vnc_lib):
    vnc_lib.project_read.side_effect = vnc_api.NoIdError("project-uuid")

    with pytest.raises(exceptions.VNCAdminProjectNotFound):
        vnc_api_client.get_project()


def test_update_vpg(vnc_api_client, vnc_lib, vpg_1):
    vnc_lib.virtual_port_group_update.side_effect = vnc_api.NoIdError(
        "vpg-uuid"
    )
    vpg_1 = mock.Mock()

    vnc_api_client.update_vpg(vpg_1)

    vnc_lib.virtual_port_group_update.assert_called_once_with(vpg_1)


def test_read_all_prs(vnc_api_client, vnc_lib):
    pr = mock.Mock()
    pr_refs = {
        "physical-routers": [{"uuid": "pr-1-uuid"}, {"uuid": "pr-2-uuid"}]
    }
    vnc_lib.physical_routers_list.return_value = pr_refs
    vnc_lib.physical_router_read.side_effect = [
        pr,
        vnc_api.NoIdError("pr-2-uuid"),
    ]

    prs = vnc_api_client.read_all_physical_routers()

    assert prs == [pr]


def test_read_pi(vnc_api_client, vnc_lib):
    pi = mock.Mock()
    vnc_lib.physical_interface_read.side_effect = [
        pi,
        vnc_api.NoIdError("pi-uuid"),
    ]

    assert vnc_api_client.read_pi("pi-uuid") == pi
    assert vnc_api_client.read_pi("pi-uuid") is None
