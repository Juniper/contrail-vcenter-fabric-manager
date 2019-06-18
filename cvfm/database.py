import logging

logger = logging.getLogger(__name__)


class Database(object):
    def __init__(self):
        self._vm_models = {}
        self._dpg_models = {}

    def add_vm_model(self, vm_model):
        self._vm_models[vm_model.name] = vm_model
        logger.debug("Saved %s", vm_model)

    def get_vm_model(self, vm_name):
        return self._vm_models.get(vm_name)

    def update_vm_model(self, vm_model):
        self.add_vm_model(vm_model)

    def remove_vm_model(self, vm_name):
        return self._vm_models.pop(vm_name, None)

    def get_all_vm_models(self):
        return self._vm_models.values()

    def clear_database(self):
        self._vm_models = {}
        self._dpg_models = {}
        logger.info("Cleared local database.")

    def add_dpg_model(self, dpg_model):
        self._dpg_models[dpg_model.name] = dpg_model
        logger.debug("Saved %s", dpg_model)

    def get_dpg_model(self, dpg_name):
        return self._dpg_models.get(dpg_name)

    def remove_dpg_model(self, dpg_name):
        return self._dpg_models.pop(dpg_name, None)

    def get_all_dpg_models(self):
        return self._dpg_models.values()
