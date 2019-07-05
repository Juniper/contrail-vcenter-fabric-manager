import mock

from cvfm import models


def test_from_vmware_vm(vmware_vm):
    dpg_models = [mock.Mock()]
    vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm, dpg_models)

    assert vm_model.name == "vm-1"
    assert vm_model.vcenter_uuid == "uuid-1"
    assert vm_model.host_name == "esxi-1"
    assert len(vm_model.dpg_models) == 1
    assert list(vm_model.dpg_models) == dpg_models


def test_detach_dpg(vm_model):
    second_dpg = mock.Mock()
    second_dpg.name = "dpg-2"
    vm_model.dpg_models.add(second_dpg)

    vm_model.detach_dpg("dpg-2")

    assert len(vm_model.dpg_models) == 1
    assert list(vm_model.dpg_models)[0].name == "dpg-1"


def test_has_interface_in_dpg(vm_model):
    dpg_model_1 = models.DistributedPortGroupModel(
        models.generate_uuid("dvportgroup-1"),
        "dvportgroup-1",
        "dpg-1",
        5,
        "dvs-1",
    )
    assert vm_model.has_interface_in_dpg(dpg_model_1)
    dpg_model_2 = models.DistributedPortGroupModel(
        models.generate_uuid("dvportgroup-2"),
        "dvportgroup-2",
        "dpg-2",
        6,
        "dvs-1",
    )
    assert not vm_model.has_interface_in_dpg(dpg_model_2)


def test_attach_dpg(vm_model):
    dpg_model = models.DistributedPortGroupModel(
        models.generate_uuid("dvportgroup-2"),
        "dvportgroup-2",
        "dpg-2",
        6,
        "dvs-1",
    )
    vm_model.attach_dpg(dpg_model)
    assert len(vm_model.dpg_models) == 2
    assert sorted(dpg.name for dpg in vm_model.dpg_models) == [
        "dpg-1",
        "dpg-2",
    ]
