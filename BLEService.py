# Abstract base classes module
from abc import ABC, abstractmethod

# GATT server modules
import GATTServer

# XBee modules
from digi.xbee.devices import XBeeDevice
from digi.xbee.exception import XBeeException
from digi.xbee.models.status import ModemStatus

# ConnectCore BLE modules
from BLEInterface import BLEInterface
from exception import ConnectCoreBLEException
from exception import BluetoothNotSupportedException

XBEE_PORT_BAUDRATES = [9600, 115200, 1200, 2400, 4800, 19200, 38400, 57600]


class BLEService(ABC):
    """
        This class offers several methods that can be used to communicate a ConnectCore 6UL working as a Peripheral
        device with an external Central device via Bluetooth Low Energy.
    """
    __BLE_service_instance = None

    def __init__(self, BLE_interface):
        self._BLE_interface = BLE_interface

        self._on_connect = []
        self._on_disconnect = []

    @classmethod
    def get_instance(cls):
        """
        Checks the available Bluetooth interfaces of the device and generates a single instance of the class. If an
        instance does already exist, the method simply returns that instance.

        If Bluetooth is natively supported, the instantiated class is ``BLEServiceNative``.

        If the device does not support Bluetooth, but is connected to an XBee 3 that does support the protocol, the
        instantiated class is ``BLEServiceXBee``.

        Returns:
            BLEService: the single instance generated from the method.

        Raises:
            BluetoothNotSupportedException: if the method does not find any valid Bluetooth interface.
        """
        if cls.__BLE_service_instance is None:

            # Check for the native Bluetooth interface
            if GATTServer.is_bluetooth_available():
                cls.__BLE_service_instance = BLEServiceNative()

            # Check for the XBee Bluetooth interface
            else:
                for baud_rate in XBEE_PORT_BAUDRATES:
                    try:
                        test_xbee_device = XBeeDevice('/dev/ttyXBee', baud_rate)
                        test_xbee_device.open()
                        test_xbee_device.enable_bluetooth()

                        cls.__BLE_service_instance = BLEServiceXBee(baud_rate)
                        break
                    except XBeeException:
                        pass

            # If no available interface is found
            if cls.__BLE_service_instance is None:
                raise BluetoothNotSupportedException()

        return cls.__BLE_service_instance

    @abstractmethod
    def start_service(self):
        raise NotImplementedError()

    @abstractmethod
    def stop_service(self):
        raise NotImplementedError()

    @abstractmethod
    def send_data(self, data):
        raise NotImplementedError()

    @abstractmethod
    def add_data_received_callback(self, callback):
        raise NotImplementedError()

    @abstractmethod
    def del_data_received_callback(self, callback):
        raise NotImplementedError()

    @abstractmethod
    def configure_advertising_name(self, device_name):
        raise NotImplementedError()

    @abstractmethod
    def is_connected(self):
        pass

    @abstractmethod
    def _execute_user_connection_callbacks(self, status):
        raise NotImplementedError()

    def add_connect_callback(self, callback):
        self._on_connect.append(callback)

    def del_connect_callback(self, callback):
        if callback in self._on_connect:
            self._on_connect.remove(callback)

    def add_disconnect_callback(self, callback):
        self._on_disconnect.append(callback)

    def del_disconnect_callback(self, callback):
        if callback in self._on_disconnect:
            self._on_disconnect.remove(callback)

    def get_type(self):
        return self._BLE_interface


class BLEServiceNative(BLEService):
    """
    This class implements the abstract methods of ``BLEService`` by creating a GATT server
    and making use of its services.
    """
    def __init__(self):
        BLEService.__init__(self, BLEInterface.NATIVE_INTERFACE)

        self.GATT_server = GATTServer.GATTServer()
        self.GATT_server.set_connection_changed_callback(self._execute_user_connection_callbacks)

    def start_service(self):
        self.GATT_server.start()

    def stop_service(self):
        self.GATT_server.stop()

    def send_data(self, data):
        pass

    def add_data_received_callback(self, callback):
        pass

    def del_data_received_callback(self, callback):
        pass

    def configure_advertising_name(self, device_name):
        self.GATT_server.configure_advertising_name(device_name)

    def is_connected(self):
        if self.GATT_server.get_connection_status() == GATTServer.GATTConnectionStatus.CONNECTED:
            return True
        elif self.GATT_server.get_connection_status() == GATTServer.GATTConnectionStatus.DISCONNECTED:
            return False

    def _execute_user_connection_callbacks(self, status):
        if status == GATTServer.GATTConnectionStatus.CONNECTED:
            for callback in self._on_connect:
                callback()

        elif status == GATTServer.GATTConnectionStatus.DISCONNECTED:
            for callback in self._on_disconnect:
                callback()


class BLEServiceXBee(BLEService):
    """
        This class implements the abstract methods of ``BLEService`` by establishing connection with an
        XBee device and communicating with its GATT server.
    """
    def __init__(self, baud_rate):
        BLEService.__init__(self, BLEInterface.XBEE_INTERFACE)

        # Open communication with the XBee device
        self.xbee = XBeeDevice('/dev/ttyXBee', baud_rate)
        self.xbee.open()

        # Subscribe to connection event and store connection information
        self._connected = False
        self.xbee.add_modem_status_received_callback(self._execute_user_connection_callbacks)
        self.add_connect_callback(lambda: setattr(self, "_connected", True))
        self.add_disconnect_callback(lambda: setattr(self, "_connected", False))

    def start_service(self):
        try:
            self.xbee.enable_bluetooth()
        except XBeeException:
            raise

    def stop_service(self):
        try:
            self.xbee.disable_bluetooth()
        except XBeeException:
            raise

    def send_data(self, data):
        pass

    def add_data_received_callback(self, callback):
        pass

    def del_data_received_callback(self, callback):
        pass

    def configure_advertising_name(self, device_name):
        self.xbee.set_parameter("BI", bytearray(device_name, "utf-8"))
        self.xbee.apply_changes()

    def is_connected(self):
        print(self._connected)
        return self._connected

    def _execute_user_connection_callbacks(self, status):
        if status == ModemStatus.BLUETOOTH_CONNECTED:
            for callback in self._on_connect:
                callback()
        elif status == ModemStatus.BLUETOOTH_DISCONNECTED:
            for callback in self._on_disconnect:
                callback()


if __name__ == '__main__':
    bleservice = BLEService.get_instance()

    def connect_callback():
        print("Connected")

    def disconnect_callback():
        print("Disconnected")

    bleservice.add_connect_callback(connect_callback)
    bleservice.add_disconnect_callback(disconnect_callback)

    bleservice.start_service()


