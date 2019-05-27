import logging
from abc import ABCMeta, abstractmethod

from pyVmomi import vim, vmodl  # pylint: disable=no-name-in-module

from cvfm import exceptions

logger = logging.getLogger(__name__)


class VmwareController(object):
    def __init__(
        self, vm_service, vmi_service, dpg_service, update_handler, lock
    ):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service
        self._update_handler = update_handler
        self._lock = lock

    def sync(self):
        logger.info("Synchronizing Contrail vCenter Fabric Manager...")
        with self._lock:
            pass
        logger.info("Synchronization completed")

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

    def _handle_change(self, obj, value):
        if isinstance(value, self.EVENTS):
            try:
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


class VmUpdatedHandler(AbstractEventHandler):
    EVENTS = (
        vim.event.VmCreatedEvent,
        vim.event.VmClonedEvent,
        vim.event.VmRegisteredEvent,
        vim.event.VmDeployedEvent,
        # TODO: figure out what CVFM should do for below events
        vim.event.VmSuspendedEvent,
        vim.event.VmMessageEvent,
        vim.event.VmMacChangedEvent,
        vim.event.VmMacAssignedEvent,
    )

    def __init__(self, vm_service, vmi_service, dpg_service, vpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service
        self._vpg_service = vpg_service

    def _handle_event(self, event):
        logger.info("VmUpdatedHandler: detected event: %s", event)
        vmware_vm = event.vm.vm
        logger.info("VMware VM: %s", vmware_vm)
        vmware_host = event.host.host
        logger.info("VMware Host: %s", vmware_host)
        vm_model = self._vm_service.create_vm_model(vmware_vm)
        vpg_models = self._vpg_service.create_vpg_models(vm_model)
        for vpg_model in vpg_models:
            self._vpg_service.create_vpg_in_vnc(vpg_model)
            self._vpg_service.attach_pis_to_vpg(vpg_model)
        vmi_models = self._vmi_service.create_vmi_models_for_vm(vm_model)
        for vmi_model in vmi_models:
            self._vmi_service.create_vmi_in_vnc(vmi_model)
            self._vmi_service.attach_vmi_to_vpg(vmi_model)


class VmReconfiguredHandler(AbstractEventHandler):
    EVENTS = (vim.event.VmReconfiguredEvent,)

    def __init__(self, vm_service, vmi_service, dpg_service, vpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service
        self._vpg_service = vpg_service

    def _handle_event(self, event):
        logger.info("VmReconfiguredHandler: detected event: %s", event)
        vmware_vm = event.vm.vm
        vm_uuid = vmware_vm.config.instanceUuid
        logger.info("VMware VM: %s with uuid: %s", vmware_vm, vm_uuid)
        for device_spec in event.configSpec.deviceChange:
            device = device_spec.device
            if not isinstance(device, vim.vm.device.VirtualEthernetCard):
                logger.info(
                    "Reconfigured device is not a VirtualEthernetCard. Skipped."
                )
                continue
            operation = device_spec.operation
            logger.info(
                "Reconfigured device: %s with operation: %s", device, operation
            )
            if operation == "add":
                self._handle_add_interface(vm_uuid, device)
            elif operation == "remove":
                self._handle_remove_interface(vm_uuid, device)
            else:
                self._handle_edit_interface(vm_uuid, device)

    def _handle_add_interface(self, vm_uuid, vmware_vmi):
        vmi_model = self._vmi_service.add_vmi(vm_uuid, vmware_vmi)
        self._dpg_service.create_fabric_vmi_for_vm_vmi(vmi_model)

    def _handle_remove_interface(self, vm_uuid, vmware_vmi):
        vmi_model = self._vmi_service.delete_vmi(vm_uuid, vmware_vmi)
        self._dpg_service.delete_fabric_vmi_for_vm_vmi(vmi_model)

    def _handle_edit_interface(self, vm_uuid, vmware_vmi):
        self._handle_remove_interface(vm_uuid, vmware_vmi)
        self._handle_add_interface(vm_uuid, vmware_vmi)


class VmRemovedHandler(AbstractEventHandler):
    EVENTS = (vim.event.VmRemovedEvent,)

    def __init__(self, vm_service, vmi_service, dpg_service, vpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service
        self._vpg_service = vpg_service

    def _handle_event(self, event):
        logger.info("VmRemovedHandler: detected event: %s", event)
        vm_name = event.vm.name
        logger.info("VmRemovedEvent regards VM: %s", vm_name)
        vm_model = self._vm_service.delete_vm_model(vm_name)
        affected_vpgs = []
        for dpg_model in vm_model.dpg_models:
            if not self._dpg_service.is_pg_empty_on_host(
                dpg_model.key, event.host.host
            ):
                continue
            for vmi_model in self._vmi_service.create_vmi_models_for_vm(
                vm_model
            ):
                connected_vpgs = self._vmi_service.find_connected_vpgs(
                    vmi_model.uuid
                )
                affected_vpgs.extend(connected_vpgs)
                self._vmi_service.detach_vmi_from_vpg(vmi_model)
                self._vmi_service.delete_vmi(vmi_model)

        self._vpg_service.prune_empty_vpgs(affected_vpgs)


class VmMigratedHandler(AbstractEventHandler):
    EVENTS = (vim.event.VmMigratedEvent, vim.event.DrsVmMigratedEvent)

    def __init__(self, vm_service, vmi_service, dpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service

    def _handle_event(self, event):
        logger.info("VmMigratedHandler: detected event: %s", event)

        vmware_target_host = event.host.host
        logger.info("VMware target host %s", vmware_target_host)
        target_host_model = self._vm_service.get_host_model(vmware_target_host)

        vmware_source_host = event.sourceHost.host
        logger.info("VMware source host %s", vmware_source_host)
        source_host_model = self._vm_service.get_host_model(vmware_source_host)

        vmware_vm = event.vm.vm
        vm_uuid = vmware_vm.config.instanceUuid
        logger.info("Migrated VMware VM: %s with uuid: %s", vmware_vm, vm_uuid)

        vm_model = self._vm_service.migrate_vm_model(
            vm_uuid, target_host_model
        )
        vmi_models = vm_model.get_all_vmis()
        for vmi_model in vmi_models:
            self._vmi_service.migrate_vmi(
                vmi_model, source_host_model, target_host_model
            )

        for vmi_model in vmi_models:
            self._dpg_service.handle_vm_vmi_migration(
                vmi_model, source_host_model
            )


class VmRenamedHandler(AbstractEventHandler):
    EVENTS = (vim.event.VmRenamedEvent,)

    def __init__(self, vm_service, vmi_service, dpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service

    def _handle_event(self, event):
        logger.info("VmRenamedHandler: detected event: %s", event)
        vmware_vm = event.vm.vm
        vm_uuid = vmware_vm.config.instanceUuid
        new_name = event.newName
        old_name = event.oldName
        logger.info(
            "Renamed VMware VM: %s with uuid: %s from %s to %s",
            vmware_vm,
            vm_uuid,
            old_name,
            new_name,
        )
        self._vm_service.rename_vm_model(vm_uuid, new_name)


class VmPowerStateHandler(AbstractEventHandler):
    EVENTS = (
        vim.event.VmPoweredOnEvent,
        vim.event.VmPoweredOffEvent,
        vim.event.DrsVmPoweredOnEvent,
    )

    def __init__(self, vm_service, vmi_service, dpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service

    def _handle_event(self, event):
        logger.info("VmPowerStateHandler: detected event: %s", event)


class DVPortgroupCreatedHandler(AbstractEventHandler):
    EVENTS = (vim.event.DVPortgroupCreatedEvent,)

    def __init__(self, vm_service, vmi_service, dpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service

    def _handle_event(self, event):
        logger.debug("DVPortgroupCreatedHandler: detected event: %s", event)
        logger.info(
            "DVPortgroupCreatedHandler: detected event: %s", type(event)
        )

        vmware_dpg = event.net.network
        logger.info("VMware DPG: %s with key: %s", vmware_dpg, vmware_dpg.key)

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

    def __init__(self, vm_service, vmi_service, dpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service

    def _handle_event(self, event):
        # TODO: what CVFM should do if dpg VLAN configuration was changed to Private VLAN/Trunk VLAN?
        logger.info(
            "DVPortgroupReconfiguredHandler: detected event: %s", event
        )

        vmware_dpg = event.net.network
        logger.info("VMware DPG: %s with uuid: %s", vmware_dpg, vmware_dpg.key)

        if self._dpg_service.detect_vlan_change(vmware_dpg):
            self._dpg_service.handle_vlan_change(vmware_dpg)


class DVPortgroupRenamedHandler(AbstractEventHandler):
    EVENTS = (vim.event.DVPortgroupRenamedEvent,)

    def __init__(self, vm_service, vmi_service, dpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service

    def _handle_event(self, event):
        logger.info("DVPortgroupRenamedHandler: detected event: %s", event)

        vmware_dpg = event.net.network
        dpg_uuid = vmware_dpg.key
        new_name = vmware_dpg.name
        logger.info(
            "VMware DPG: %s with uuid: %s new_name: %s",
            vmware_dpg,
            dpg_uuid,
            new_name,
        )

        self._dpg_service.rename_dpg(vmware_dpg.key, vmware_dpg.name)


class DVPortgroupDestroyedHandler(AbstractEventHandler):
    EVENTS = (vim.event.DVPortgroupDestroyedEvent,)

    def __init__(self, vm_service, vmi_service, dpg_service):
        self._vm_service = vm_service
        self._vmi_service = vmi_service
        self._dpg_service = dpg_service

    def _handle_event(self, event):
        logger.info("DVPortgroupDestroyedHandler: detected event: %s", event)

        dpg_name = event.net.name
        logger.info("Deleted DPG with name %s", dpg_name)

        dpg_model = self._dpg_service.delete_dpg_model(dpg_name)
        self._dpg_service.delete_fabric_vn(dpg_model)
