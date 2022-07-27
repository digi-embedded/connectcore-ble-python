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

import io
import json
import os
import sys
import threading

from json import JSONDecodeError

from digi.ccble.exceptions import BluetoothNotSupportedException, ConnectCoreBLEException
from digi.ccble.service import ConnectCoreBLEService

# Constants.
DIR_INTERFACES = "interfaces"

ERROR_REQUEST_FORMAT = "Invalid request format: '{}' not specified"

EXTENSION_TEXT = ".txt"

OPERATION_READ = "read"
OPERATION_WRITE = "write"

SETTING_SEPARATOR = "="

STATUS_ERROR = "error"
STATUS_OK = "ok"

TAG_DESCRIPTION = "desc"
TAG_INTERFACE = "interface"
TAG_OPERATION = "operation"
TAG_SETTING = "setting"
TAG_STATUS = "status"
TAG_VALUE = "value"

# Variables.
cc_ble_service = None
interfaces = {}


def data_received_callback(data):
    """
    Callback to be notified when new data is received from the connected device.

    After parsing the data, this method will perform a different action depending on the requested operation:
        - If it is a read request, it will send back the configuration data of the specified interface file.
        - If it is a write request, it will update the configuration data of the specified interface file.

    Args:
        data (Bytearray): received (JSON) data.
    """
    # Parse data as JSON.
    try:
        json_request = json.loads(data.decode("utf-8"))
    except JSONDecodeError:
        print("Error: could not parse JSON data")
        return
    # Check if the JSON data is correct.
    try:
        check_json(json_request)
    except ValueError as exc:
        # Error found during the JSON validation. Send error.
        send_error(str(exc))
        return
    # Process the request.
    process_request(json_request)


def check_json(json_properties):
    """
    Checks if json_properties follows the correct format.

    The defined format is as follows:
    {
        "operation"      : "read" / "write",        required: always
        "interface"      : "<interface_name>",      required: always
        "setting"        : "<setting_name>",        required: always
        "value"          : "<setting_value>",       required: Operation=write
    }

    Args:
        json_properties (Dictionary<String, String>): JSON string to be checked.

    Raises:
        ValueError: if the JSON string is not valid.
    """
    if TAG_OPERATION not in json_properties:
        raise ValueError(ERROR_REQUEST_FORMAT.format(TAG_OPERATION))
    if TAG_INTERFACE not in json_properties:
        raise ValueError(ERROR_REQUEST_FORMAT.format(TAG_INTERFACE))
    if TAG_SETTING not in json_properties:
        raise ValueError(ERROR_REQUEST_FORMAT.format(TAG_SETTING))
    if json_properties[TAG_OPERATION] == OPERATION_WRITE:
        if TAG_VALUE not in json_properties:
            raise ValueError(ERROR_REQUEST_FORMAT.format(TAG_VALUE))


def process_request(json_request):
    """
    Processes the request.

    Args:
        json_request (Dictionary<String, String>): JSON string to be processed.
    """
    # Retrieve the operation to execute.
    operation = json_request[TAG_OPERATION]
    # Retrieve the network interface.
    interface = json_request[TAG_INTERFACE]
    # Check if the interface exists.
    if interface not in interfaces:
        send_error(f"Interface '{interface}' not found")
        return
    # Retrieve the setting.
    setting = json_request[TAG_SETTING]
    # Check if the setting exists in the requested interface.
    if setting not in interfaces[interface]:
        send_error(f"Setting '{setting}' not found in interface '{interface}'")
        return
    # Execute the request.
    if operation == OPERATION_READ:
        json_response = json.dumps({TAG_STATUS: STATUS_OK,
                                    TAG_INTERFACE: interface,
                                    TAG_SETTING: setting,
                                    TAG_VALUE: interfaces[interface][setting]})
        send_data(json_response.encode('utf-8'))
    elif operation == OPERATION_WRITE:
        # Save previous value.
        old_value = interfaces[interface][setting]
        # Set new value.
        interfaces[interface][setting] = json_request[TAG_VALUE]
        # Save new value.
        try:
            save_interface(interface)
            json_response = json.dumps({TAG_STATUS: STATUS_OK})
            send_data(json_response.encode('utf-8'))
        except Exception as exc:
            send_error(f"Could not write setting: {str(exc)}")
            # Restore previous value.
            interfaces[interface][setting] = old_value
            return
    else:
        # If the request is not a read or write request, send an error response.
        send_error(f"Invalid operation '{operation}'")


def send_error(error_message):
    """
    Sends an error message to the client.

    Args:
        error_message (String): error message to be sent.
    """
    json_response = json.dumps({TAG_STATUS: STATUS_ERROR,
                                TAG_DESCRIPTION: error_message})
    send_data(json_response.encode('utf-8'))


def connection_callback():
    """
    Callback to be notified when a new connection is established.
    """
    print(f"Connection established using '{cc_ble_service.get_interface_type().title}'")


def send_data(data):
    """
    Sends data to the connected device through the Bluetooth Low Energy interface.

    Args:
        data (Bytearray): data to be sent.
    """
    try:
        cc_ble_service.send_data(data)
    except ConnectCoreBLEException as exc:
        print(f"Error: could not send data to connected device: {str(exc)}")


def save_interface(interface):
    """
    Saves the given interface.

    Args:
        interface (String): name of the interface to save.
    """
    with io.open(os.path.join(DIR_INTERFACES, interface + EXTENSION_TEXT),
                 'r+', encoding='utf-8') as file:
        # Overwrite file data.
        file.seek(0)
        file.truncate(0)
        for setting in interfaces[interface]:
            file.write(setting + SETTING_SEPARATOR + interfaces[interface][setting] + "\n")


def initialize_interfaces():
    """
    Initializes the interfaces
    """
    # Iterate all files of the interfaces directory.
    for file in os.listdir(DIR_INTERFACES):
        # Check if the file is a text file.
        if file.endswith(EXTENSION_TEXT):
            # Get the interface name.
            interface_name = file.split('.')[0]
            # Initialize interface settings.
            interface_settings = {}
            # Read the interface settings.
            with io.open(os.path.join(DIR_INTERFACES, file), 'r', encoding='utf-8') as iface_file:
                for line in iface_file:
                    line_dict = line.strip().split(SETTING_SEPARATOR)
                    interface_settings[line_dict[0]] = line_dict[1]
            # Add the interface to the list of interfaces.
            interfaces[interface_name] = interface_settings


def main():
    global cc_ble_service

    # Initialize the interfaces.
    try:
        initialize_interfaces()
    except Exception as exc:
        print(f"Error: could not initialize interfaces: {str(exc)}")
        sys.exit(1)
    # Initialize the service.
    try:
        cc_ble_service = ConnectCoreBLEService.get_instance()
    except BluetoothNotSupportedException:
        print("The system does not support bluetooth. Aborting...")
        sys.exit(1)
    # Register service callbacks.
    cc_ble_service.add_data_received_callback(data_received_callback)
    cc_ble_service.add_connect_callback(connection_callback)
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
