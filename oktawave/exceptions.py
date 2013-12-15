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
