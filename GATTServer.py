# Bluezero modules
from bluezero import constants
from bluezero import adapter
from bluezero import advertisement
from bluezero import localGATT
from bluezero import GATT

# D-Bus module
import dbus

import  threading

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
    try:
        adapter.list_adapters()
    except adapter.AdapterError:
        return False
    if not adapter.Adapter(adapter.list_adapters()[0]).powered:
        return False

    return True


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
        # New tx value
        self.props[constants.GATT_CHRC_IFACE]['Value'] = value

        # Notify new data through the set callback
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
            # Already notifying, nothing to do
            return

        # Notifications on
        self.props[constants.GATT_CHRC_IFACE]['Notifying'] = True

    def StopNotify(self):
        """
        Callback executed when the indicate property of the characteristic is changed to ``False``.
        """
        if not self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            # Not notifying, nothing to do
            return

        # Notifications off
        self.props[constants.GATT_CHRC_IFACE]['Notifying'] = False

    def update_characteristic(self, data):
        """
        Updates the rx characteristic and notifies the changes if notifications are enabled

        Args:
            data (Bytearray): new rx data
        """
        value = encode_bytes(data)

        # New rx value
        self.props[constants.GATT_CHRC_IFACE]['Value'] = value

        # Notifying new value
        if self.props[constants.GATT_CHRC_IFACE]['Notifying']:
            self.PropertiesChanged(constants.GATT_CHRC_IFACE, {'Value': value}, [])
        self.props[constants.GATT_CHRC_IFACE]['Value'] = ''


class GATTServer:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.app = localGATT.Application()
        self.srv = localGATT.Service(1, SER_UUID, True)

        # Writeable characteristic creation
        self.tx_char = TxCharacteristic(self.srv)
        self.tx_char.service = self.srv.path
        self.add_tx_data_callback(self.default_tx_callback)

        # Readable characteristic creation
        self.rx_char = RxCharacteristic(self.srv)
        self.rx_char.service = self.srv.path

        # Characteristic and service registration
        self.app.add_managed_object(self.srv)
        self.app.add_managed_object(self.tx_char)
        self.app.add_managed_object(self.rx_char)

        self.srv_mng = GATT.GattManager(adapter.list_adapters()[0])
        self.srv_mng.register_application(self.app, {})

        # Configure dongle and advertisement
        self.dongle = adapter.Adapter(adapter.list_adapters()[0])
        self.dongle.alias = advertising_name
        advert = advertisement.Advertisement(1, 'peripheral')

        # Start advertisement
        advert.service_UUIDs = [SER_UUID]
        if not self.dongle.powered:
            self.dongle.powered = True
        ad_manager = advertisement.AdvertisingManager(self.dongle.address)
        ad_manager.register_advertisement(advert, {})

        # Define service starting thread
        self.service_thread = threading.Thread(target=self.app.start)

    def start(self):
        """
        Starts the thread service.
        """
        self.service_thread.start()

    def stop(self):
        """
        Stops the thread service.
        """
        self.app.stop()
        self.service_thread.join()

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
