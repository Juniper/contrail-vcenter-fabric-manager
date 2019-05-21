from cvfm import models


def test_to_vnc_vpg():
    vpg_model = models.VirtualPortGroupModel(
        "vpg_uuid", "host_name", "dvs_name"
    )

    vnc_vpg = vpg_model.to_vnc_vpg()

    assert vnc_vpg.name == "host_name_dvs_name"
    assert vnc_vpg.uuid == "vpg_uuid"
    assert vnc_vpg.get_id_perms().get_creator() == "vcenter-fabric-manager"


def test_from_vmware_vm(vmware_vm):
    vpg_models = models.VirtualPortGroupModel.from_vmware_vm(vmware_vm)

    assert vpg_models[0].uuid == models.generate_uuid("esxi-1_dvs-1")
    assert vpg_models[0].host_name == "esxi-1"
    assert vpg_models[0].dvs_name == "dvs-1"


def test_from_vm_model(vmware_vm):
    vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm)

    vpg_models = models.VirtualPortGroupModel.from_vm_model(vm_model)

    assert vpg_models[0].uuid == models.generate_uuid("esxi-1_dvs-1")
    assert vpg_models[0].host_name == "esxi-1"
    assert vpg_models[0].dvs_name == "dvs-1"
