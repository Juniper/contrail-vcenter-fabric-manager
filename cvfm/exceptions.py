class DPGCreationException(Exception):
    pass


class VNCVMICreationException(Exception):
    pass


class VNCPortValidationException(Exception):
    pass


class ConnectionLostError(Exception):
    pass


class VNCConnectionLostError(ConnectionLostError):
    pass
