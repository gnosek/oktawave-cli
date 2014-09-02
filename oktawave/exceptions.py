class OktawaveLoginError(RuntimeError):
    pass

class OktawaveOCIClassNotFound(ValueError):
    pass

class OktawaveOVSTierNotFound(ValueError):
    pass

class OktawaveOVSMapError(ValueError):
    pass

class OktawaveOVSUnmapError(ValueError):
    pass

class OktawaveOVSDeleteError(RuntimeError):
    pass

class OktawaveOVSNotFoundError(ValueError):
    pass

class OktawaveOVSMappedError(ValueError):
    pass

class OktawaveOVSUnmappedError(ValueError):
    pass

class OktawaveOVSTooSmallError(ValueError):
    pass

class OktawaveORDBInvalidTemplateError(ValueError):
    pass

class OktawaveContainerNotFoundError(ValueError):
    pass

class OktawaveOCIInContainer(ValueError):
    pass

class OktawaveOCINotInContainer(ValueError):
    pass

class OktawaveOCIInOPN(ValueError):
    pass

class OktawaveOCINotInOPN(ValueError):
    pass

class OktawaveLRTNotAllowed(ValueError):
    pass

class OktawaveAPIError(RuntimeError):

    OCI_PENDING_OPS = 133  # Maszyna wirtualna jest zablokowana przez zlecone zadanie

    ACCESS_DENIED = -403
    GENERIC_FAULT = -999

    def __init__(self, code, error_msg):
        self.code = code
        self.error_msg = error_msg

    def __str__(self):
        return '[{0}] {1}'.format(self.code, self.error_msg)


class OktawaveAccessDenied(OktawaveAPIError):
    def __init__(self, error_msg):
        self.code = self.ACCESS_DENIED
        self.error_msg = error_msg

    def __str__(self):
        return self.error_msg


class OktawaveFault(OktawaveAPIError):
    def __init__(self, error_msg):
        self.code = self.GENERIC_FAULT
        self.error_msg = error_msg

    def __str__(self):
        return self.error_msg
