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

import logging

from bluezero.peripheral import Peripheral
from dbus.exceptions import DBusException
from digi.ccble import utils

# Constants.
CHAR_RX_ID = 1
CHAR_RX_UUID = "F9279EE9-2CD0-410C-81CC-ADF11E4E5AEA"
CHAR_TX_ID = 2
CHAR_TX_UUID = "7DDDCA00-3E05-4651-9254-44074792C590"
PERIPHERAL_NAME = "CONNECTCORE_{}"
SERVICE_ID = 1
SERVICE_UUID = "53DA53B9-0447-425A-B9EA-9837505EB59A"
DEFAULT_MTU = 27 - 3


class ConnectCoreBLEPeripheral(Peripheral):
    """
    Class used to represent a Bluetooth Low Energy UART peripheral.

    The peripheral offers a UART service with two characteristics:
      - TX Characteristic: Used to allow connected devices to send data.
      - RX Characteristic: Used to allow connected devices to read/receive data.
    """

    # Variables.
    _log = logging.getLogger(__name__)

    def __init__(self, adapter_address):
        """
        Class constructor. Instantiates a new :class:`.ConnectCoreBLEPeripheral` object
        with the given adapter address.

        Args:
            adapter_address (String): local adapter address.
        """
        # Call Peripheral constructor.
        Peripheral.__init__(self,
                            adapter_address,
                            local_name=PERIPHERAL_NAME.format(
                                "".join(adapter_address.split(":")[-2:])))

        # Initialize variables.
        self._rx_characteristic = None
        self._running = False
        self._connected = False
        self._data_received_callbacks = []
        self._connection_changed_callbacks = []
        self._mtu = DEFAULT_MTU

        # Create UART service.
        self.add_service(srv_id=SERVICE_ID, uuid=SERVICE_UUID, primary=True)
        # Create RX characteristic (available data for the device)
        self.add_characteristic(srv_id=SERVICE_ID,
                                chr_id=CHAR_RX_ID,
                                uuid=CHAR_RX_UUID,
                                value=[],
                                notifying=False,
                                flags=['notify'],
                                read_callback=None,
                                write_callback=None,
                                notify_callback=self._notify_changed)
        # Create TX characteristic (incoming data from the device)
        self.add_characteristic(srv_id=SERVICE_ID,
                                chr_id=CHAR_TX_ID,
                                uuid=CHAR_TX_UUID,
                                value=[],
                                notifying=False,
                                flags=['write', 'write-without-response'],
                                read_callback=None,
                                write_callback=self._data_written,
                                notify_callback=None)
        # Register connection callbacks.
        self.on_connect = self._device_connected
        self.on_disconnect = self._device_disconnected

    def _data_written(self, value, _options):
        """
        Callback function to be notified when new data is written to the
        TX characteristic by the device.

        Args:
            value (Byterray): data written to the TX characteristic.
            _options (Dict): options used to write the data.
        """
        self._log.debug("Data written: %s", utils.hex_to_string(value))
        self._mtu = max(len(value), self._mtu)
        # Notify callbacks if any.
        for callback in self._data_received_callbacks:
            callback(value)

    def _notify_changed(self, notifying, characteristic):
        """
        Callback function to be notified when the notify state of the RX
        characteristic changes.

        Args:
            notifying (Boolean): `True` if the RX characteristic is notifying,
                                 `False` otherwise.
            characteristic (:class:`.GATTCharacteristic`): RX characteristic.
        """
        self._log.info("RX notify state changed: %s", notifying)
        # When the notify state changes, update the RX characteristic.
        if notifying:
            self._rx_characteristic = characteristic
        else:
            self._rx_characteristic = None

    def _device_connected(self, device=None, _address=None):
        """
        Callback function to be notified when a device connects.

        Args:
            device (:class:`.Device`): device instance of the connected target.
            _address (String): local adapter address followed by the remote address.
        """
        self._log.info("Device connected" if device is None else "Device connected: %s", device)
        self._connected = True
        # Notify callbacks if any.
        for callback in self._connection_changed_callbacks:
            callback(True)

    def _device_disconnected(self, device=None, _address=None):
        """
        Callback function to be notified when a device disconnects.

        Args:
            device (:class:`.Device`): device instance of the disconnected target.
            _address (String): local adapter address followed by the remote address.
        """
        self._log.info("Device disconnected" if device is None else
                       "Device disconnected: %s", device)
        self._connected = False
        # Notify callbacks if any.
        for callback in self._connection_changed_callbacks:
            callback(False)

    def start(self):
        """
        Starts the peripheral.
        """
        self._log.info("Starting peripheral '%s'...", self.local_name)
        self._running = True
        try:
            self.publish()
        except Exception as exc:
            self._log.error("Error starting peripheral: %s", str(exc))
            self._running = False
            raise

    def stop(self):
        """
        Stops the peripheral.
        """
        self.mainloop.quit()
        try:
            self.ad_manager.unregister_advertisement(self.advert)
        except DBusException:
            # Ignore this error, service has stopped.
            pass
        self._running = False
        self._log.info("Peripheral stopped")

    def send_rx_data(self, data):
        """
        Sends new data to the RX Characteristic.

        Args:
            data (Byterray): data to be sent to the RX Characteristic.

        Raises:
            DBusException: if there is any error writing in the RX characteristic.
        """
        if self._rx_characteristic is not None:
            sent_bytes = 0
            # Slice the data to send.
            while sent_bytes < len(data):
                # There is no way to retrieve the negotiated MTU in the connection. Start with a
                # conservative value and set it to the maximum length of all received data.
                bytes_to_send = min(len(data), self._mtu)
                self._rx_characteristic.set_value(data[sent_bytes:sent_bytes + bytes_to_send])
                sent_bytes += bytes_to_send
                self._log.debug("Sent data: %s", utils.hex_to_string(data[sent_bytes:sent_bytes + bytes_to_send]))

    def get_advertising_name(self):
        """
        Returns the advertising device name.

        Returns:
            String: the advertising name.
        """
        return self.local_name

    def configure_advertising_name(self, device_name):
        """
        Modifies the advertising device name.

        Args:
            device_name (String): new advertising name.
        """
        self._log.info("Configuring advertising name to '%s'", device_name)
        self.local_name = device_name
        if not self._connected and self._running:
            self.stop()
            self.start()

    def is_device_connected(self):
        """
        Returns whether there is any device connected or not.

        Returns:
            Boolean: `True` if there is any device connected, `False` otherwise.
        """
        return self._connected

    def add_connection_changed_callback(self, callback):
        """
        Adds a new callback to be notified when the connection status changes.

        Args:
            callback (Function): the callback function to add. Receives a `Boolean` object.
        """
        if callback not in self._connection_changed_callbacks:
            self._connection_changed_callbacks.append(callback)

    def del_connection_changed_callback(self, callback):
        """
        Removes the given callback from the list.

        Args:
            callback (Function): the callback function to remove.
        """
        if callback in self._connection_changed_callbacks:
            self._connection_changed_callbacks.remove(callback)

    def add_data_received_callback(self, callback):
        """
        Adds a new callback to be notified when data is written to the TX characteristic.

        Args:
            callback (Function): the callback function to add. Receives a `Byterray` object.
        """
        if callback not in self._data_received_callbacks:
            self._data_received_callbacks.append(callback)

    def del_data_received_callback(self, callback):
        """
        Removes the given callback from the list.

        Args:
            callback (Function): the callback function to remove.
        """
        if callback in self._data_received_callbacks:
            self._data_received_callbacks.remove(callback)
