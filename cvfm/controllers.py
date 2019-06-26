import logging
from abc import ABCMeta, abstractmethod

from pyVmomi import vim, vmodl  # pylint: disable=no-name-in-module

from cvfm import exceptions

logger = logging.getLogger(__name__)


class VmwareController(object):
    def __init__(self, synchronizer, update_handler, lock):
        self._synchronizer = synchronizer
        self._update_handler = update_handler
        self._lock = lock

    def sync(self):
        logger.info("Synchronizing Contrail vCenter Fabric Manager...")
        with self._lock:
            try:
                self._synchronizer.sync()
                logger.info("Synchronization completed")
            except Exception:
                logger.exception("Unexpected error during CVFM sync")

    def handle_update(self, update_set):
        with self._lock:
            self._update_handler.handle_update(update_set)


class UpdateHandler(object):
    def __init__(self, handlers):
        self._handlers = handlers

    def handle_update(self, update_set):
        for property_filter_update in update_set.filterSet:
            for object_update in property_filter_update.objectSet:
                for property_change in object_update.changeSet:
                    for handler in self._handlers:
                        handler.handle_change(
                            object_update.obj, property_change
                        )


class AbstractChangeHandler(object):
    __metaclass__ = ABCMeta

    def handle_change(self, obj, property_change):
        name = getattr(property_change, "name", None)
        value = getattr(property_change, "val", None)
        if value:
            if name.startswith(self.PROPERTY_NAME):
                try:
                    self._handle_change(obj, value)
                except Exception:
                    logger.exception(
                        "Unexpected exception during handling %s", value
                    )

    @abstractmethod
    def _handle_change(self, obj, value):
        pass


