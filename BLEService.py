# Abstract base classes module
from abc import ABC, abstractmethod

# GATT server modules
import GATTServer
import sys

# XBee modules
from digi.xbee.devices import XBeeDevice
from digi.xbee.exception import XBeeException
from digi.xbee.exception import InvalidOperatingModeException
from digi.xbee.exception import InvalidPacketException
from digi.xbee.models.mode import OperatingMode
from digi.xbee.models.options import XBeeLocalInterface
from digi.xbee.models.status import ModemStatus
from digi.xbee.packets.base import UnknownXBeePacket
from digi.xbee.packets.relay import UserDataRelayPacket, UserDataRelayOutputPacket

# ConnectCore BLE modules
from exception import ConnectCoreBLEException
from exception import BluetoothNotSupportedException

# Security modules
from BLE_security_manager import BLESecurityManager

# Standard modules
import traceback
import threading


XBEE_PORT_BAUDRATES = [9600, 115200, 1200, 2400, 4800, 19200, 38400, 57600]
XBEE_PORT = '/dev/ttymxc1'


class BLEService(ABC):
    """
        This class offers several methods that can be used to communicate a ConnectCore 6UL working as a Peripheral
        device with an external Central device via Bluetooth Low Energy.
    """
    __BLE_service_instance = None

    def __init__(self):

        # Various function arrays.
        self._on_connect = []
        self._on_disconnect = []
        self._on_data_received = []

        self.service_active = False

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

            # Check for the native Bluetooth interface.
            if GATTServer.is_bluetooth_available():
                cls.__BLE_service_instance = BLEServiceNative()

            # Check for the XBee Bluetooth interface.
            else:
                for baud_rate in XBEE_PORT_BAUDRATES:
                    try:
                        test_xbee_device = XBeeDevice(XBEE_PORT, baud_rate)
                        test_xbee_device.open()
                        test_xbee_device.enable_bluetooth()
                        test_xbee_device.get_parameter('$S')

                        cls.__BLE_service_instance = BLEServiceXBee(test_xbee_device)
                        break
                    except InvalidOperatingModeException:
                        traceback.print_exc()
                        sys.exit(1)
                    except XBeeException:
                        pass

            # If no available interface is found.
            if cls.__BLE_service_instance is None:
                raise BluetoothNotSupportedException()

        return cls.__BLE_service_instance

    @abstractmethod
    def start_service(self):
        """
        Enables the usage of the BLE services.
        """
        raise NotImplementedError()

    @abstractmethod
    def stop_service(self):
        """
        Disables the usage of the BLE services.
        """
        raise NotImplementedError()

    @abstractmethod
    def send_data(self, data):
        """
        Sends the specified data through the available BLE interface.

        Args:
            data (Bytearray): data to send.
        """
        raise NotImplementedError()

    @abstractmethod
    def _execute_user_data_received_callbacks(self, data):
        """
        Executes all the previously set callbacks with the data received from the available BLE interface.

        Args:
            data (Bytearray): received data.
        """
        raise NotImplementedError()

    def add_data_received_callback(self, callback):
        """
        Adds a new callback function to be called on :meth:`.BLEService._execute_user_data_received_callbacks`.

        Args:
            callback (Function): the new callback function.
        """
        self._on_data_received.append(callback)

    def del_data_received_callback(self, callback):
        """
        Removes one of the callback functions to be called on :meth:`.BLEService._execute_user_data_received_callbacks`.

        Args:
            callback (Function): the callback function to be removed.
        """
        if callback in self._on_data_received:
            self._on_data_received.remove(callback)

    @abstractmethod
    def configure_advertising_name(self, device_name):
        """
        Changes the currently advertised service name.

        Args:
            device_name (String): the new name of the service.
        """
        raise NotImplementedError()

    @abstractmethod
    def is_connected(self):
        """
        Checks if the BLE interface is currently connected to a device.

        Returns:
            Boolean representing the connection status.
        """
        raise NotImplementedError()

    @abstractmethod
    def _execute_user_connection_callbacks(self, status):
        """
        Executes all the previously set callbacks with the status of the connection.

        Args:
            status.
        """
        raise NotImplementedError()

    def add_connect_callback(self, callback):
        """
        Adds a new callback function to be called when connection is established on :meth:`.BLEService._execute_user_connection_callbacks`.

        Args:
            callback (Function): the new callback function.
        """
        self._on_connect.append(callback)

    def del_connect_callback(self, callback):
        """
        Removes one of the callback functions to be called when connection is established on :meth:`.BLEService._execute_user_connection_callbacks`.

        Args:
            callback (Function): the callback function to be removed.
        """
        if callback in self._on_connect:
            self._on_connect.remove(callback)

    def add_disconnect_callback(self, callback):
        """
        Adds a new callback function to be called when connection is lost on :meth:`.BLEService._execute_user_connection_callbacks`.

        Args:
            callback (Function): the new callback function.
        """
        self._on_disconnect.append(callback)

    def del_disconnect_callback(self, callback):
        """
        Removes one of the callback functions to be called when connection is lost on :meth:`.BLEService._execute_user_connection_callbacks`.

        Args:
            callback (Function): the callback function to be removed.
        """
        if callback in self._on_disconnect:
            self._on_disconnect.remove(callback)

    @abstractmethod
    def set_password(self, new_password):
        """
        Sets the new authentication password for the service.

        Args:
            new_password (String): the new authentication password.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_type(self):
        """
        Returns a string that indicates the type of the object in a human-friendly way.

        Returns:
            A string indicating the interface.
        """
        raise NotImplementedError()


class BLEServiceNative(BLEService):
    """
    This class implements the abstract methods of ``BLEService`` by creating a GATT server
    and making use of its services.
    """

    def __init__(self):
        BLEService.__init__(self)

        self._GATT_server = GATTServer.GATTServer()

        # Set callback functions.
        self._GATT_server.add_tx_data_callback(self._execute_user_data_received_callbacks)
        self._GATT_server.add_connection_changed_callback(self._execute_user_connection_callbacks)

        BLESecurityManager.generate_salted_verification_key('1234')

    def start_service(self):
        """
        Override.

        See Also:
            :meth:`.BLEService.start_service`
        """
        self.service_active = True
        self._GATT_server.start()

    def stop_service(self):
        """
        Override.

        See Also:
            :meth:`.BLEService.stop_service`
        """
        self.service_active = False
        self._GATT_server.stop()

    def send_data(self, data):
        """
        Override.

        See Also:
            :meth:`.BLEService.send_data`
        """
        # If the packet is a Bluetooth Unlock API Frame, prepare the SRP response.
        if len(data) > 3 and data[3] == 0xAC:
            packet = UnknownXBeePacket.create_packet(data)
            sent_data = packet.output()

        else:
            packet = UserDataRelayOutputPacket(XBeeLocalInterface.BLUETOOTH, data)
            sent_data = packet.output()

            # Encrypt the data if possible.
            try:
                sent_data = BLESecurityManager.encrypt_data(sent_data)
            except ConnectCoreBLEException:
                raise

        self._GATT_server.send_rx_data(sent_data)

    def _execute_user_data_received_callbacks(self, data):
        """
        Override.

        See Also:
            :meth:`.BLEService._execute_user_data_received_callbacks`
        """
        # If the packet is a Bluetooth Unlock API Frame, process the SRP request.
        if len(data) > 3 and data[3] == 0x2C:
            srp_response = BLESecurityManager.process_srp_request(data)
            self.send_data(srp_response)
            return

        try:
            # Decrypt the data if possible.
            decrypted_data = BLESecurityManager.decrypt_data(data)

            # Ignore if it is an AT Command.
            if len(decrypted_data) > 3 and decrypted_data[3] == 0x08:
                return

            # Create User Data Relay Packet from the raw data received.
            packet = UserDataRelayPacket.create_packet(decrypted_data, OperatingMode.API_MODE)
            payload = packet.data

            for callback in self._on_data_received:
                callback(payload)
        except ConnectCoreBLEException:
            raise
        except InvalidPacketException:
            raise

    def configure_advertising_name(self, device_name):
        """
        Override.

        See Also:
            :meth:`.BLEService.configure_advertising_name`
        """
        self._GATT_server.configure_advertising_name(device_name)

    def is_connected(self):
        """
        Override.

        See Also:
            :meth:`.BLEService.is_connected`
        """
        if self._GATT_server.get_connection_status() == GATTServer.GATTConnectionStatus.CONNECTED:
            return True
        elif self._GATT_server.get_connection_status() == GATTServer.GATTConnectionStatus.DISCONNECTED:
            return False

    def _execute_user_connection_callbacks(self, status):
        """
        Override.

        See Also:
            :meth:`.BLEService._execute_user_connection_callbacks`
        """
        if status == GATTServer.GATTConnectionStatus.CONNECTED:
            for callback in self._on_connect:
                callback()

        elif status == GATTServer.GATTConnectionStatus.DISCONNECTED:
            for callback in self._on_disconnect:
                callback()

    def set_password(self, new_password):
        """
        Override.

        See Also:
            :meth:`.BLEService.set_password`
        """
        BLESecurityManager.generate_salted_verification_key(new_password)

    def get_type(self):
        """
        Override.

        See Also:
            :meth:`.BLEService.get_type`
        """
        return 'Native Interface'


class BLEServiceXBee(BLEService):
    """
        This class implements the abstract methods of ``BLEService`` by establishing connection with an
        XBee device and communicating with its GATT server.
    """

    def __init__(self, open_xbee):
        BLEService.__init__(self)

        self._stop_service_event = threading.Event()

        # Open communication with the XBee device.
        self._xbee = open_xbee

        # Set data received callback.
        self._xbee.add_bluetooth_data_received_callback(self._execute_user_data_received_callbacks)

        # Subscribe to connection event and store connection information.
        self._connected = False
        self._xbee.add_modem_status_received_callback(self._execute_user_connection_callbacks)

    def start_service(self):
        """
        Override.

        See Also:
            :meth:`.BLEService.start_service`
        """
        try:
            self.service_active = True
            self._xbee.enable_bluetooth()

            # Wait for new connections.
            wait_thread = threading.Thread(target=self._stop_service_event.wait)
            wait_thread.start()
        except XBeeException:
            raise

    def stop_service(self):
        """
        Override.

        See Also:
            :meth:`.BLEService.stop_service`
        """
        try:
            self.service_active = False
            self._xbee.disable_bluetooth()

            # Release wait thread.
            self._stop_service_event.set()
        except XBeeException:
            raise

    def send_data(self, data):
        """
        Override.

        See Also:
            :meth:`.BLEService.send_data`
        """
        self._xbee.send_bluetooth_data(data)

    def _execute_user_data_received_callbacks(self, data):
        """
        Override.

        See Also:
            :meth:`.BLEService._execute_user_data_received_callbacks`
        """
        for callback in self._on_data_received:
            callback(data)

    def configure_advertising_name(self, device_name):
        """
        Override.

        See Also:
            :meth:`.BLEService.configure_advertising_name`
        """
        try:
            self._xbee.set_parameter("BI", bytearray(device_name, "utf-8"))
            self._xbee.apply_changes()
        except:
            raise

    def is_connected(self):
        """
        Override.

        See Also:
            :meth:`.BLEService.is_connected`
        """
        return self._connected

    def _execute_user_connection_callbacks(self, status):
        """
        Override.

        See Also:
            :meth:`.BLEService._execute_user_connection_callbacks`
        """
        if status == ModemStatus.BLUETOOTH_CONNECTED:
            self._connected = True
            for callback in self._on_connect:
                callback()
        elif status == ModemStatus.BLUETOOTH_DISCONNECTED:
            self._connected = False
            for callback in self._on_disconnect:
                callback()

    def set_password(self, new_password):
        """
        Override.

        See Also:
            :meth:`.BLEService.set_password`
        """
        self._xbee.update_bluetooth_password(new_password)

    def get_type(self):
        """
        Override.

        See Also:
            :meth:`.BLEService.get_type`
        """
        return 'XBee Interface'
