import logging

from cvfm import constants, models
from cvfm.exceptions import ConnectionLostError
from cvfm.services.base import Service

__all__ = ["VirtualMachineService"]

logger = logging.getLogger(__name__)


class VirtualMachineService(Service):
    def populate_db_with_vms(self):
        vmware_vms = self._vcenter_api_client.get_all_vms()
        for vmware_vm in vmware_vms:
            try:
                self.create_vm_model(vmware_vm)
            except ConnectionLostError:
                raise
            except Exception:
                logger.exception("Unexpected error during VM model creation")

    def create_vm_model(self, vmware_vm):
        dpg_models = set()
        for net in vmware_vm.network:
            dpg_model = self._database.get_dpg_model(net.name)
            if dpg_model:
                dpg_models.add(dpg_model)

        vm_model = models.VirtualMachineModel.from_vmware_vm(
            vmware_vm, dpg_models
        )
        self._database.add_vm_model(vm_model)
        property_filter = self._vcenter_api_client.add_filter(
            vmware_vm, constants.VM_UPDATE_FILTERS
        )
        vm_model.set_property_filter(property_filter)
        return vm_model

    def delete_vm_model(self, vm_name):
        vm_model = self._database.get_vm_model(vm_name)
        self._database.remove_vm_model(vm_name)
        if vm_model is not None:
            vm_model.destroy_property_filter()
        return vm_model

    def update_dpg_in_vm_models(self, dpg_model):
        for vm_model in self._database.get_all_vm_models():
            if vm_model.has_interface_in_dpg(dpg_model):
                vm_model.detach_dpg(dpg_model.name)
                vm_model.attach_dpg(dpg_model)

    def get_all_vm_models(self):
        return self._database.get_all_vm_models()

    def create_vm_models_for_dpg_model(self, dpg_model):
        vm_models = []
        for vmware_vm in self._vcenter_api_client.get_vms_by_portgroup(
            dpg_model.key
        ):
            vm_model = self.create_vm_model(vmware_vm)
            vm_models.append(vm_model)
        return vm_models

    def rename_vm_model(self, old_name, new_name):
        vm_model = self._database.remove_vm_model(old_name)
        if vm_model is None:
            logger.error(
                "VM model %s could not be found in Database", old_name
            )
            return
        vm_model.name = new_name
        self._database.add_vm_model(vm_model)
        logger.info("VM model renamed from %s to %s", old_name, new_name)

    def check_vm_moved(self, vm_name, host):
        vm_model = self._database.get_vm_model(vm_name)
        if vm_model is None:
            return False
        return vm_model.host_name != host.name

    def get_host_from_vm(self, vm_name):
        vm_model = self._database.get_vm_model(vm_name)
        return self._vcenter_api_client.get_host(vm_model.host_name)

    def is_vm_removed_from_vcenter(self, vm_name, host_name):
        vm_model = self._database.get_vm_model(vm_name)
        if vm_model is None:
            return True
        return self._vcenter_api_client.is_vm_removed(
            vm_model.vcenter_uuid, host_name
        )
