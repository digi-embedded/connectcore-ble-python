# Enum modules
from enum import Enum
from enum import unique

# Bluezero modules
from bluezero import constants
from bluezero import adapter
from bluezero import advertisement
from bluezero import localGATT
from bluezero import GATT

# D-Bus module
import dbus

# Standard modules
import threading

import utils

SER_UUID = '53DA53B9-0447-425A-B9EA-9837505EB59A'
TX_CHAR_UUID = '7DDDCA00-3E05-4651-9254-44074792C590'
RX_CHAR_UUID = 'F9279EE9-2CD0-410C-81CC-ADF11E4E5AEA'

advertising_name = 'ConnectCore BLE'


def encode_bytes(value):
    """
    Transforms the given ``Bytearray`` value in a ``dbus.Array``.

    Args:
        value (Bytearray): the value to transform to ``dbus.Array``.

    Returns:
        dbus.Array - The value transformed in ``dbus.Array``.
    """
    encoded_data = []
    for bytes in value:
        encoded_data.append(dbus.Byte(bytes))

    return encoded_data


def decode_bytes(value):
    """
    Transforms the given ``dbus.Array`` value in a ``Bytearray``.

    Args:
        value (dbus.Array): the value to transform to Bytearray.

    Returns:
        Bytearray - The value transformed in Bytearray.
    """
    decoded_data = bytearray()
    for byte in value:
        decoded_data.append(int(byte))

    return decoded_data


def is_bluetooth_available():
    """
    Checks for an available, powered bluetooth adapter on the device.

    Returns:
        True if it finds at least one available adapter. False otherwise.
    """
    try:
        adapter.list_adapters()
    except adapter.AdapterError:
        return False
    if not adapter.Adapter(adapter.list_adapters()[0]).powered:
        return False

    return True


@unique
class GATTConnectionStatus(Enum):
    """
    Enumerates the possible connection statuses of the GATT server as detected by the DBus.
    """
    DISCONNECTED = (0, "The GATT server is NOT connected to any other device")
    CONNECTED = (1, "The GATT server is connected to another device")
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
            return GATTConnectionStatus.UNKNOWN

    code = property(__get_code)
    description = property(__get_description)


GATTConnectionStatus.lookupTable = {x.code: x for x in GATTConnectionStatus}
GATTConnectionStatus.__doc__ += utils.doc_enum(GATTConnectionStatus)


class TxCharacteristic(localGATT.Characteristic):
    def __init__(self, service):
        localGATT.Characteristic.__init__(self,
                                          1,
                                          TX_CHAR_UUID,
                                          service,
                                          '',
                                          False,
                                          ['write'])

    def WriteValue(self, value, options):
        """
        Callback executed when the write method of the characteristic is called.

        Updates the value property of the characteristic and notifies about changes in the properties.

        Args:
            value (dbus.Array): the new value written in the characteristic.
            options (Integer): write options.
        """
        # New tx value.
        self.props[constants.GATT_CHRC_IFACE]['Value'] = value

        # Notify new data through the set callback.
        self.PropertiesChanged(decode_bytes(value))


class RxCharacteristic(localGATT.Characteristic):
    def __init__(self, service):
        localGATT.Characteristic.__init__(self,
                                          2,
                                          RX_CHAR_UUID,
                                          service,
                                          '',
                                          False,
                                          ['indicate'])

    def StartNotify(self):
        """
        Callback executed when the indicate property of the characteristic is changed to ``True``.
        """
        if self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            # Already notifying, nothing to do.
            return

        # Notifications on.
        self.props[constants.GATT_CHRC_IFACE]['Notifying'] = True

    def StopNotify(self):
        """
        Callback executed when the indicate property of the characteristic is changed to ``False``.
        """
        if not self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            # Not notifying, nothing to do.
            return

        # Notifications off.
        self.props[constants.GATT_CHRC_IFACE]['Notifying'] = False

    def update_characteristic(self, data):
        """
        Updates the rx characteristic and notifies the changes if notifications are enabled.

        Args:
            data (Bytearray): new rx data.
        """
        value = encode_bytes(data)

        # New rx value.
        self.props[constants.GATT_CHRC_IFACE]['Value'] = value

        # Notifying new value.
        if self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            self.PropertiesChanged(constants.GATT_CHRC_IFACE, {'Value': value}, [])
        self.props[constants.GATT_CHRC_IFACE]['Value'] = ''


