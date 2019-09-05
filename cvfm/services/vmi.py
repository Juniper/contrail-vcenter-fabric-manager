import logging

from cvfm import models
from cvfm.exceptions import VNCVMICreationError
from cvfm.services.base import Service

__all__ = ["VirtualMachineInterfaceService"]

logger = logging.getLogger(__name__)


class VirtualMachineInterfaceService(Service):
    def create_vmi_models_for_vm(self, vm_model):
        return models.VirtualMachineInterfaceModel.from_vm_model(vm_model)

    def create_vmi_in_vnc(self, vmi_model):
        vnc_vpg = self._vnc_api_client.read_vpg(vmi_model.vpg_uuid)
        if vnc_vpg is None:
            return
        fabric_vn = self._vnc_api_client.read_vn(vmi_model.dpg_model.uuid)
        project = self._vnc_api_client.get_project()
        try:
            vnc_vmi = vmi_model.to_vnc_vmi(project, fabric_vn)
        except VNCVMICreationError as exc:
            logger.error(
                "Unable to create VMI in VNC for %s. Reason: %s",
                vmi_model,
                exc,
            )
            return
        existing_vmi = self._vnc_api_client.read_vmi(vmi_model.uuid)
        if existing_vmi is None:
            self._vnc_api_client.create_vmi(vnc_vmi)
        else:
            self._update_existing_vmi(vmi_model, existing_vmi, fabric_vn)

    def _update_existing_vmi(self, vmi_model, existing_vmi, fabric_vn):
        old_props = existing_vmi.get_virtual_machine_interface_properties()
        old_vlan = old_props.get_sub_interface_vlan_tag()
        new_vlan = vmi_model.dpg_model.vlan_id
        if old_vlan != new_vlan:
            logger.info(
                "Detected VLAN change for VMI %s from VLAN %s to VLAN %s",
                vmi_model.name,
                old_vlan,
                new_vlan,
            )
            self._vnc_api_client.recreate_vmi_with_new_vlan(
                existing_vmi, fabric_vn, new_vlan
            )

    def attach_vmi_to_vpg(self, vmi_model):
        vnc_vmi = self._vnc_api_client.read_vmi(vmi_model.uuid)
        if vnc_vmi is None:
            return
        vnc_vpg = self._vnc_api_client.read_vpg(vmi_model.vpg_uuid)
        vmi_refs = vnc_vpg.get_virtual_machine_interface_refs() or ()
        vmi_uuids = [vmi_ref["uuid"] for vmi_ref in vmi_refs]
        if vnc_vmi.uuid not in vmi_uuids:
            vnc_vpg.add_virtual_machine_interface(vnc_vmi)
            logger.info(
                "Attached VMI %s to VPG %s", vnc_vmi.name, vnc_vpg.name
            )
            self._vnc_api_client.update_vpg(vnc_vpg)

    def find_affected_vmis(self, old_vm_model, new_vm_model):
        if old_vm_model is None:
            old_vmi_models = set()
        else:
            old_vmi_models = set(self.create_vmi_models_for_vm(old_vm_model))
        new_vmi_models = set(self.create_vmi_models_for_vm(new_vm_model))
        vmis_to_delete = old_vmi_models - new_vmi_models
        vmis_to_create = new_vmi_models - old_vmi_models
        return vmis_to_delete, vmis_to_create

    def delete_vmi(self, vmi_uuid):
        self._vnc_api_client.delete_vmi(vmi_uuid)

    def read_all_vmis(self):
        return self._vnc_api_client.read_all_vmis()
