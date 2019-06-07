import mock
import pytest
import copy

from cvfm import models
from cvfm.services import DistributedPortGroupService


@pytest.fixture
def vcenter_api_client():
    return mock.Mock()


@pytest.fixture
def dpg_service(vcenter_api_client, vnc_api_client, database):
    return DistributedPortGroupService(
        vcenter_api_client, vnc_api_client, database
    )


def test_create_dpg_model(dpg_service, vmware_dpg):
    dpg_model = dpg_service.create_dpg_model(vmware_dpg)

    assert dpg_model.name == "dpg-1"
    assert dpg_model.uuid == "5a6bd262-1f96-3546-a762-6fa5260e9014"
    assert dpg_model.dvs_name == "dvs-1"
    assert dpg_model.vlan_id == 5


def test_create_fabric_vn(dpg_service, vnc_api_client, project):
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
    dpg_name = "dpg-1"
    dvs_name = "dvs-1"

    dpg_service.delete_fabric_vn(dvs_name, dpg_name)

    delete_fq_name = vnc_api_client.delete_vn.call_args[0][0]
    expected_fq_name = project.fq_name + ["dvs-1_dpg-1"]
    assert delete_fq_name == expected_fq_name


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


def test_destroy_dpg_from_vm(dpg_service, database):
    vm_model = mock.Mock()
    vm_model.name = "vm-1"
    database.add_vm_model(vm_model)

    dpg_service.delete_dpg_model("dpg-1")

    assert vm_model.detach_dpg.call_args[0][0] == "dpg-1"
