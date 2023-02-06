# Copyright 2022, Digi International Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import glob
import logging
import threading

from abc import ABC, abstractmethod
from enum import Enum

from bluezero.adapter import Adapter, AdapterError
from dbus.exceptions import DBusException

from serial.serialutil import SerialException
from serial.tools.list_ports_linux import SysFS
from serial.tools import list_ports

from digi.ccble import utils
from digi.ccble.exceptions import ConnectCoreBLEException, BluetoothNotSupportedException
from digi.ccble.peripheral import ConnectCoreBLEPeripheral
from digi.ccble.security import SRPSecurityManager
from digi.xbee.devices import XBeeDevice
from digi.xbee.exception import InvalidOperatingModeException, InvalidPacketException, XBeeException
from digi.xbee.models.atcomm import ATStringCommand
from digi.xbee.models.hw import HardwareVersion
from digi.xbee.models.mode import OperatingMode
from digi.xbee.models.options import XBeeLocalInterface
from digi.xbee.models.status import ModemStatus, ATCommandStatus
from digi.xbee.packets.aft import ApiFrameType
from digi.xbee.packets.base import UnknownXBeePacket, XBeeAPIPacket
from digi.xbee.packets.common import ATCommPacket, ATCommResponsePacket
from digi.xbee.packets.relay import UserDataRelayPacket, UserDataRelayOutputPacket

# Constants.
_ERROR_BLUETOOTH_NOT_SUPPORTED = "Bluetooth is not supported on this device."
_ERROR_CHANGE_ADVERTISE_NAME = "Failed to change advertise name: %s"
_ERROR_CHANGE_ENCRYPTION_PASSWORD = "Failed to change encryption password: %s"
_ERROR_READ_ADVERTISE_NAME = "Failed to read advertise name: %s"
_ERROR_SEND_DATA = "Failed to send data: %s"
_ERROR_START_BLUETOOTH_SERVICE = "Failed to start Bluetooth service: %s"
_ERROR_STOP_BLUETOOTH_SERVICE = "Failed to stop Bluetooth service: %s"

_WARNING_DATA_DECRYPT = "Could not decrypt received data %s."
_WARNING_DATA_ENCRYPT = "Could not encrypt data to send %s."
_WARNING_INVALID_PACKET_RECEIVED = "Invalid packet received: %s"
_WARNING_SPURIOUS_LOGIN_PACKET_RECEIVED = "Spurious login packet received"

_XBEE_API_FRAME_SRP_LOGIN_REQUEST = 0x2C
_XBEE_API_FRAME_SRP_LOGIN_ANSWER = 0xAC
_XBEE_PORT_PREFIXES = ["ttyXBee", "ttymxc", "ttymca", "ttyUSB"]
_XBEE_PORT_BAUDRATE = 115200


class BLEInterface(Enum):
    """
    Enumeration class listing all the Bluetooth Low Energy interfaces.
    """
    ANY = (0, "Any", "Use first available interface, starting with native adapters")
    ADAPTER = (1, "Bluetooth adapter", "Use native Bluetooth adapter interface")
    XBEE3 = (2, "XBee 3", "Use XBee 3 Bluetooth interface")

    def __init__(self, code, title, description):
        """
        Class constructor. Instantiates a new `BLEInterface` entry with the provided parameters.

        Args:
            code (Integer): BLE interface code.
            title (String): BLE interface title.
            description (String): BLE interface description.
        """
        self.__code = code
        self.__title = title
        self.__description = description

    @property
    def code(self):
        """
        Returns the BLE interface code.

        Returns:
            Integer: BLE interface code.
        """
        return self.__code

    @property
    def title(self):
        """
        Returns the BLE interface title.

        Returns:
            String: BLE interface title.
        """
        return self.__title

    @property
    def description(self):
        """
        Returns the BLE interface description.

        Returns:
            String: BLE interface description.
        """
        return self.__description

    @classmethod
    def get(cls, code):
        """
        Returns the BLE interface corresponding to the given code.

        Args:
            code (Integer): BLE interface code.

        Returns:
            SrpError: BLE interface corresponding to the given code, `None` if not found.
        """
        for ble_interface in cls:
            if code == ble_interface.code:
                return ble_interface
        return None


BLEInterface.__doc__ += utils.doc_enum(BLEInterface)


def get_bluetooth_adapter():
    """
    Returns the first available Bluetooth adapter in the system.

    Returns:
        :class:`.Adapter`: The first :class:`.Adapter` available in the system, `None` if
                           no adapter is found.
    """
    try:
        for bt_adapter in Adapter.available():
            if bt_adapter.powered:
                return bt_adapter
    except (AdapterError, DBusException):
        return None

    return None


