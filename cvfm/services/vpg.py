import logging

from cvfm import models
from cvfm.services.base import Service

__all__ = ["VirtualPortGroupService"]

logger = logging.getLogger(__name__)


class VirtualPortGroupService(Service):
    def create_vpg_models(self, vm_model):
        return models.VirtualPortGroupModel.from_vm_model(vm_model)

    def create_vpg_in_vnc(self, vpg_model, pi_models):
        if not pi_models:
            return
        vnc_pis = [
            self._vnc_api_client.read_pi(pi_model.uuid)
            for pi_model in pi_models
        ]
        vnc_vpg = self._vnc_api_client.read_vpg(vpg_model.uuid)
        if vnc_vpg is None:
            pi_model = pi_models[0]
            vnc_fabric = self._vnc_api_client.read_fabric(pi_model.fabric_uuid)
            logger.info("Not found VPG in VNC for %s. Creating...", vpg_model)
            vnc_vpg = self._create_vpg(vpg_model, vnc_fabric)

        self.update_pis_for_vpg(vnc_vpg, vnc_pis)

    def _create_vpg(self, vpg_model, vnc_fabric):
        vnc_vpg = vpg_model.to_vnc_vpg(vnc_fabric)
        self._vnc_api_client.create_vpg(vnc_vpg)
        return vnc_vpg

    def read_all_vpgs(self):
        return self._vnc_api_client.read_all_vpgs()

    def delete_vpg(self, vpg_uuid):
        self._vnc_api_client.delete_vpg(vpg_uuid)

    def update_pis_for_vpg(self, existing_vpg, pis):
        previous_pis_uuids = [
            pi_ref["uuid"]
            for pi_ref in existing_vpg.get_physical_interface_refs() or ()
        ]
        pis_to_attach = [pi for pi in pis if pi.uuid not in previous_pis_uuids]

        current_pis_uuids = [pi.uuid for pi in pis]
        pis_to_detach = [
            pi_uuid
            for pi_uuid in previous_pis_uuids
            if pi_uuid not in current_pis_uuids
        ]
        pis_change = len(pis_to_attach) != 0 or len(pis_to_attach) != 0
        if not pis_change:
            return
        logger.info(
            "Updating list of physical interfaces connected to VPG %s",
            existing_vpg.name,
        )
        self._vnc_api_client.attach_pis_to_vpg(existing_vpg, pis_to_attach)
        self._vnc_api_client.detach_pis_from_vpg(existing_vpg, pis_to_detach)
        logger.info(
            "Updated list of physical interfaces connected to VPG %s",
            existing_vpg.name,
        )