class AbstractEventHandler(AbstractChangeHandler):
    __metaclass__ = ABCMeta
    PROPERTY_NAME = "latestPage"

    def __init__(self, vm_service, vmi_service, dpg_service, vpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service
        self._vpg_service = vpg_service

    def _handle_change(self, obj, value):
        if isinstance(value, self.EVENTS):
            try:
                logger.debug("Detected event: %s", value)
                self._handle_event(value)
            except Exception:
                logger.exception(
                    "Unexpected exception during handling %s", value
                )
        if isinstance(value, list):
            for change in sorted(value, key=lambda e: e.key):
                self._handle_change(obj, change)

    @abstractmethod
    def _handle_event(self, event):
        pass

    def _delete_vmis(self, vmis_to_delete):
        for vmi_model in vmis_to_delete:
            self._vmi_service.delete_vmi(vmi_model.uuid)

    def _create_vmis(self, vm_model, vmis_to_create):
        vpg_models = self._vpg_service.create_vpg_models(vm_model)
        for vpg_model in vpg_models:
            self._vpg_service.create_vpg_in_vnc(vpg_model)
            self._vpg_service.attach_pis_to_vpg(vpg_model)
        for vmi_model in vmis_to_create:
            self._vmi_service.create_vmi_in_vnc(vmi_model)
            self._vmi_service.attach_vmi_to_vpg(vmi_model)


class VmUpdatedHandler(AbstractEventHandler):
    EVENTS = (
        vim.event.VmCreatedEvent,
        vim.event.VmClonedEvent,
        vim.event.VmRegisteredEvent,
        vim.event.VmDeployedEvent,
    )

    def _handle_event(self, event):
        vm_name = event.vm.name
        logger.info("Detected VM %s creation event", vm_name)
        vmware_vm = event.vm.vm
        vm_model = self._vm_service.create_vm_model(vmware_vm)
        vmi_models = self._vmi_service.create_vmi_models_for_vm(vm_model)
        self._create_vmis(vm_model, vmi_models)


class VmReconfiguredHandler(AbstractEventHandler):
    EVENTS = (vim.event.VmReconfiguredEvent,)

    def _handle_event(self, event):
        vm_name = event.vm.name
        logger.info("Detected VM %s reconfiguration event", vm_name)
        if not self._should_update_vmis(event):
            logger.info("Not detected reconfiguration of network adapters")
            return
        logger.info(
            "Detected reconfiguration of VM: %s network adapter(s)", vm_name
        )
        old_vm_model = self._vm_service.delete_vm_model(vm_name)
        new_vm_model = self._vm_service.create_vm_model(event.vm.vm)
        vmis_to_delete, vmis_to_create = self._vmi_service.find_affected_vmis(
            old_vm_model, new_vm_model
        )
        vmis_to_delete = self._dpg_service.filter_out_non_empty_dpgs(
            vmis_to_delete, event.host.host
        )
        self._create_vmis(new_vm_model, vmis_to_create)
        self._delete_vmis(vmis_to_delete)

    @staticmethod
    def _should_update_vmis(event):
        reconfigured_interfaces = [
            device_spec
            for device_spec in event.configSpec.deviceChange
            if isinstance(
                device_spec.device, vim.vm.device.VirtualEthernetCard
            )
        ]
        return bool(reconfigured_interfaces)


class VmRemovedHandler(AbstractEventHandler):
    EVENTS = (vim.event.VmRemovedEvent,)

    def _handle_event(self, event):
        vm_name = event.vm.name
        logger.info("Detected VM: %s deletion", vm_name)
        vm_model = self._vm_service.delete_vm_model(vm_name)

        affected_vmis = self._vmi_service.create_vmi_models_for_vm(vm_model)
        vmis_to_delete = self._dpg_service.filter_out_non_empty_dpgs(
            affected_vmis, event.host.host
        )
        self._delete_vmis(vmis_to_delete)


class VmMovedHandler(AbstractEventHandler):
    EVENTS = (
        vim.event.VmMigratedEvent,
        vim.event.DrsVmMigratedEvent,
        vim.event.VmRelocatedEvent,
    )

    def _handle_event(self, event):
        vmware_vm = event.vm.vm
        vm_uuid = vmware_vm.config.instanceUuid
        new_host = event.host.host
        source_host = event.sourceHost.host
        logger.info(
            "VMware VM %s was moved from host %s to host: %s",
            vmware_vm.name,
            source_host.name,
            new_host.name,
        )

        old_vm_model = self._vm_service.delete_vm_model(vmware_vm.name)
        new_vm_model = self._vm_service.create_vm_model(vmware_vm)
        vmis_to_delete = set(
            self._vmi_service.create_vmi_models_for_vm(old_vm_model)
        )
        vmis_to_create = set(
            self._vmi_service.create_vmi_models_for_vm(new_vm_model)
        )

        vmis_to_delete = self._dpg_service.filter_out_non_empty_dpgs(
            vmis_to_delete, source_host
        )
        self._create_vmis(new_vm_model, vmis_to_create)
        self._delete_vmis(vmis_to_delete)


class VmRenamedHandler(AbstractEventHandler):
    EVENTS = (vim.event.VmRenamedEvent,)

    def _handle_event(self, event):
        new_name = event.newName
        old_name = event.oldName
        logger.info("Detected VM %s rename to %s", old_name, new_name)
        self._vm_service.rename_vm_model(old_name, new_name)


class DVPortgroupCreatedHandler(AbstractEventHandler):
    EVENTS = (vim.event.DVPortgroupCreatedEvent,)

    def _handle_event(self, event):
        logger.info("Detected DPG %s creation", event.net.name)
        vmware_dpg = event.net.network
        try:
            dpg_model = self._dpg_service.create_dpg_model(vmware_dpg)
            logger.info("DPG Model created: %s", dpg_model)
        except exceptions.DPGCreationException:
            logger.exception(
                "Error while creating a model for DPG: %s", vmware_dpg.name
            )
            return

        self._dpg_service.create_fabric_vn(dpg_model)


class DVPortgroupReconfiguredHandler(AbstractEventHandler):
    EVENTS = (vim.event.DVPortgroupReconfiguredEvent,)

    def _handle_event(self, event):
        vmware_dpg = event.net.network
        logger.info("Detected DPG %s reconfiguration", event.net.name)
        try:
            dpg_model = self._dpg_service.create_dpg_model(vmware_dpg)
        except exceptions.DPGCreationException:
            logger.info(
                "Detected DPG %s reconfiguration to invalid VLAN",
                event.net.name,
            )
            self._reconfigure_to_invalid_vlan(vmware_dpg)
            return

        if not self._dpg_service.exists_vn_for_portgroup(vmware_dpg.key):
            logger.info(
                "Detected DPG %s reconfiguration from invalid to valid VLAN",
                event.net.name,
            )
            self._reconfigure_from_invalid_to_valid_vlan(dpg_model)
            return

        if self._dpg_service.should_update_vlan(dpg_model):
            self._handle_vlan_change(dpg_model)

    def _reconfigure_to_invalid_vlan(self, vmware_dpg):
        if not self._dpg_service.exists_vn_for_portgroup(vmware_dpg.key):
            return
        dpg_name = vmware_dpg.name
        dpg_model = self._dpg_service.delete_dpg_model(dpg_name)
        self._dpg_service.delete_fabric_vn(dpg_model.uuid)

    def _reconfigure_from_invalid_to_valid_vlan(self, dpg_model):
        self._dpg_service.create_fabric_vn(dpg_model)
        for vm_model in self._vm_service.create_vm_models_for_dpg_model(
            dpg_model
        ):
            vmi_models = self._vmi_service.create_vmi_models_for_vm(vm_model)
            self._create_vmis(vm_model, vmi_models)

    def _handle_vlan_change(self, dpg_model):
        self._dpg_service.update_vmis_vlan_in_vnc(dpg_model)
        self._vm_service.update_dpg_in_vm_models(dpg_model)


class DVPortgroupRenamedHandler(AbstractEventHandler):
    EVENTS = (vim.event.DVPortgroupRenamedEvent,)

    def _handle_event(self, event):
        old_name = event.oldName
        new_name = event.newName
        logger.info("Detected DPG %s rename to %s", old_name, new_name)
        self._dpg_service.rename_dpg(old_name, new_name)


class DVPortgroupDestroyedHandler(AbstractEventHandler):
    EVENTS = (vim.event.DVPortgroupDestroyedEvent,)

    def _handle_event(self, event):
        dpg_name = event.net.name
        logger.info("Detected DPG %s deletion", dpg_name)
        dpg_model = self._dpg_service.delete_dpg_model(dpg_name)
        self._dpg_service.delete_fabric_vn(dpg_model.uuid)