def get_xbee_device():
    """
    Returns the first available XBee BTLE capable device in the system.

    Returns:
        :class:`.XBeeDevice`: The first BTLE :class:`.XBeeDevice` available in the system, `None`
                              if no device is found.
    """
    # List serial ports.
    serial_ports = list(list_ports.comports())
    # Add custom ports.
    devices = ['/dev/ttyXBee']
    devices.extend(glob.glob('/dev/ttymca*'))
    devices.extend(glob.glob('/dev/ttymxc*'))
    devices.extend(glob.glob('/dev/ttyLP*'))
    serial_ports.extend(info
                        for info in [SysFS(d) for d in devices]
                        if info.subsystem != "platform")
    # Iterate all ports found.
    for port in serial_ports:
        # Check whether port matches supported prefixes.
        if any(port.name.startswith(prefix) for prefix in _XBEE_PORT_PREFIXES):
            # Try to open the port with default baudrate and forcing settings.
            try:
                xbee_device = XBeeDevice(port.device, _XBEE_PORT_BAUDRATE)
                xbee_device.open(force_settings=True)
            except (InvalidOperatingModeException, XBeeException, SerialException):
                # Continue with next port.
                continue
            try:
                # Try to read Bluetooth setting, if exception is thrown then the device
                # is not BTLE capable.
                xbee_device.get_parameter(ATStringCommand.BT.command)
                # Try to read the SRP salt value, if exception is thrown then the device
                # is not SRP capable.
                xbee_device.get_parameter(ATStringCommand.DOLLAR_S.command)
                # Disable bluetooth to start from a known state.
                xbee_device.disable_bluetooth()
            except XBeeException:
                xbee_device.close()
                # Continue with next port.
                continue
            # The device is valid.
            return xbee_device
    # No devices found.
    return None


