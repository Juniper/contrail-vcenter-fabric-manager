import pytest
import mock

from cvfm import services, models


@pytest.fixture
def vm_service(vcenter_api_client, vnc_api_client, database):
    return services.VirtualMachineService(
        vcenter_api_client, vnc_api_client, database
    )


def test_create_vm_model(vm_service, vmware_vm, database):
    dpg_model = mock.Mock()
    dpg_model.name = "dpg-1"
    database.add_dpg_model(dpg_model)

    vm_model = vm_service.create_vm_model(vmware_vm)

    assert database.get_vm_model("vm-1") == vm_model
    assert vm_model.name == "vm-1"
    assert vm_model.host_name == "esxi-1"
    assert vm_model.property_filter is not None
    assert len(vm_model.dpg_models) == 1
    assert list(vm_model.dpg_models)[0] == dpg_model


def test_create_vm_model_when_dpg_not_exists(vm_service, vmware_vm, database):
    database.clear_database()

    vm_model = vm_service.create_vm_model(vmware_vm)

    assert len(vm_model.dpg_models) == 0


def test_delete_vm_model(vm_service, vm_model, database):
    database.add_vm_model(vm_model)

    result_vm_model = vm_service.delete_vm_model("vm-1")

    assert database.get_vm_model("vm-1") is None
    assert result_vm_model == vm_model
    vm_model.property_filter.DestroyPropertyFilter.assert_called_once()


def test_update_dpg_in_vm_models(vm_service, vm_model, database):
    database.add_vm_model(vm_model)

    assert len(vm_model.dpg_models) == 1
    dpg_model = list(vm_model.dpg_models)[0]
    assert dpg_model.vlan_id == 5

    dpg_model = models.DistributedPortGroupModel(
        models.generate_uuid("dvportgroup-1"),
        "dvportgroup-1",
        "dpg-1",
        6,
        "dvs-1",
    )
    vm_service.update_dpg_in_vm_models(dpg_model)
    dpg_model = list(vm_model.dpg_models)[0]
    assert dpg_model.vlan_id == 6


def test_populate_db(
    vm_service, vmware_vm, dpg_model, database, vcenter_api_client
):
    database.clear_database()
    database.add_dpg_model(dpg_model)
    vcenter_api_client.get_all_vms.return_value = [vmware_vm]

    vm_service.populate_db_with_vms()

    assert len(database.get_all_vm_models()) == 1
    vm_model = database.get_vm_model("vm-1")
    assert vm_model.name == "vm-1"
    assert vm_model.host_name == "esxi-1"
    assert len(vm_model.dpg_models) == 1
    assert list(vm_model.dpg_models)[0].name == "dpg-1"


def test_rename_vm(vm_service, vm_model, database):
    database.add_vm_model(vm_model)
    old_name = vm_model.name
    new_name = "vm-1-renamed"

    vm_service.rename_vm_model(old_name, new_name)

    assert database.get_vm_model("vm-1") is None
    assert database.get_vm_model("vm-1-renamed") is vm_model


def test_rename_non_existent_vm(vm_service, database):
    old_name = "vm-1"
    new_name = "vm-1-renamed"

    vm_service.rename_vm_model(old_name, new_name)

    assert database.get_vm_model("vm-1") is None
    assert database.get_vm_model("vm-1-renamed") is None
