import sys
sys.path.append('../')

from BLEService import BLEService, BLEServiceNative, BLEServiceXBee
from getpass import getpass
import io
import json
import re
import threading
import time
import traceback
import zlib

IP_V4_REGEX = '^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\\.(?!$)|$)){4}$'
MAC_REGEX = '^([0-9a-fA-F][0-9a-fA-F]:){5}([0-9a-fA-F][0-9a-fA-F])$'


class ConnectCoreBLESample:
    """
        This class provides an example on how to use the Connect Core BLE Python API.
    """

    def __init__(self):
        self.BLE_service = BLEService.get_instance()

        self.BLE_service.add_data_received_callback(self._data_received_callback)
        self.BLE_service.add_connect_callback(self._connection_callback)

    def start(self):
        """
        Enables the BLE services.
        """
        self.BLE_service.start_service()

    def stop(self):
        """
        Disables the BLE services.
        """
        self.BLE_service.stop_service()

    def _data_received_callback(self, data):
        """
        Callback to be called after new JSON data is received.
        After parsing the data, this method will perform a different action depending on the requested operation:
            - If it is a read request, it will send back the configuration data of the specified interface file.
            - If it is a write request, it will update the configuration of the specified interface file.

        Args:
            data (Bytearray): received JSON data.
        """
        # Decompress the received data.
        decompressed_data = zlib.decompress(data, -zlib.MAX_WBITS)

        # Create a dictionary from the encoded JSON string in 'decompressed_data'.
        json_properties = json.loads(decompressed_data.decode('utf-8'))

        try:
            # Check if the JSON data is correct.
            self._check_json(json_properties)
        except Exception as e:
            # Error found during the validation. Send back notification.
            json_response_error = json.dumps({'Operation': json_properties['Operation'], 'Status': str(e)})
            self._send_compressed_data(json_response_error.encode('utf-8'))
            return

        interface = json_properties["Interface"]

        # If the message was a write request, overwrite the file properties with the received ones.
        if json_properties['Operation'] == 'Write':
            try:
                # If the file is updated correctly, send back confirmation that the operation was successful.
                self._set_file_properties(interface, json_properties)
                json_response = json.dumps({'Operation': 'Write', 'Status': 'OK'})
                self._send_compressed_data(json_response.encode('utf-8'))
                return
            except:
                # If a problem is found while updating the file, send back notification of the error.
                json_response_error = json.dumps({'Operation': 'Write', 'Status': 'Error: could not update'})
                self._send_compressed_data(json_response_error.encode('utf-8'))
                return

        # If the message was a read request, get the file properties and send them back.
        if json_properties['Operation'] == 'Read':
            try:
                # If the properties are read correctly, send back confirmation that the operation was successful.
                interface_properties = self._get_file_properties(interface)
                interface_properties.update({'Operation': 'Read', 'Status': 'OK'})

                # Prepare the JSON data.
                json_response = json.dumps(interface_properties)

                # Wait until the client is ready to receive data.
                time.sleep(1)

                # Send the data.
                self._send_compressed_data(json_response.encode('utf-8'))
                return
            except:
                traceback.print_exc()
                # If a problem is found while reading the file, send back notification of the error.
                json_response_error = json.dumps({'Operation': 'Read', 'Status': 'Error: Could not read'})
                self._send_compressed_data(json_response_error.encode('utf-8'))
                return

    def _connection_callback(self):
        """
        Callback to be called after a new connection is established.
        """
        print('Connection established through ' + self.BLE_service.get_type())

    def change_advertising_name(self, new_advertising_name):
        """
        Modifies the advertising name of the services.

        Args:
            new_advertising_name (String).
        """
        self.BLE_service.configure_advertising_name(new_advertising_name)

    def _send_compressed_data(self, data):
        """
        Compresses the data and sends it through the Bluetooth Low Energy interface.
        Since the JSON strings are too long, they must get compressed in order to fit within reasonable MTU values,
        such as 185 on iOs.

        Args:
            data (Bytearray): data to be compressed and sent.
        """
        try:
            compressed_json = zlib.compress(data)[2:-1]
            self.BLE_service.send_data(compressed_json)
        except:
            traceback.print_exc()
            raise

    @staticmethod
    def _get_file_properties(interface):
        """
        Obtains the properties of the specified network interface file.

        Args:
            interface (String): interface whose properties are obtained.

        Returns:
            A ``Dictionary<String, String>`` containing the properties.

        Raises:
            OSError: if an error is found while processing the file.
        """
        try:
            with io.open('interfaces/' + interface + '.txt', 'r', encoding='utf-8') as interface_file:
                interface_properties = dict(line.strip().split('=') for line in interface_file)
        except OSError:
            raise
        return interface_properties

    @staticmethod
    def _set_file_properties(interface, properties):
        """
        Updates the properties of the specified network interface file.

        Args:
            interface (String): interface whose properties are updated.
            properties (Dictionary<String, String>): interface whose properties are modified.

        Raises:
            OSError: if an error is found while processing the file.
        """
        try:
            with io.open('interfaces/' + interface + '.txt', 'r+', encoding='utf-8') as interface_file:
                # Get dictionary from the old file data and update it.
                interface_properties = dict(line.strip().split('=') for line in interface_file)
                interface_properties.update(properties)

                # Eliminate unnecessary fields.
                interface_properties.pop('Operation')
                interface_properties.pop('Interface')

                # Overwrite file data.
                interface_file.seek(0)
                interface_file.truncate(0)
                interface_file.write(
                    '\n'.join('{!s}={!s}'.format(prop, val) for (prop, val) in interface_properties.items()))
        except OSError:
            raise

    @staticmethod
    def _check_json(json_properties):
        """
        Checks if json_properties follows the correct format.

        The defined format is as follows:
        {
            "Operation"      : "Read" / "Write",        required: always
            "Interface"      : "Ethernet" / "WiFi",     required: always
            "Type"           : "Static" / "Dynamic",    required: Operation=Write
            "IP"             : "xxx.xxx.xxx.xxx",       required: Operation=Write, Type=Static
            "Netmask"        : "xxx.xxx.xxx.xxx",       required: Operation=Write, Type=Static
            "Gateway"        : "xxx.xxx.xxx.xxx",       required: Operation=Write, Type=Static
            "DNS"            : "xxx.xxx.xxx.xxx",       required: never
            "MAC"            : "xx:xx:xx:xx:xx:xx",     required: never
            "Enabled"        : "True" / "False",        required: never
        }

        Args:
            json_properties (Dictionary<String, String>): JSON string to be checked.

        Raises:
            Exception: if the JSON string does not follow the correct format.
        """
        if 'Operation' not in json_properties:
            raise Exception('Error: Wrong operation')
        if 'Interface' not in json_properties or \
                (json_properties['Interface'] != 'Ethernet' and
                 json_properties['Interface'] != 'WiFi'):
            raise Exception('Error: Wrong interface')

        if json_properties['Operation'] == 'Write':
            if 'Type' not in json_properties:
                raise Exception('Error: Wrong connection type')

            if json_properties['Type'] == 'Static':
                if 'IP' not in json_properties or \
                        not re.match(IP_V4_REGEX, json_properties['IP']):
                    raise Exception('Error: Wrong IP')
                if 'Netmask' not in json_properties or \
                        not re.match(IP_V4_REGEX, json_properties['Netmask']):
                    raise Exception('Error: Wrong netmask')
                if 'Gateway' not in json_properties or \
                        not re.match(IP_V4_REGEX, json_properties['Gateway']):
                    raise Exception('Error: Wrong gateway')
            elif json_properties['Type'] != 'Dynamic':
                raise Exception('Error: Wrong connection type')

            if 'DNS' in json_properties and \
                    not re.match(IP_V4_REGEX, json_properties['DNS']):
                raise Exception('Error: Wrong DNS')
            if 'MAC' in json_properties and \
                    not re.match(MAC_REGEX, json_properties['MAC']):
                raise Exception('Error: Wrong MAC')
            if 'Enabled' in json_properties and \
                    json_properties['Enabled'] != 'True' and \
                    json_properties['Enabled'] != 'False':
                raise Exception('Error: Wrong enable value')
        elif json_properties['Operation'] == 'Read':
            if 'Type' in json_properties or \
                    'IP' in json_properties or \
                    'Netmask' in json_properties or \
                    'Gateway' in json_properties or \
                    'DNS' in json_properties or \
                    'MAC' in json_properties or \
                    'Enabled' in json_properties:
                raise Exception('Error: Too many properties')
        else:
            raise Exception('Error: Wrong operation')


