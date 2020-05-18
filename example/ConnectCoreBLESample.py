from BLEService import BLEService
import io
import json
import re

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
        # Create a dictionary from the encoded JSON string in 'data'
        json_properties = json.loads(data.decode('utf-8'))

        try:
            # Check if the JSON data is correct
            self.check_json(json_properties)
        except Exception as e:
            # Error found during the validation. Send back notification
            json_response_error = json.dumps({'Status': str(e)})
            self.BLE_service.send_data(json_response_error.encode('utf-8'))
            return

        interface = json_properties["Interface"]

        # If the message was a write request, overwrite the file properties with the received ones
        if json_properties['Operation'] == 'Write':
            try:
                # If the file is updated correctly, send back confirmation that the operation was successful
                self._set_file_properties(interface, json_properties)
                json_response = json.dumps({'Status': 'OK'})
                self.BLE_service.send_data(json_response.encode('utf-8'))
                return
            except:
                # If a problem is found while updating the file, send back notification of the error
                json_response_error = json.dumps({'Status': 'Error: could not update the interface configuration'})
                self.BLE_service.send_data(json_response_error.encode('utf-8'))
                return

        # If the message was a read request, get the file properties and send them back
        if json_properties['Operation'] == 'Read':
            try:
                # If the properties are read correctly, send back confirmation that the operation was successful
                interface_properties = self._get_file_properties(interface)
                interface_properties.update({'Status': 'OK'})

                # Send the JSON data
                json_response = json.dumps(interface_properties)
                self.BLE_service.send_data(json_response.encode('utf-8'))
                return
            except:
                # If a problem is found while reading the file, send back notification of the error
                json_response_error = json.dumps({'Status': 'Error: could not read the interface configuration'})
                self.BLE_service.send_data(json_response_error.encode('utf-8'))
                return

    def _connection_callback(self):
        """
        Callback to be called after a new connection is established.
        """
        print('Connection established through interface %s', self.BLE_service.get_type())

    def change_advertising_name(self, new_advertising_name):
        """
        Modifies the advertising name of the services.
        """
        self.BLE_service.configure_advertising_name(new_advertising_name)

    @staticmethod
    def _get_file_properties(interface):
        """
        Obtains the properties of the specified network interface file.

        Args:
            interface (String): interface whose properties are obtained.

        Returns:
            A ``Dictionary<String, Sring>`` containing the properties.

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
                # Get dictionary from the old file data and update it
                interface_properties = dict(line.strip().split('=') for line in interface_file)
                interface_properties.update(properties)

                # Eliminate unnecessary fields
                interface_properties.pop('Operation')
                interface_properties.pop('Interface')

                # Overwrite file data
                interface_file.seek(0)
                interface_file.truncate(0)
                interface_file.write('\n'.join('{!s}={!s}'.format(prop, val) for (prop, val) in interface_properties.items()))
        except OSError:
            raise

    @staticmethod
    def check_json(json_properties):
        """
        Checks if json_properties follows the correct format.

        The defined format is as follows:
        {
            "Operation"      : "Read" / "Write",        required: always
            "Interface"      : "Ethernet" / "WiFi",     required: always
            "Type"           : "Static" / "Dynamic",    required: Operation=Write
            "IP Address"     : "xxx.xxx.xxx.xxx",       required: Operation=Write, Type=Static
            "Subnet Mask"    : "xxx.xxx.xxx.xxx",       required: Operation=Write, Type=Static
            "Default Gateway": "xxx.xxx.xxx.xxx",       required: Operation=Write, Type=Static
            "DNS Server 1"   : "xxx.xxx.xxx.xxx",       required: never
            "DNS Server 2"   : "xxx.xxx.xxx.xxx",       required: never
            "MAC Address"    : "xx:xx:xx:xx:xx:xx",     required: never
            "Enabled"        : "True" / "False",        required: never
        }

        Args:
            json_properties (String): JSON string to be checked.

        Raises:
            Exception: if the JSON string does not follow the correct format.
        """
        if 'Operation' not in json_properties:
            raise Exception('Error: operation not specified')
        if 'Interface' not in json_properties or \
                (json_properties['Interface'] != 'Ethernet' and
                 json_properties['Interface'] != 'WiFi'):
            raise Exception('Error: no valid network interface specified')

        if json_properties['Operation'] == 'Write':
            if 'Type' not in json_properties:
                raise Exception('Error: connection type not specified')

            if json_properties['Type'] == 'Static':
                if 'IP Address' not in json_properties or \
                        not re.match('^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$', json_properties['IP Address']):
                    raise Exception('Error: no valid IP address found')
                if 'Subnet Mask' not in json_properties or \
                        not re.match('^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$', json_properties['Subnet Mask']):
                    raise Exception('Error: no valid subnet mask found')
                if 'Default Gateway' not in json_properties or \
                        not re.match('^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$', json_properties['Default Gateway']):
                    raise Exception('Error: no valid default gateway found')
            elif json_properties['Type'] != 'Dynamic':
                raise Exception('Error: invalid connection type')

            if 'DNS Server 1' in json_properties and \
                    not re.match('^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$', json_properties['DNS Server 1']):
                raise Exception('Error: invalid DNS server 1')
            if 'DNS Server 2' in json_properties and \
                    not re.match('^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$', json_properties['DNS Server 2']):
                raise Exception('Error: invalid DNS server 2')
            if 'MAC Address' in json_properties and \
                    not re.match('^([0-9a-fA-F][0-9a-fA-F]:){5}([0-9a-fA-F][0-9a-fA-F])$', json_properties['MAC Address']):
                raise Exception('Error: invalid MAC Address')
            if 'Enabled' in json_properties and \
                    json_properties['Enabled'] != 'True' and \
                    json_properties['Enabled'] != 'False':
                raise Exception('Error: invalid enable value')
        elif json_properties['Operation'] == 'Read':
            if 'Type' in json_properties or \
                    'IP Address' in json_properties or \
                    'Subnet Mask' in json_properties or \
                    'Default Gateway' in json_properties or \
                    'DNS Server 1' in json_properties or \
                    'DNS Server 2' in json_properties or \
                    'MAC Address' in json_properties or \
                    'Enabled' in json_properties:
                raise Exception('Error: too many properties in read request')
        else:
            raise Exception('Error: invalid operation')

if __name__ == '__main__':
    test_json = {
        'Operation': 'Read',
        'Interface': 'WiFi',
        'Type': 'Dynamic',
        'Enabled': 'True'
    }
    json_data = json.dumps(test_json).encode('utf-8')

    sample = ConnectCoreBLESample()
    sample._data_received_callback(json_data)