from cvfm import models


def test_generate_uuid():
    key = "dvportgroup-1"

    uuid = models.generate_uuid(key)

    assert uuid == "5a6bd262-1f96-3546-a762-6fa5260e9014"


def test_get_vn_vnc_name():
    dpg_name = "dpg-name"
    dvs_name = "dvs-name"

    vn_vnc_name = models.DistributedPortGroupModel.get_vnc_name(
        dvs_name, dpg_name
    )

    assert vn_vnc_name == "dvs-name_dpg-name"


def test_from_vmware_dpg(vmware_dpg):
    dpg_model = models.DistributedPortGroupModel.from_vmware_dpg(vmware_dpg)

    assert dpg_model.name == "dpg-1"
    assert dpg_model.key == "dvportgroup-1"
    assert dpg_model.uuid == models.generate_uuid("dvportgroup-1")
    assert dpg_model.vlan_id == 5
    assert dpg_model.dvs_name == "dvs-1"


def test_to_vnc_vn(project):
    dpg_model = models.DistributedPortGroupModel(
        uuid=models.generate_uuid("dvportgroup-1"),
        key="dvportgroup-1",
        name="dpg-1",
        dvs_name="dvs-1",
        vlan_id=5,
    )

    vnc_vn = dpg_model.to_vnc_vn(project)

    assert vnc_vn.name == "dvs-1_dpg-1"
    assert vnc_vn.uuid == models.generate_uuid("dvportgroup-1")
    assert vnc_vn.parent_name == project.name
    assert vnc_vn.get_id_perms().get_creator() == "vcenter-fabric-manager"
