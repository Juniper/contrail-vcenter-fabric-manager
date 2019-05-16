from cvfm import models


def test_from_vmware_vm(vmware_vm):
    vmi_models = models.VirtualMachineInterfaceModel.from_vmware_vm(vmware_vm)

    assert vmi_models[0].uuid == models.generate_uuid("esxi-1_dvs-1_dpg-1")
    assert vmi_models[0].host_name == "esxi-1"
    assert vmi_models[0].dpg_model.dvs_name == "dvs-1"
    assert vmi_models[0].dpg_model.name == "dpg-1"
    assert vmi_models[0].dpg_model.uuid == models.generate_uuid(
        "dvportgroup-1"
    )
    assert vmi_models[0].vpg_uuid == models.generate_uuid('esxi-1_dvs-1')


def test_to_vnc_vmi(vmware_dpg, project, fabric_vn):
    dpg_model = models.DistributePortGroupModel.from_vmware_dpg(vmware_dpg)
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