class GATTServer:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.app = localGATT.Application()
        self.srv = localGATT.Service(1, SER_UUID, True)

        # Writeable characteristic creation.
        self.tx_char = TxCharacteristic(self.srv)
        self.tx_char.service = self.srv.path
        self.add_tx_data_callback(self.default_tx_callback)

        # Readable characteristic creation.
        self.rx_char = RxCharacteristic(self.srv)
        self.rx_char.service = self.srv.path

        # Characteristic and service registration.
        self.app.add_managed_object(self.srv)
        self.app.add_managed_object(self.tx_char)
        self.app.add_managed_object(self.rx_char)

        self.srv_mng = GATT.GattManager(adapter.list_adapters()[0])
        self.srv_mng.register_application(self.app, {})

        # Configure dongle and advertisement.
        self.dongle = adapter.Adapter(adapter.list_adapters()[0])
        self.dongle.alias = advertising_name
        self.advert = advertisement.Advertisement(1, 'peripheral')

        # Register advertisement.
        self.advert.service_UUIDs = [SER_UUID]
        if not self.dongle.powered:
            self.dongle.powered = True
        self.ad_manager = advertisement.AdvertisingManager(self.dongle.address)

        # Dictionary of devices subscribed by the DBus, associated with the signal they are subscribed to.
        self._dbus_subscribed_devices = {}

        # Get DBus object manager and start listening for new interfaces.
        bluez_proxy = self.bus.get_object('org.bluez', "/")
        self.object_manager = dbus.Interface(bluez_proxy, "org.freedesktop.DBus.ObjectManager")
        self.object_manager.connect_to_signal("InterfacesAdded", self._subscribe_dbus_managed_device)
        self.object_manager.connect_to_signal("InterfacesRemoved", self._unsubscribe_dbus_managed_device)

        # Every device managed by the DBus will listen for the PropertiesChanged signal.
        self._subscribe_dbus_managed_objects()

        # Connection callback definition.
        self._on_connection_changed = None

    def start(self):
        """
        Starts the thread service.
        """
        # Start advertisement.
        self.ad_manager.register_advertisement(self.advert, {})

        self.app.start()

    def stop(self):
        """
        Stops the thread service.
        """
        # Stop advertisement.
        self.ad_manager.unregister_advertisement(self.advert)

        self.app.stop()

    def default_tx_callback(self, value):
        """
        Default callback to be called after tx data is received.

        Args:
            value (Bytearray): tx data.
        """
        print('Data received: ' + value.decode('utf-8'))

    def add_tx_data_callback(self, callback):
        """
        Sets new callback to be called after tx data is received.

        Args:
            callback (Function): the callback. Receives a ``Bytearray``.
        """
        self.tx_char.add_call_back(callback)

    def del_tx_data_callback(self, callback):
        """
        Stops the callback from being called after tx data is received.

        Args:
            callback (Function): the callback. Receives a ``Bytearray``.
        """
        if callback == self.tx_char.PropertiesChanged:
            self.tx_char.add_call_back(self.default_tx_callback)

    def send_rx_data(self, data):
        """
        Sends new data to the rx characteristic.

        Args:
            data (Byterray): rx data to be sent to the rx characteristic.
        """
        self.rx_char.update_characteristic(data)

    def configure_advertising_name(self, device_name):
        """
        Modifies the advertised device name.

        Args:
            device_name (String): new advertised name.
        """
        global advertising_name

        advertising_name = device_name
        self.dongle.alias = advertising_name

    def get_connection_status(self):
        """
        Checks if any of the DBus managed objects is a connected device.

        Returns:
            ``GATTConnectionStatus.CONNECTED`` if it finds a device managed object with Connected property set to True.
            ``GATTConnectionStatus.DISCONNECTED`` otherwise.
        """
        objects = self.object_manager.GetManagedObjects()

        for obj_path in objects:
            obj_proxy = self.bus.get_object('org.bluez', obj_path)
            prop = dbus.Interface(obj_proxy, "org.freedesktop.DBus.Properties")

            # Check if any interface within the object is a device,
            # and if so, check if Connected property is True.
            for interface in objects[obj_path]:
                if interface == 'org.bluez.Device1':
                    if prop.Get('org.bluez.Device1', "Connected"):
                        return GATTConnectionStatus.CONNECTED

        return GATTConnectionStatus.DISCONNECTED

    def add_connection_changed_callback(self, callback):
        """
        Sets new callback to be called after the connection status changes.

        Args:
            callback (Function): the callback. Receives a ``GATTConnectionStatus`` element.
        """
        self._on_connection_changed = callback

    def del_connection_changed_callback(self, callback):
        """
        Removes callback to be called after the connection status changes.

        Args:
            callback (Function): the callback. Receives a ``GATTConnectionStatus`` element.
        """
        if self._on_connection_changed == callback:
            self._on_connection_changed = None

    def _subscribe_dbus_managed_objects(self):
        """
        Subscribes every device managed by the DBus object to the PropertiesChanged signal.
        """
        objects = self.object_manager.GetManagedObjects()

        for obj_path in objects:
            if obj_path not in self._dbus_subscribed_devices:
                for interface in objects[obj_path]:
                    if interface == 'org.bluez.Device1':
                        obj_proxy = self.bus.get_object('org.bluez', obj_path)
                        prop = dbus.Interface(obj_proxy, "org.freedesktop.DBus.Properties")
                        self._dbus_subscribed_devices[obj_path] = \
                            prop.connect_to_signal("PropertiesChanged", self._dbus_connected_changed_callback)

    def _subscribe_dbus_managed_device(self, path=None, interfaces_and_properties=None):
        """
        Subscribes the added device with object path "path" to the PropertiesChanged signal.

        This method can be triggered in response to a DBus InterfacesAdded signal, so it follows the signature
        described by the signal.

        See https://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-properties

        Args:
            path (OBJPATH).
            interfaces_and_properties (DICT<STRING, DICT<STRING, VARIANT>>).
        """
        for interface in interfaces_and_properties:
            if interface == 'org.bluez.Device1':
                if path not in self._dbus_subscribed_devices:
                    obj_proxy = self.bus.get_object('org.bluez', path)
                    prop = dbus.Interface(obj_proxy, "org.freedesktop.DBus.Properties")
                    self._dbus_subscribed_devices[path] = \
                        prop.connect_to_signal("PropertiesChanged", self._dbus_connected_changed_callback)

                    # To assure that the connection methods are executed even if the interface gets added after
                    # 'Connected' is changed, skipping the signal.
                    connected = prop.Get('org.bluez.Device1', 'Connected')
                    if connected:
                        self._dbus_connected_changed_callback('org.bluez.Device1', {'Connected': connected})

    def _unsubscribe_dbus_managed_device(self, path=None, interfaces=None):
        """
        Unsubscribes the removed device with object path "path" from the PropertiesChanged signal.

        This method can be triggered in response to a DBus InterfacesRemoved signal, so it follows the signature
        described by the signal.

        See https://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-properties

        Args:
            path (OBJPATH).
            interfaces (DICT<STRING, DICT<STRING, VARIANT>>).
        """
        for interface in interfaces:
            if interface == 'org.bluez.Device1':
                if path in self._dbus_subscribed_devices:
                    self._dbus_subscribed_devices[path].remove()
                    self._dbus_subscribed_devices.pop(path)

    def _dbus_connected_changed_callback(self, interface, changed, invalidated=None):
        """
        Callback function to be called when a DBus PropertiesChanged signal is recieved. Checks if the ``Connected``
        property has changed, and calls the corresponding method if that is the case.

        This method can be triggered in response to a DBus PropertiesChanged signal, so it follows the signature
        described by the signal.

        See https://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-properties

        Note: the PropertiesChanged signal on the Connected property only triggers correctly with bonded devices.

        Args:
            interface (STRING).
            changed (DICT<STRING, VARIANT>).
            invalidated (ARRAY<STRING>).
        """
        if 'Connected' in changed:
            if changed['Connected']:
                if self._on_connection_changed:
                    self._on_connection_changed(GATTConnectionStatus.CONNECTED)
            else:
                if self._on_connection_changed:
                    self._on_connection_changed(GATTConnectionStatus.DISCONNECTED)
