def test_add_vm_model(database, vm_model):
    database.add_vm_model(vm_model)

    assert database.get_vm_model("vm-1") == vm_model
    assert database.get_vm_model("vm-2") is None


def test_update_vm_model(database, vm_model):
    database.add_vm_model(vm_model)
    assert len(database.get_vm_model("vm-1").dpg_models) == 1

    vm_model.dpg_models = set()
    database.update_vm_model(vm_model)

    assert database.get_vm_model("vm-1").dpg_models == set()


def test_remove_vm_model(database, vm_model):
    database.add_vm_model(vm_model)
    assert database.get_vm_model("vm-1") == vm_model

    database.remove_vm_model("vm-1")
    assert database.get_vm_model("vm-1") is None

def test_get_all_vm_models(database, vm_model):
    database.add_vm_model(vm_model)

    vm_models = database.get_all_vm_models()

    assert list(vm_models) == [vm_model]
