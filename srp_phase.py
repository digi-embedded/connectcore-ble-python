from enum import Enum, unique
import utils


@unique
class SrpPhase(Enum):
    PHASE_1 = (0x01, "Phase 1: Client presents A value")
    PHASE_2 = (0x02, "Phase 2: Server presents B and salt")
    PHASE_3 = (0x03, "Phase 3: Client presents M1 session key validation value")
    PHASE_4 = (0x04, "Phase 4: Server presents M2 session key validation value and two 12-byte nonces")
    UNKNOWN = (0xFF, "Unknown")

    def __init__(self, code, description):
        self.__code = code
        self.__description = description

    def __get_code(self):
        return self.__code

    def __get_description(self):
        return self.__description

    @classmethod
    def get(cls, code):
        try:
            return cls.lookupTable[code]
        except KeyError:
            return SrpPhase.UNKNOWN

    code = property(__get_code)

    description = property(__get_description)


SrpPhase.lookupTable = {x.code: x for x in SrpPhase}
SrpPhase.__doc__ += utils.doc_enum(SrpPhase)


@unique
class SrpError(Enum):
    B_OFFERING_ERROR = (0x80, "Unable to offer B (cryptographic error with content, usually due to A mod N == 0")
    INCORRECT_LENGTH = (0x81, "Incorrect payload length")
    BAD_PROOF_OF_KEY = (0x82, "Bad proof of key")
    ALLOCATION_ERROR = (0x83, "Resource allocation error")
    WRONG_STEP_ERROR = (0x84, "Request contained a step not in the correct sequence")

    def __init__(self, code, description):
        self.__code = code
        self.__description = description

    def __get_code(self):
        return self.__code

    def __get_description(self):
        return self.__description

    @classmethod
    def get(cls, code):
        try:
            return cls.lookupTable[code]
        except KeyError:
            return None

    code = property(__get_code)

    description = property(__get_description)


SrpError.lookupTable = {x.code: x for x in SrpError}
SrpError.__doc__ += utils.doc_enum(SrpError)
