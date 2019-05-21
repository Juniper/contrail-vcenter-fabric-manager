import pytest

from cvfm import services


@pytest.fixture
def vm_service(vnc_api_client):
    return services.VirtualMachineService(None, vnc_api_client, None)


def test_create_vm_model(vm_service, vmware_vm):
    vm_model = vm_service.create_vm_model(vmware_vm)

    assert vm_model.name == "vm-1"
    assert vm_model.host_name == "esxi-1"
    assert len(vm_model.dpg_models) == 1
    assert list(vm_model.dpg_models)[0].name == "dpg-1"
