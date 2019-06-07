class Synchronizer(object):
    def __init__(self, vm_synchronizer, dpg_synchronizer, vpg_synchronizer):
        self.vm_synchronizer = vm_synchronizer
        self.dpg_synchronizer = dpg_synchronizer
        self.vpg_synchronizer = vpg_synchronizer

    def sync(self):
        self.vm_synchronizer.sync()
        self.dpg_synchronizer.sync_create()
        self.vpg_synchronizer.sync_create()


class VirtualMachineSynchronizer(object):
    def __init__(self, vm_service):
        self._vm_service = vm_service

    def sync(self):
        self._vm_service.populate_db_with_vms()


class DistributedPortGroupSynchronizer(object):
    def __init__(self, dpg_service):
        self._dpg_service = dpg_service

    def sync_create(self):
        dpgs_in_vcenter = self._dpg_service.get_all_dpg_models()
        fabric_vn_uuids = self._dpg_service.get_all_fabric_vn_uuids()

        vns_to_create = [
            dpg_model
            for dpg_model in dpgs_in_vcenter
            if dpg_model.uuid not in fabric_vn_uuids
        ]

        for dpg_model in vns_to_create:
            self._dpg_service.create_fabric_vn(dpg_model)


class VirtualPortGroupSynchronizer(object):
    def __init__(self, vm_service, vpg_service):
        self._vm_service = vm_service
        self._vpg_service = vpg_service

    def sync_create(self):
        vm_models = self._vm_service.get_all_vm_models()
        vpg_models = []
        for vm_model in vm_models:
            vpg_models.extend(self._vpg_service.create_vpg_models(vm_model))
        for vpg_model in set(vpg_models):
            pis = self._vpg_service.find_pis_for_vpg(vpg_model)
            self._vpg_service.create_vpg_with_pis_in_vnc(vpg_model, pis)