if __name__ == '__main__':

    sample = ConnectCoreBLESample()
    application_thread = threading.Thread(target=sample.start, daemon=True)

    # Application menu:
    #    start    - Begins the advertisement and the service.
    #    stop     - Stops the advertisement and the service.
    #    name     - Asks for a new advertising name.
    #    password - Asks for a new password for the BLE authentication.
    #    exit     - Ends the execution of the application.

    while True:
        user_input = input('> ')
        if user_input == 'start':
            if not sample.BLE_service.service_active:
                print('Starting the service.')
                application_thread.start()
            else:
                print('Service already running.')
        elif user_input == 'stop':
            if sample.BLE_service.service_active:
                print('Stopping the service.')
                sample.stop()
                application_thread.join()
                application_thread = threading.Thread(target=sample.start, daemon=True)
            else:
                print('The service is not running.')
        elif user_input == 'name':
            new_advertising_name = input('> New advertising name: ')
            try:
                sample.BLE_service.configure_advertising_name(new_advertising_name)
            except:
                print('Unable to set new advertising name.')
        elif user_input == 'password':
            if not sample.BLE_service.service_active:
                new_password = getpass('> New password: ')
                sample.BLE_service.set_password(new_password)
            else:
                print('Stop the service before changing the password.')
        elif user_input == 'exit':
            if sample.BLE_service.service_active:
                print('Stopping the service.')
                sample.stop()
                application_thread.join()
            break
