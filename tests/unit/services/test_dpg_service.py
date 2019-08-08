import mock
import pytest

from cvfm import models
from cvfm.exceptions import DPGCreationError
from cvfm.services import DistributedPortGroupService


@pytest.fixture
def vcenter_api_client():
    return mock.Mock()


@pytest.fixture
def dpg_service(vcenter_api_client, vnc_api_client, database):
    return DistributedPortGroupService(
        vcenter_api_client, vnc_api_client, database
    )


@pytest.fixture
def make_vmi():
    def _make_vmi(vmi_uuid, vpg_uuid):
        vmi = mock.Mock(uuid=vmi_uuid)
        vmi.get_virtual_port_group_back_refs.return_value = [
            {"uuid": vpg_uuid}
        ]
        return vmi

    return _make_vmi


def test_create_dpg_model(dpg_service, vmware_dpg, database):
    dpg_model = dpg_service.create_dpg_model(vmware_dpg)

    assert dpg_model.name == "dpg-1"
    assert dpg_model.uuid == "5a6bd262-1f96-3546-a762-6fa5260e9014"
    assert dpg_model.dvs_name == "dvs-1"
    assert dpg_model.vlan_id == 5
    assert database.get_dpg_model("dpg-1") == dpg_model


def test_create_dpg_model_invalid_network(
    dpg_service, vmware_network, database
):
    with pytest.raises(DPGCreationError):
        dpg_model = dpg_service.create_dpg_model(vmware_network)


def test_create_fabric_vn(dpg_service, vnc_api_client, project, database):
    dpg_model = models.DistributedPortGroupModel(
        uuid="5a6bd262-1f96-3546-a762-6fa5260e9014",
        key="dvportgroup-1",
        name="dpg-1",
        vlan_id=None,
        dvs_name="dvs-1",
    )

    dpg_service.create_fabric_vn(dpg_model)

    created_vn = vnc_api_client.create_vn.call_args[0][0]
    assert created_vn.name == "dvs-1_dpg-1"
    assert created_vn.uuid == "5a6bd262-1f96-3546-a762-6fa5260e9014"
    assert created_vn.parent_name == project.name


def test_delete_fabric_vn(dpg_service, vnc_api_client, project):
    dpg_service.delete_fabric_vn("dpg-uuid-1")

    assert vnc_api_client.delete_vn.call_args[0] == ("dpg-uuid-1",)


# Strings are used here as a substitute for vmware_vm fixtures
@pytest.mark.parametrize(
    "pg_vms,host,expected",
    [
        (["vm-1"], mock.Mock(vm=["vm-1"]), False),
        (["vm-1"], mock.Mock(vm=[]), True),
        ([], mock.Mock(vm=["vm-1"]), True),
        ([], mock.Mock(vm=[]), True),
    ],
)
def test_is_pg_empty_on_host(
    vcenter_api_client, dpg_service, pg_vms, host, expected
):
    vcenter_api_client.get_vms_by_portgroup.return_value = pg_vms
    result = dpg_service.is_pg_empty_on_host("dvportgroup-1", host)

    assert result is expected


def test_filter_out_non_empty_dpgs(dpg_service, vcenter_api_client):
    vmi_model_1 = mock.Mock()
    vmi_model_2 = mock.Mock()
    vmi_model_3 = mock.Mock()
    vmware_vm_1 = mock.Mock()
    vmware_vm_2 = mock.Mock()

    host = mock.Mock(vm=[vmware_vm_1, vmware_vm_2])
    vcenter_api_client.get_vms_by_portgroup.side_effect = [
        [vmware_vm_1],
        [vmware_vm_2],
        [],
    ]

    result_vmi_models = dpg_service.filter_out_non_empty_dpgs(
        [vmi_model_1, vmi_model_2, vmi_model_3], host
    )

    assert result_vmi_models == [vmi_model_3]


def test_is_vlan_changed(dpg_service, vnc_api_client):
    dpg_model = models.DistributedPortGroupModel(
        uuid="dpg-uuid",
        key="dvportgroup-1",
        name="dpg-1",
        vlan_id=5,
        dvs_name="dvs-1",
    )

    vnc_api_client.get_vn_vlan.return_value = 15
    assert dpg_service.should_update_vlan(dpg_model)

    vnc_api_client.get_vn_vlan.return_value = 5
    assert not dpg_service.should_update_vlan(dpg_model)

    vnc_api_client.get_vn_vlan.return_value = None
    assert not dpg_service.should_update_vlan(dpg_model)


def test_destroy_dpg_from_vm(dpg_service, database, dpg_model):
    vm_model = mock.Mock()
    vm_model.name = "vm-1"
    database.add_vm_model(vm_model)
    database.add_dpg_model(dpg_model)
    assert database.get_dpg_model("dpg-1") == dpg_model

    deleted = dpg_service.delete_dpg_model("dpg-1")

    assert vm_model.detach_dpg.call_args[0][0] == "dpg-1"
    assert database.get_dpg_model("dpg-1") is None
    assert deleted == dpg_model


def test_populate_db(
    vcenter_api_client, dpg_service, vmware_dpg, vmware_network, database
):
    vcenter_api_client.get_all_portgroups.return_value = [
        vmware_dpg,
        vmware_network,
    ]

    dpg_service.populate_db_with_dpgs()

    assert len(database.get_all_dpg_models()) == 1
    dpg_model = database.get_dpg_model("dpg-1")
    assert dpg_model.name == "dpg-1"
    assert dpg_model.key == "dvportgroup-1"


def test_get_all_dpg_models(dpg_service, dpg_model, database):
    database.add_dpg_model(dpg_model)

    dpg_models = dpg_service.get_all_dpg_models()

    assert list(dpg_models) == [dpg_model]


def test_dpg_rename(dpg_service, dpg_model, database):
    database.add_dpg_model(dpg_model)
    assert database.get_dpg_model("dpg-1") == dpg_model

    dpg_service.rename_dpg("dpg-1", "dpg-new-name")

    assert database.get_dpg_model("dpg-1") is None
    dpg_from_db = database.get_dpg_model("dpg-new-name")
    assert dpg_from_db is dpg_model
    assert dpg_from_db.uuid == dpg_model.uuid
    assert dpg_from_db.name == "dpg-new-name"


@pytest.mark.parametrize("vlan_id", [0, None])
def test_validate_dpg_vlan_id(dpg_service, vmware_dpg, vlan_id):
    vmware_dpg.config.defaultPortConfig.vlan.vlanId = vlan_id

    with pytest.raises(DPGCreationError):
        dpg_service.create_dpg_model(vmware_dpg)


def test_validate_dpg_type(dpg_service, vmware_network):
    with pytest.raises(DPGCreationError):
        dpg_service.create_dpg_model(vmware_network)


def test_validate_dpg_dvs(dpg_service, vmware_dpg):
    vmware_dpg.config.distributedVirtualSwitch.name = "dvs-2"

    with pytest.raises(DPGCreationError):
        dpg_service.create_dpg_model(vmware_dpg)
