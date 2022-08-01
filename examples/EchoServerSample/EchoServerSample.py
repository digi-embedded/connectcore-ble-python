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

import sys
import threading

from digi.ccble.exceptions import BluetoothNotSupportedException, ConnectCoreBLEException
from digi.ccble.service import ConnectCoreBLEService

# Variables.
cc_ble_service = None


def _data_received_callback(data):
    """
    Callback to be notified when new data is received from the connected device.

    Args:
        data (Bytearray): received (JSON) data.
    """
    # Send data back.
    try:
        cc_ble_service.send_data(data)
    except ConnectCoreBLEException as exc:
        print(f"Error sending data: {str(exc)}")


def _connection_callback():
    """
    Callback to be notified when a new connection is established.
    """
    print(f"Connection established through '{cc_ble_service.get_interface_type().title}'")


def main():
    global cc_ble_service

    # Initialize service.
    try:
        cc_ble_service = ConnectCoreBLEService.get_instance()
    except BluetoothNotSupportedException:
        print("The system does not support bluetooth. Aborting...")
        sys.exit(1)
    # Register service callbacks.
    cc_ble_service.add_data_received_callback(_data_received_callback)
    cc_ble_service.add_connect_callback(_connection_callback)
    # Configure thread for service execution.
    application_thread = threading.Thread(target=cc_ble_service.start, daemon=True)
    application_thread.start()
    # Wait for input to stop application.
    print('Service started, hit <ENTER> to stop and exit.')
    try:
        input('> ')
        # Stop the service.
        print('Stopping the service...')
        try:
            cc_ble_service.stop()
            application_thread.join()
            application_thread = threading.Thread(target=cc_ble_service.start, daemon=True)
            print('Service stopped!')
        except ConnectCoreBLEException as exc:
            print(str(exc))
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    main()
