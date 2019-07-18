import pytest

from cvfm import models
from cvfm.exceptions import VNCVMICreationError


def test_from_vm_model(vm_model):
    vmi_models = models.VirtualMachineInterfaceModel.from_vm_model(vm_model)

    assert vmi_models[0].uuid == models.generate_uuid("esxi-1_dvs-1_dpg-1")
    assert vmi_models[0].name == "esxi-1_dvs-1_dpg-1"
    assert vmi_models[0].host_name == "esxi-1"
    assert vmi_models[0].dpg_model.dvs_name == "dvs-1"
    assert vmi_models[0].dpg_model.name == "dpg-1"
    assert vmi_models[0].dpg_model.uuid == models.generate_uuid(
        "dvportgroup-1"
    )
    assert vmi_models[0].vpg_uuid == models.generate_uuid("esxi-1_dvs-1")


def test_to_vnc_vmi(vmware_dpg, project, fabric_vn):
    dpg_model = models.DistributedPortGroupModel.from_vmware_dpg(vmware_dpg)
    vmi_model = models.VirtualMachineInterfaceModel(
        uuid=models.generate_uuid("esxi-1_dvs-1_dpg-1"),
        host_name="esxi-1",
        dpg_model=dpg_model,
    )

    vnc_vmi = vmi_model.to_vnc_vmi(project, fabric_vn)

    assert vnc_vmi.uuid == models.generate_uuid("esxi-1_dvs-1_dpg-1")
    assert vnc_vmi.name == "esxi-1_dvs-1_dpg-1"
    assert vnc_vmi.parent_name == project.name
    assert len(vnc_vmi.virtual_network_refs) == 1
    assert vnc_vmi.virtual_network_refs[0]["uuid"] == dpg_model.uuid
    assert (
        vnc_vmi.virtual_machine_interface_properties.sub_interface_vlan_tag
        == 5
    )
    assert vnc_vmi.get_id_perms().get_creator() == "vcenter-fabric-manager"


def test_no_fabric_vn(vmware_dpg, project):
    dpg_model = models.DistributedPortGroupModel.from_vmware_dpg(vmware_dpg)
    vmi_model = models.VirtualMachineInterfaceModel(
        uuid=models.generate_uuid("esxi-1_dvs-1_dpg-1"),
        host_name="esxi-1",
        dpg_model=dpg_model,
    )

    with pytest.raises(VNCVMICreationError):
        vmi_model.to_vnc_vmi(project, None)


def test_hash(vm_model):
    vmi_1 = models.VirtualMachineInterfaceModel.from_vm_model(vm_model)[0]
    vmi_2 = models.VirtualMachineInterfaceModel.from_vm_model(vm_model)[0]

    assert vmi_1 == vmi_2
    assert len({vmi_1, vmi_2}) == 1
