import logging

logger = logging.getLogger(__name__)


class Database(object):
    def __init__(self):
        self._vm_models = {}

    def add_vm_model(self, vm_model):
        self._vm_models[vm_model.name] = vm_model

    def get_vm_model(self, vm_name):
        return self._vm_models.get(vm_name)

    def update_vm_model(self, vm_model):
        self.add_vm_model(vm_model)

    def remove_vm_model(self, vm_name):
        self._vm_models.pop(vm_name)

    def clear_database(self):
        pass
