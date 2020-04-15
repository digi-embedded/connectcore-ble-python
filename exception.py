class ConnectCoreBLEException(Exception):
    """
    Generic ConnectCore BLE API exception. This class and its subclasses indicate
    conditions that an application might want to catch.

    All functionality of this class is the inherited of `Exception
    <https://docs.python.org/2/library/exceptions.html?highlight=exceptions.exception#exceptions.Exception>`_.
    """
    pass


class BluetoothNotSupportedException(ConnectCoreBLEException):
    """
    This exception will be thrown when Bluetooth is not supported by the device.

    All functionality of this class is the inherited of `Exception
    <https://docs.python.org/2/library/exceptions.html?highlight=exceptions.exception#exceptions.Exception>`_.
    """
    __DEFAULT_MESSAGE = "Bluetooth is not supported by either the ConnectCore or " \
                        "the XBee device."

    def __init__(self, message=__DEFAULT_MESSAGE):
        ConnectCoreBLEException.__init__(self, message)


class NotAuthenticatedException(ConnectCoreBLEException):
    """
    This exception will be thrown when the client attempts communication before a successful authentication process.

    All functionality of this class is the inherited of `Exception
    <https://docs.python.org/2/library/exceptions.html?highlight=exceptions.exception#exceptions.Exception>`_.
    """
    __DEFAULT_MESSAGE = "Data cannot be encrypted. User has not been authenticated"

    def __init__(self, message=__DEFAULT_MESSAGE):
        ConnectCoreBLEException.__init__(self, message)
