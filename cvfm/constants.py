from vnc_api.vnc_api import IdPermsType

EVENTS_TO_OBSERVE = [
    "VmCreatedEvent",
    "VmClonedEvent",
    "VmDeployedEvent",
    "VmRenamedEvent",
    "VmReconfiguredEvent",
    "VmRegisteredEvent",
    "VmRemovedEvent",
    "DVPortgroupCreatedEvent",
    "DVPortgroupReconfiguredEvent",
    "DVPortgroupRenamedEvent",
    "DVPortgroupDestroyedEvent",
]

VM_UPDATE_FILTERS = ["runtime.host"]

WAIT_FOR_UPDATE_TIMEOUT = 20
SUPERVISOR_TIMEOUT = 25

WAIT_FOR_VM_RETRY = 10
TEMP_VM_RENAME_PHRASES = ["vmfs", "volumes"]

HISTORY_COLLECTOR_PAGE_SIZE = 1000

VNC_PROJECT_DOMAIN = "default-domain"
VNC_PROJECT_NAME = "admin"
ID_PERMS = IdPermsType(creator="vcenter-fabric-manager", enable=True)
VNC_TOPOLOGY_OBJECTS = [
    "node",
    "port",
    "physical_interface",
    "physical_router",
]
TOPOLOGY_UPDATE_MESSAGE_TIMEOUT = 5
