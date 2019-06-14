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

    removed = database.remove_vm_model("vm-1")

    assert database.get_vm_model("vm-1") is None
    assert removed == vm_model


def test_get_all_vm_models(database, vm_model):
    database.add_vm_model(vm_model)

    vm_models = database.get_all_vm_models()

    assert list(vm_models) == [vm_model]


def test_add_dpg_model(database, dpg_model):
    database.add_dpg_model(dpg_model)

    assert database.get_dpg_model("dpg-1") == dpg_model
    assert database.get_dpg_model("dpg-2") is None


def test_remove_dpg_model(database, dpg_model):
    database.add_dpg_model(dpg_model)
    assert database.get_dpg_model("dpg-1") == dpg_model

    removed = database.remove_dpg_model("dpg-1")

    assert database.get_dpg_model("dpg-1") is None
    assert removed == dpg_model


def test_get_dpg_model_returns_reference(database, dpg_model, vm_model):
    database.add_dpg_model(dpg_model)
    vm_model.dpg_models = [database.get_dpg_model("dpg-1")]
    assert vm_model.dpg_models[0].dvs_name == "dvs-1"

    dpg = database.get_dpg_model("dpg-1")
    dpg.dvs_name = "changed-value"

    assert vm_model.dpg_models[0].dvs_name == "changed-value"


def test_get_all_dpg_models(database, dpg_model):
    database.add_dpg_model(dpg_model)

    dpg_models = database.get_all_dpg_models()

    assert list(dpg_models) == [dpg_model]


def test_clear_database(database, dpg_model, vm_model):
    database.add_dpg_model(dpg_model)
    database.add_vm_model(vm_model)
    assert len(database.get_all_dpg_models()) == 1
    assert len(database.get_all_vm_models()) == 1

    database.clear_database()

    assert len(database.get_all_dpg_models()) == 0
    assert len(database.get_all_vm_models()) == 0
