from cvfm import models


def test_to_vnc_vpg():
    vpg_model = models.VirtualPortGroupModel(
        "vpg_uuid", "host_name", "dvs_name"
    )

    vnc_vpg = vpg_model.to_vnc_vpg()

    assert vnc_vpg.name == "host_name_dvs_name"
    assert vnc_vpg.uuid == "vpg_uuid"


def test_from_vmware_vm(vmware_vm):
    vpg_models = models.VirtualPortGroupModel.from_vmware_vm(vmware_vm)

    assert vpg_models[0].uuid == models.generate_uuid("esxi-1_dvs-1")
    assert vpg_models[0].host_name == "esxi-1"
    assert vpg_models[0].dvs_name == "dvs-1"
