import mock
import pytest

from cvfm import models, exceptions


def test_generate_uuid():
    key = "dvportgroup-1"

    uuid = models.generate_uuid(key)

    assert uuid == "5a6bd262-1f96-3546-a762-6fa5260e9014"


def test_from_vmware_dpg(vmware_dpg):
    dpg_model = models.DistributePortGroupModel.from_vmware_dpg(vmware_dpg)

    assert dpg_model.name == "dpg-1"
    assert dpg_model.uuid == models.generate_uuid("dvportgroup-1")
    assert dpg_model.vlan_id == 5
    assert dpg_model.dvs_name == "dvs-1"


def test_invalid_vlan_id(vmware_dpg):
    vmware_dpg.config.defaultPortConfig.vlan.vlanId = mock.Mock()

    with pytest.raises(exceptions.DPGCreationException):
        models.DistributePortGroupModel.from_vmware_dpg(vmware_dpg)


def test_to_vnc_vn(project):
    dpg_model = models.DistributePortGroupModel(
        uuid=models.generate_uuid("dvportgroup-1"),
        name="dpg-1",
        dvs_name="dvs-1",
        vlan_id=5,
    )

    vnc_vn = dpg_model.to_vnc_vn(project)

    assert vnc_vn.name == "dvs-1_dpg-1"
    assert vnc_vn.uuid == models.generate_uuid("dvportgroup-1")
    assert vnc_vn.parent_name == project.name
