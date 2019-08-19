from builtins import object
import logging

from cvfm.exceptions import ConnectionLostError

logger = logging.getLogger(__name__)


class CVFMSynchronizer(object):
    def __init__(
        self,
        database,
        vm_synchronizer,
        dpg_synchronizer,
        vpg_synchronizer,
        vmi_synchronizer,
        dvs_synchronizer,
        pi_synchronizer,
    ):
        self.database = database
        self.vm_synchronizer = vm_synchronizer
        self.dpg_synchronizer = dpg_synchronizer
        self.vpg_synchronizer = vpg_synchronizer
        self.vmi_synchronizer = vmi_synchronizer
        self.dvs_synchronizer = dvs_synchronizer
        self.pi_synchronizer = pi_synchronizer

    def sync(self):
        self.database.clear_database()
        self.dvs_synchronizer.sync()
        self.pi_synchronizer.sync()
        self.dpg_synchronizer.sync_create()
        self.vm_synchronizer.sync()
        self.vpg_synchronizer.sync_create()
        self.vmi_synchronizer.sync_create()
        self.vmi_synchronizer.sync_delete()
        self.vpg_synchronizer.sync_delete()
        self.dpg_synchronizer.sync_delete()


class BaseSynchronizer(object):
    def __init__(
        self,
        vm_service=None,
        vmi_service=None,
        dpg_service=None,
        vpg_service=None,
        dvs_service=None,
        pi_service=None,
    ):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service
        self._vpg_service = vpg_service
        self._dvs_service = dvs_service
        self._pi_service = pi_service


class VirtualMachineSynchronizer(BaseSynchronizer):
    def sync(self):
        logger.info("Populating local database with VM models...")
        self._vm_service.populate_db_with_vms()
        logger.info("Populated local database with VM models")


class DistributedPortGroupSynchronizer(BaseSynchronizer):
    def sync_create(self):
        logger.info("Populating local database with DPG models...")
        self._dpg_service.populate_db_with_dpgs()
        logger.info("Populated local database with DPG models")
        dpgs_in_vcenter = self._dpg_service.get_all_dpg_models()
        fabric_vns = self._dpg_service.get_all_fabric_vns()
        fabric_vn_uuids = [vn.uuid for vn in fabric_vns]

        vns_to_create = [
            dpg_model
            for dpg_model in dpgs_in_vcenter
            if dpg_model.uuid not in fabric_vn_uuids
        ]

        if len(vns_to_create) == 0:
            logger.info("Not detected lacking VNs in VNC")
            return

        logger.info("Creating lacking VNs in VNC...")
        for dpg_model in vns_to_create:
            try:
                self._dpg_service.create_fabric_vn(dpg_model)
            except ConnectionLostError:
                raise
            except Exception:
                logger.exception(
                    "Unexpected error during creating VN for %s", dpg_model
                )
        logger.info("Created lacking VNs in VNC")

    def sync_delete(self):
        dpgs_in_vcenter = self._dpg_service.get_all_dpg_models()
        dpgs_in_vcenter_uuids = set(dpg.uuid for dpg in dpgs_in_vcenter)
        fabric_vns = self._dpg_service.get_all_fabric_vns()

        fabric_vns_to_delete = [
            fabric_vn
            for fabric_vn in fabric_vns
            if fabric_vn.uuid not in dpgs_in_vcenter_uuids
        ]

        if len(fabric_vns_to_delete) == 0:
            logger.info("Not detected stale VNs in VNC")
            return

        logger.info("Deleting stale VNs from VNC...")
        for fabric_vn in fabric_vns_to_delete:
            try:
                self._dpg_service.delete_fabric_vn(fabric_vn.uuid)
            except ConnectionLostError:
                raise
            except Exception:
                logger.exception(
                    "Unexpected error during deleting VN with uuid: %s",
                    fabric_vn.uuid,
                )
        logger.info("Deleted stale VNs from VNC...")


class VirtualPortGroupSynchronizer(BaseSynchronizer):
    def sync_create(self):
        logger.info("Creating lacking/Updating VPGs in VNC...")
        vm_models = self._vm_service.get_all_vm_models()
        vpg_models = []
        for vm_model in vm_models:
            vpg_models.extend(self._vpg_service.create_vpg_models(vm_model))
        for vpg_model in set(vpg_models):
            logger.debug("Syncing VPG in VNC for %s", vpg_model)
            try:
                pi_models = self._pi_service.get_pi_models_for_vpg(vpg_model)
                self._vpg_service.create_vpg_in_vnc(vpg_model, pi_models)
            except ConnectionLostError:
                raise
            except Exception:
                logger.exception(
                    "Unexpected error during syncing %s", vpg_model
                )
        logger.info("Created lacking/Updated VPGs in VNC")

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
        if len(vpgs_to_delete) == 0:
            logger.info("Not detected stale VPGs in VNC")
            return
        logger.info("Deleting stale VPGs from VNC...")
        for vpg_uuid in vpgs_to_delete:
            try:
                self._vpg_service.delete_vpg(vpg_uuid)
            except ConnectionLostError:
                raise
            except Exception:
                logger.exception(
                    "Unexpected error during deleting VPG with uuid: %s",
                    vpg_uuid,
                )
        logger.info("Deleted stale VPGs from VNC...")


class VirtualMachineInterfaceSynchronizer(BaseSynchronizer):
    def sync_create(self):
        vm_models = self._vm_service.get_all_vm_models()
        vmi_models = []
        for vm_model in vm_models:
            vmi_models.extend(
                self._vmi_service.create_vmi_models_for_vm(vm_model)
            )
        logger.info("Creating lacking/Updating VMIs in VNC...")
        for vmi_model in set(vmi_models):
            logger.debug("Syncing VMI in VNC for %s", vmi_model)
            try:
                self._vmi_service.create_vmi_in_vnc(vmi_model)
                self._vmi_service.attach_vmi_to_vpg(vmi_model)
            except ConnectionLostError:
                raise
            except Exception:
                logger.exception(
                    "Unexpected error during syncing %s", vmi_model
                )
        logger.info("Created lacking/Updated VMIs in VNC")

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

        if len(vmis_to_delete) == 0:
            logger.info("Not detected stale VMIs in VNC")
            return
        logger.info("Deleting stale VMIs from VNC...")
        for vmi_uuid in vmis_to_delete:
            try:
                self._vmi_service.delete_vmi(vmi_uuid)
            except ConnectionLostError:
                raise
            except Exception:
                logger.exception(
                    "Unexpected error during deleting VMI with uuid %s",
                    vmi_uuid,
                )
        logger.info("Deleted stale VMIs from VNC")


class DistributedVirtualSwitchSynchronizer(BaseSynchronizer):
    def sync(self):
        logger.info("Populating list of supported DVSes...")
        self._dvs_service.populate_db_with_supported_dvses()
        logger.info("List of supported DVSes populated")


class PhysicalInterfaceSynchronizer(BaseSynchronizer):
    def sync(self):
        logger.info("Populating list of Physical Interfaces...")
        self._pi_service.populate_db_with_pi_models()
        logger.info("List of Physical Interfaces populated")
