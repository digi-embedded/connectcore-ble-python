from enum import Enum, unique
import utils


@unique
class BLEInterface(Enum):
    NATIVE_INTERFACE = (0, "ConnectCore native BLE interface")
    XBEE_INTERFACE = (1, "ConnectCore BLE through XBee interface")
    UNKNOWN = (99, "Unknown")

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
            return BLEInterface.UNKNOWN

    code = property(__get_code)

    description = property(__get_description)


BLEInterface.lookupTable = {x.code: x for x in BLEInterface}
BLEInterface.__doc__ += utils.doc_enum(BLEInterface)