class ConnectCoreBLEService(ABC):
    """
    This class offers several methods that can be used to communicate a ConnectCore device
    working as a Peripheral device with an external device via Bluetooth Low Energy.

    The Bluetooth Low Energy communication can be based on native Bluetooth adapters or on the
    XBee 3 Bluetooth Low Energy interface.
    """

    # Variables.
    __BLE_service_instance = None  # Track a unique instance for the service (singleton).
    _log = logging.getLogger(__name__)

    def __init__(self, interface_type):
        """
        Class constructor. Instantiates a new :class:`.ConnectCoreBLEService` object with the given
        parameters.

        Args:
            interface_type (:class:`.BLEInterface`): the BLE interface type to use.
        """
        # Initialize variables.
        self._on_connect = []
        self._on_disconnect = []
        self._on_data_received = []
        self._interface_type = interface_type
        self.service_active = False

    @classmethod
    def get_instance(cls, ble_interface=BLEInterface.ANY):
        """
        Checks the available Bluetooth interfaces of the device and generates a single instance of
        the class depending on the preferred interface. If an instance already exist, the method
        simply returns that instance.

        Depending on the preferred interface, the method returns as follows:
          - If the interface is set to 'ANY' or 'ADAPTER' and Bluetooth is natively supported in
            the system, a :class:`.ConnectCoreBLEServiceNative` object is returned.
          - If the interface is set to 'ANY' and the system does not support native Bluetooth or
            the interface is set to 'XBEE3', the method tries to find a BLE capable XBee 3 device
            connected to the system and returns a :class:`.ConnectCoreBLEServiceXBee` object.

        Args:
            ble_interface (:class:`.BLEInterface`): the BLE interface type to use.

        Returns:
            :class:`.ConnectCoreBLEService`: the single service instance.

        Raises:
            BluetoothNotSupportedException: if the system does not have any valid Bluetooth
                                            interface.
        """
        # Check if an instance of same type already exists.
        if (cls.__BLE_service_instance is not None
                and ((cls.__BLE_service_instance.get_interface_type() == BLEInterface.ADAPTER
                      and ble_interface in (BLEInterface.ANY, BLEInterface.ADAPTER))
                     or (cls.__BLE_service_instance.get_interface_type() == BLEInterface.XBEE3
                         and ble_interface in (BLEInterface.ANY, BLEInterface.XBEE3)))):
            return cls.__BLE_service_instance
        # Initialize variables.
        adapter = None
        cls.__BLE_service_instance = None
        # Check the requested interface type.
        if ble_interface in (BLEInterface.ANY, BLEInterface.ADAPTER):
            # Check for native Bluetooth interface.
            adapter = get_bluetooth_adapter()
        if adapter is not None:
            cls.__BLE_service_instance = ConnectCoreBLEServiceNative(adapter.address)
            cls._log.info("Native Bluetooth interface found: %s", adapter.address)
        elif ble_interface in (BLEInterface.ANY, BLEInterface.XBEE3):
            # Check for XBee Bluetooth interface.
            xbee_device = get_xbee_device()
            if xbee_device is not None:
                cls.__BLE_service_instance = BLEServiceXBee(xbee_device)
                cls._log.info("XBee Bluetooth interface found: %s", xbee_device.get_64bit_addr())
        # If no available interface is found raise exception.
        if cls.__BLE_service_instance is None:
            cls._log.error(_ERROR_BLUETOOTH_NOT_SUPPORTED)
            raise BluetoothNotSupportedException()
        return cls.__BLE_service_instance

    def is_running(self):
        """
        Returns whether the service is running or not.

        Returns:
            Boolean: `True` if service is running, `False` otherwise.
        """
        return self.service_active

    def get_interface_type(self):
        """
        Returns the interface type.

        Returns:
            :class:`.BLEInterface`: The interface type.
        """
        return self._interface_type

    def add_data_received_callback(self, callback):
        """
        Adds a new callback to the list of callbacks that will be notified when data is received
        from the connected device.

        Args:
            callback (Function): the new callback function.
        """
        self._on_data_received.append(callback)

    def remove_data_received_callback(self, callback):
        """
        Removes the given callback from the `data_received` callbacks list.

        Args:
            callback (Function): the callback function to be removed.
        """
        if callback in self._on_data_received:
            self._on_data_received.remove(callback)

    def add_connect_callback(self, callback):
        """
        Adds a new callback to the list of callbacks that will be notified when a device connects.

        Args:
            callback (Function): the new callback function.
        """
        self._on_connect.append(callback)

    def remove_connect_callback(self, callback):
        """
        Removes the given callback from the list of `connect` callbacks.

        Args:
            callback (Function): the callback function to be removed.
        """
        if callback in self._on_connect:
            self._on_connect.remove(callback)

    def add_disconnect_callback(self, callback):
        """
        Adds a new callback to the list of callbacks that will be notified when a device
        disconnects.

        Args:
            callback (Function): the new callback function.
        """
        self._on_disconnect.append(callback)

    def remove_disconnect_callback(self, callback):
        """
        Removes the given callback from the list of `disconnect` callbacks.

        Args:
            callback (Function): the callback function to be removed.
        """
        if callback in self._on_disconnect:
            self._on_disconnect.remove(callback)

    @abstractmethod
    def start(self):
        """
        Starts the BLE service.

        Raises:
            ConnectCoreBLEException: if an error occurs while starting the service.
        """
        raise NotImplementedError()

    @abstractmethod
    def stop(self):
        """
        Stops the BLE service.

        Raises:
            ConnectCoreBLEException: if an error occurs while stopping the service.
        """
        raise NotImplementedError()

    @abstractmethod
    def send_data(self, data):
        """
        Sends the given data to the connected device through the available BLE interface.

        Args:
            data (Bytearray): data to send.

        Raises:
            ConnectCoreBLEException: if an error occurs while sending the data.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_advertising_name(self):
        """
        Changes the currently advertised service name.

        Returns:
            String: the current advertising name.

        Raises:
            ConnectCoreBLEException: if an error occurs while reading the advertising name.
        """
        raise NotImplementedError()

    @abstractmethod
    def set_advertising_name(self, device_name):
        """
        Changes the currently advertised service name.

        Args:
            device_name (String): the new name of the service.

        Raises:
            ConnectCoreBLEException: if an error occurs while changing the advertising name.
        """
        raise NotImplementedError()

    @abstractmethod
    def is_device_connected(self):
        """
        Checks whether there is any device connected to the BLE interface or not.

        Returns:
            Boolean: `True` if there is any device connected, `False` otherwise.
        """
        raise NotImplementedError()

    @abstractmethod
    def set_password(self, new_password):
        """
        Sets the new authentication password for the service.

        Args:
            new_password (String): the new authentication password.

        Raises:
            ConnectCoreBLEException: if an error occurs while setting the new password.
        """
        raise NotImplementedError()


class ConnectCoreBLEServiceNative(ConnectCoreBLEService):
    """
    This class represents a native `ConnectCoreBLEService` by creating a local GATT server with an
    UART peripheral exposing read and write interfaces.

    The service uses SRP authentication protocol to encrypt and decrypt data with a default
    password of '1234'.
    """

    # Constants.
    _DEFAULT_AUTHENTICATION_KEY = "1234"
    _DEFAULT_FIRMWARE_VERSION = [0, 0, 0x10, 0x0D]

    def __init__(self, adapter_address):
        """
        Class constructor. Instantiates a new :class:`.ConnectCoreBLEServiceNative` object with the
        given parameters.

        Args:
            adapter_address (String): the address of the native Bluetooth adapter to use.
        """
        ConnectCoreBLEService.__init__(self, BLEInterface.ADAPTER)

        # Instantiate peripheral.
        self._peripheral = ConnectCoreBLEPeripheral(adapter_address)
        # Set callback functions.
        self._peripheral.add_data_received_callback(self._data_received)
        self._peripheral.add_connection_changed_callback(self._connection_changed)
        self._security_manager = SRPSecurityManager()
        # Initialize SRP authentication.
        self._security_manager.generate_salted_verification_key(self._DEFAULT_AUTHENTICATION_KEY)

    def start(self):
        """
        Override.

        See Also:
            :meth:`.ConnectCoreBLEService.start`
        """
        # Sanity checks.
        if self.service_active:
            return

        try:
            self.service_active = True
            self._peripheral.start()
        except Exception as exc:
            self.service_active = False
            self._log.error(_ERROR_START_BLUETOOTH_SERVICE, str(exc))
            raise ConnectCoreBLEException(_ERROR_START_BLUETOOTH_SERVICE % str(exc)) from exc

    def stop(self):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.stop`
        """
        # Sanity checks.
        if not self.service_active:
            return

        self._peripheral.stop()
        self.service_active = False

    def send_data(self, data):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.send_data`
        """
        # Initialize variables.
        encrypt = True
        # If the packet is a Bluetooth Unlock API Frame answer, prepare the SRP response.
        # This packet must not be encrypt as it is part of the SRP handshake.
        if len(data) > 3 and data[3] == _XBEE_API_FRAME_SRP_LOGIN_ANSWER:
            packet = UnknownXBeePacket.create_packet(data)
            data_to_send = packet.output()
            encrypt = False
        elif len(data) > 3 and data[3] == ApiFrameType.AT_COMMAND_RESPONSE.code:
            # If the packet is an AT Command Answer, just send the given data.
            data_to_send = data
        else:
            # For any other data, build an XBee User Relay Output frame.
            packet = UserDataRelayOutputPacket(XBeeLocalInterface.BLUETOOTH, data)
            data_to_send = packet.output()
        # Encrypt the data if required.
        if encrypt:
            try:
                data_to_send = self._security_manager.encrypt_data(data_to_send)
            except ConnectCoreBLEException as exc:
                self._log.warning(_WARNING_DATA_ENCRYPT, str(exc))
                return
        # Try to send the data.
        try:
            self._peripheral.send_rx_data(data_to_send)
        except DBusException as exc:
            self._log.error(_ERROR_SEND_DATA, str(exc))
            raise ConnectCoreBLEException(_ERROR_SEND_DATA % str(exc)) from exc

    def get_advertising_name(self):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.get_advertising_name`
        """
        return self._peripheral.get_advertising_name()

    def set_advertising_name(self, device_name):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.set_advertising_name`
        """
        try:
            self._peripheral.configure_advertising_name(device_name)
        except Exception as exc:
            self._log.error(_ERROR_CHANGE_ADVERTISE_NAME, str(exc))
            raise ConnectCoreBLEException(_ERROR_CHANGE_ADVERTISE_NAME % str(exc)) from exc

    def is_device_connected(self):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.is_device_connected`
        """
        return self._peripheral.is_device_connected()

    def set_password(self, new_password):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.set_password`
        """
        try:
            self._security_manager.generate_salted_verification_key(new_password)
        except ValueError as exc:
            self._log.error(_ERROR_CHANGE_ENCRYPTION_PASSWORD, str(exc))
            raise ConnectCoreBLEException(_ERROR_CHANGE_ENCRYPTION_PASSWORD % str(exc)) from exc

    def _data_received(self, data):
        """
        Callback function to be notified when new data is received from the device connected
        to the peripheral.

        Args:
            data (Bytearray): the data received from the device connected to the peripheral.
        """
        # If the packet is a Bluetooth Unlock API Frame, process the SRP request and return.
        # This process is executed before SRP encryption is set, so do not decode data here and
        # execute only if user is not authenticated yet.
        if (len(data) > 3 and data[3] == _XBEE_API_FRAME_SRP_LOGIN_REQUEST):
            try:
                XBeeAPIPacket._check_api_packet(data)
                self._security_manager.deauthenticate()
                srp_response = self._security_manager.process_srp_request(data)
                self.send_data(srp_response)
                return
            except InvalidPacketException:
                self._log.warning(_WARNING_SPURIOUS_LOGIN_PACKET_RECEIVED)
        # Decrypt the data if possible.
        try:
            decrypted_data = self._security_manager.decrypt_data(data)
        except ConnectCoreBLEException as exc:
            self._log.warning(_WARNING_DATA_DECRYPT, str(exc))
            return
        # Check if it is an AT Command request to obtain device information.
        if len(decrypted_data) > 3 and decrypted_data[3] == ApiFrameType.AT_COMMAND.code:
            # Get the AT Command request answer.
            answer_packet = self._process_at_command_request(decrypted_data)
            # If the answer is valid, send it to the device, otherwise the given packet was invalid.
            if answer_packet is not None:
                self.send_data(answer_packet.output())
            return
        # Check if it is a User Data Relay Request frame.
        if (len(decrypted_data) > 3
                and decrypted_data[3] == ApiFrameType.USER_DATA_RELAY_REQUEST.code):
            # Try to create an XBee user data relay frame with the given data.
            try:
                packet = UserDataRelayPacket.create_packet(decrypted_data, OperatingMode.API_MODE)
                # Notify subscribed service callbacks about new data received.
                for callback in self._on_data_received:
                    callback(packet.data)
            except InvalidPacketException as exc:
                self._log.warning(_WARNING_INVALID_PACKET_RECEIVED, str(exc))
                return

    def _connection_changed(self, status):
        """
        Callback function to be notified when a connectivity change occurs in the BLE peripheral.

        Args:
            status (Boolean): `True` if any device connects, `False` if any device disconnects.
        """
        # Notify corresponding registered service callbacks.
        if status:
            for callback in self._on_connect:
                callback()
        else:
            for callback in self._on_disconnect:
                callback()

    def _process_at_command_request(self, data):
        """
        Processes the given data as an AT Command Request and returns the requested device
        information in an AT Command Response packet.

        Args:
            data (Bytearray): Data to process.

        Returns:
            :class:`.ATCommResponsePacket`: the AT Command Response packet, `None` if the
                                            given data is invalid.
        """
        # Initialize variables.
        payload = bytearray()
        # Try to create an XBee user data relay frame with the given data.
        try:
            packet = ATCommPacket.create_packet(data, OperatingMode.API_MODE)
            if packet.command == ATStringCommand.SH.command:
                # Use 0x0000 plus the first 2 bytes of the adapter address.
                payload = bytearray.fromhex("0000".join(
                    self._peripheral.dongle.address.split(":")[0:2]))
            elif packet.command == ATStringCommand.SL.command:
                # Use last 4 bytes of the adapter address.
                payload = bytearray.fromhex("".join(
                    self._peripheral.dongle.address.split(":")[2:]))
            elif packet.command == ATStringCommand.NI.command:
                # Use advertising name as device identifier.
                payload = bytearray(self._peripheral.local_name.encode(encoding="utf-8"))
            elif packet.command == ATStringCommand.HV.command:
                # Report ourselves as an XBee 3 SMT
                payload = bytearray([HardwareVersion.XBEE3_SMT.code, 0])
            elif packet.command == ATStringCommand.VR.command:
                payload = bytearray(self._DEFAULT_FIRMWARE_VERSION)
            elif packet.command == ATStringCommand.MY.command:
                # Use the coordinator address '0000'
                payload = bytearray([0, 0])
            # If the payload is filled then the command was valid.
            if len(payload) > 0:
                response_status = ATCommandStatus.OK
            else:
                response_status = ATCommandStatus.INVALID_COMMAND
            # Build and return the response packet.
            return ATCommResponsePacket(packet.frame_id,
                                        packet.command,
                                        response_status=response_status,
                                        comm_value=payload,
                                        op_mode=OperatingMode.API_MODE)
        except InvalidPacketException as exc:
            self._log.warning(_WARNING_INVALID_PACKET_RECEIVED, str(exc))
            return None


class BLEServiceXBee(ConnectCoreBLEService):
    """
    This class implements the abstract methods of `ConnectCoreBLEService` by establishing
    connection with an XBee device and communicating with its GATT server.

    The service uses SRP authentication protocol to encrypt and decrypt data managed by the XBee
    device.
    """

    def __init__(self, open_xbee):
        ConnectCoreBLEService.__init__(self, BLEInterface.XBEE3)

        # Initialize variables.
        self._stop_service_event = threading.Event()
        self._xbee = open_xbee
        self._connected = False
        # Subscribe callbacks callback.
        self._xbee.add_bluetooth_data_received_callback(self._data_received)
        self._xbee.add_modem_status_received_callback(self._modem_status_changed)

    def start(self):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.start`
        """
        # Sanity checks.
        if self.service_active:
            return

        try:
            # Enable bluetooth service in the XBee device.
            self._xbee.enable_bluetooth()
        except XBeeException as exc:
            self._log.error(_ERROR_START_BLUETOOTH_SERVICE, str(exc))
            raise ConnectCoreBLEException(_ERROR_START_BLUETOOTH_SERVICE % str(exc)) from exc
        # Wait for new connections.
        wait_thread = threading.Thread(target=self._stop_service_event.wait)
        wait_thread.start()
        # Set active flag.
        self.service_active = True

    def stop(self):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.stop`
        """
        # Sanity checks.
        if not self.service_active:
            return

        try:
            # Disable bluetooth service in the XBee device.
            self._xbee.disable_bluetooth()
        except XBeeException as exc:
            self._log.error(_ERROR_STOP_BLUETOOTH_SERVICE, str(exc))
            raise ConnectCoreBLEException(_ERROR_STOP_BLUETOOTH_SERVICE % str(exc)) from exc
        # Release wait thread.
        self._stop_service_event.set()
        # Set active flag.
        self.service_active = False

    def send_data(self, data):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.send_data`
        """
        try:
            self._xbee.send_bluetooth_data(data)
        except XBeeException as exc:
            self._log.error(_ERROR_SEND_DATA, str(exc))
            raise ConnectCoreBLEException(_ERROR_SEND_DATA % str(exc)) from exc

    def get_advertising_name(self):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.get_advertising_name`
        """
        try:
            return self._xbee.get_parameter(ATStringCommand.BI.command).decode(encoding="utf-8")
        except XBeeException as exc:
            self._log.error(_ERROR_READ_ADVERTISE_NAME, str(exc))
            raise ConnectCoreBLEException(_ERROR_READ_ADVERTISE_NAME % str(exc)) from exc

    def set_advertising_name(self, device_name):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.set_advertising_name`
        """
        try:
            self._xbee.set_parameter(ATStringCommand.BI.command,
                                     bytearray(device_name, "utf-8"),
                                     apply=True)
        except XBeeException as exc:
            self._log.error(_ERROR_CHANGE_ADVERTISE_NAME, str(exc))
            raise ConnectCoreBLEException(_ERROR_CHANGE_ADVERTISE_NAME % str(exc)) from exc

    def is_device_connected(self):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.is_device_connected`
        """
        return self._connected

    def set_password(self, new_password):
        """
        Override.

        .. seealso::
           | :meth:`.ConnectCoreBLEService.set_password`
        """
        try:
            self._xbee.update_bluetooth_password(new_password)
        except (ValueError, XBeeException) as exc:
            self._log.error(_ERROR_CHANGE_ENCRYPTION_PASSWORD, str(exc))
            raise ConnectCoreBLEException(_ERROR_CHANGE_ENCRYPTION_PASSWORD % str(exc)) from exc

    def _data_received(self, data):
        """
        Callback function to be notified when new data is received from the device
        connected to the XBee.

        Args:
            data (Bytearray): the data received from the device connected to the XBee.
        """
        # Notify corresponding registered service callbacks.
        for callback in self._on_data_received:
            callback(data)

    def _modem_status_changed(self, modem_status):
        """
        Callback function to be notified when the XBee modem status changes.

        Args:
            modem_status (:class:`.ModemStatus`): the new modem status.
        """
        if modem_status == ModemStatus.BLUETOOTH_CONNECTED:
            # A device just connected to the XBee.
            self._connected = True
            # Notify corresponding registered service callbacks.
            for callback in self._on_connect:
                callback()
        elif modem_status == ModemStatus.BLUETOOTH_DISCONNECTED:
            # A device just disconnected from the XBee.
            self._connected = False
            # Notify corresponding registered service callbacks.
            for callback in self._on_disconnect:
                callback()
