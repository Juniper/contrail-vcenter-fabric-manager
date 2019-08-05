class CVFMError(Exception):
    pass


class DPGCreationError(CVFMError):
    pass


class VNCVMICreationError(CVFMError):
    pass


class VNCPortValidationError(CVFMError):
    pass


class ConnectionLostError(CVFMError):
    pass


class VNCConnectionLostError(ConnectionLostError):
    pass


class VCenterConnectionLostError(ConnectionLostError):
    pass


class VNCAdminProjectNotFound(CVFMError):
    pass
