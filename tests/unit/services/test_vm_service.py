import pytest

from cvfm import services


@pytest.fixture
def vm_service(vnc_api_client, database):
    return services.VirtualMachineService(None, vnc_api_client, database)


def test_create_vm_model(vm_service, vmware_vm, database):
    vm_model = vm_service.create_vm_model(vmware_vm)

    assert database.get_vm_model("vm-1") == vm_model
    assert vm_model.name == "vm-1"
    assert vm_model.host_name == "esxi-1"
    assert len(vm_model.dpg_models) == 1
    assert list(vm_model.dpg_models)[0].name == "dpg-1"


def test_delete_vm_model(vm_service, vm_model, database):
    database.add_vm_model(vm_model)

    result_vm_model = vm_service.delete_vm_model("vm-1")

    assert database.get_vm_model("vm-1") is None
    assert result_vm_model == vm_model
