from cvfm import models


def test_from_vmware_vm(vmware_vm):
    vm_model = models.VirtualMachineModel.from_vmware_vm(vmware_vm)

    assert vm_model.name == "vm-1"
    assert vm_model.host_name == "esxi-1"
    assert len(vm_model.dpg_models) == 1
    assert list(vm_model.dpg_models)[0].name == "dpg-1"
