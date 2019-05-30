from cvfm import models

import mock


def test_to_vnc_vpg():
    vpg_model = models.VirtualPortGroupModel(
        "vpg_uuid", "host_name", "dvs_name"
    )
    fabric = mock.Mock()
    fabric.fq_name = ["a", "b"]
    vnc_vpg = vpg_model.to_vnc_vpg(fabric)

    assert vnc_vpg.name == "host_name_dvs_name"
    assert vnc_vpg.uuid == "vpg_uuid"
    assert vnc_vpg.get_id_perms().get_creator() == "vcenter-fabric-manager"
    assert vnc_vpg.get_parent_fq_name() == ["a", "b"]


def test_from_vm_model(vmware_vm):
    vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm)

    vpg_models = models.VirtualPortGroupModel.from_vm_model(vm_model)

    assert vpg_models[0].uuid == models.generate_uuid("esxi-1_dvs-1")
    assert vpg_models[0].host_name == "esxi-1"
    assert vpg_models[0].dvs_name == "dvs-1"
