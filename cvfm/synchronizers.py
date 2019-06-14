class Synchronizer(object):
    def __init__(
        self,
        database,
        vm_synchronizer,
        dpg_synchronizer,
        vpg_synchronizer,
        vmi_synchronizer,
    ):
        self.database = database
        self.vm_synchronizer = vm_synchronizer
        self.dpg_synchronizer = dpg_synchronizer
        self.vpg_synchronizer = vpg_synchronizer
        self.vmi_synchronizer = vmi_synchronizer

    def sync(self):
        self.database.clear_database()
        self.dpg_synchronizer.sync_create()
        self.vm_synchronizer.sync()
        self.vpg_synchronizer.sync_create()
        self.vmi_synchronizer.sync_create()
        self.vmi_synchronizer.sync_delete()
        self.vpg_synchronizer.sync_delete()
        self.dpg_synchronizer.sync_delete()


class VirtualMachineSynchronizer(object):
    def __init__(self, vm_service):
        self._vm_service = vm_service

    def sync(self):
        self._vm_service.populate_db_with_vms()


class DistributedPortGroupSynchronizer(object):
    def __init__(self, dpg_service):
        self._dpg_service = dpg_service

    def sync_create(self):
        self._dpg_service.populate_db_with_dpgs()
        dpgs_in_vcenter = self._dpg_service.get_all_dpg_models()
        fabric_vns = self._dpg_service.get_all_fabric_vns()
        fabric_vn_uuids = [vn.uuid for vn in fabric_vns]

        vns_to_create = [
            dpg_model
            for dpg_model in dpgs_in_vcenter
            if dpg_model.uuid not in fabric_vn_uuids
        ]

        for dpg_model in vns_to_create:
            self._dpg_service.create_fabric_vn(dpg_model)

    def sync_delete(self):
        dpgs_in_vcenter = self._dpg_service.get_all_dpg_models()
        dpgs_in_vcenter_uuids = set(dpg.uuid for dpg in dpgs_in_vcenter)
        fabric_vns = self._dpg_service.get_all_fabric_vns()

        fabric_vns_to_delete = [
            fabric_vn
            for fabric_vn in fabric_vns
            if fabric_vn.uuid not in dpgs_in_vcenter_uuids
        ]

        for fabric_vn in fabric_vns_to_delete:
            self._dpg_service.delete_fabric_vn(fabric_vn.uuid)


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
            self._vpg_service.create_vpg_in_vnc(vpg_model)
            self._vpg_service.attach_pis_to_vpg(vpg_model)

    def sync_delete(self):
        vm_models = self._vm_service.get_all_vm_models()
        vpg_models = []
        for vm_model in vm_models:
            vpg_models.extend(self._vpg_service.create_vpg_models(vm_model))
        vpg_uuids = set(vpg_model.uuid for vpg_model in vpg_models)
        vpg_uuids_in_vnc = set(
            vpg.uuid for vpg in self._vpg_service.read_all_vpgs()
        )
        vpgs_to_delete = vpg_uuids_in_vnc - vpg_uuids
        for vpg_uuid in vpgs_to_delete:
            self._vpg_service.delete_vpg(vpg_uuid)


class VirtualMachineInterfaceSynchronizer(object):
    def __init__(self, vm_service, vmi_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service

    def sync_create(self):
        vm_models = self._vm_service.get_all_vm_models()
        vmi_models = []
        for vm_model in vm_models:
            vmi_models.extend(
                self._vmi_service.create_vmi_models_for_vm(vm_model)
            )
        for vmi_model in set(vmi_models):
            self._vmi_service.create_vmi_in_vnc(vmi_model)
            self._vmi_service.attach_vmi_to_vpg(vmi_model)

    def sync_delete(self):
        vm_models = self._vm_service.get_all_vm_models()
        vmi_models = []
        for vm_model in vm_models:
            vmi_models.extend(
                self._vmi_service.create_vmi_models_for_vm(vm_model)
            )
        vmi_uuids = set(vmi_model.uuid for vmi_model in vmi_models)
        vmi_uuids_in_vnc = set(
            vmi.uuid for vmi in self._vmi_service.read_all_vmis()
        )
        vmis_to_delete = vmi_uuids_in_vnc - vmi_uuids
        for vmi_uuid in vmis_to_delete:
            self._vmi_service.delete_vmi(vmi_uuid)
