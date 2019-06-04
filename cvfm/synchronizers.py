class Synchronizer(object):
    def __init__(self, dpg_synchronizer):
        self.dpg_synchronizer = dpg_synchronizer

    def sync(self):
        self.dpg_synchronizer.sync_create()


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
