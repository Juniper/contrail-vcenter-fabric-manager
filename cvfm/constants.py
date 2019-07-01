from vnc_api.vnc_api import IdPermsType

EVENTS_TO_OBSERVE = [
    "VmCreatedEvent",
    "VmClonedEvent",
    "VmDeployedEvent",
    "VmRenamedEvent",
    "VmReconfiguredEvent",
    "VmMigratedEvent",
    "VmRelocatedEvent",
    "VmRegisteredEvent",
    "VmRemovedEvent",
    "DrsVmMigratedEvent",
    "DVPortgroupCreatedEvent",
    "DVPortgroupReconfiguredEvent",
    "DVPortgroupRenamedEvent",
    "DVPortgroupDestroyedEvent",
]

VM_UPDATE_FILTERS = ["runtime.host"]

WAIT_FOR_UPDATE_TIMEOUT = 20
SUPERVISOR_TIMEOUT = 25

HISTORY_COLLECTOR_PAGE_SIZE = 1000

VNC_PROJECT_NAME = "vCenter"
ID_PERMS = IdPermsType(creator="vcenter-fabric-manager", enable=True)
