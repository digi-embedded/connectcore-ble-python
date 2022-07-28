ConnectCore Bluetooth Low Energy Library User Guide
===================================================

The ConnectCore Bluetooth Low Energy Python library provides the ability to
communicate your Digi International's `ConnectCore <https://www.digi.com/products/browse/connectcore>`_
modules with mobile applications using the `Digi XBee Mobile SDK
<https://www.digi.com/resources/documentation/digidocs/PDFs/90002361.pdf>`_.

For this purpose, a local GATT server is created using the native Bluetooth
support of the device. This GATT server emulates the one included in XBee 3
modules, which includes an RX and TX characteristic to communicate with the
connected device. This is really useful when developing mobile applications
using the 'Digi XBee Mobile SDK', as the same communication protocol and
library is used.

.. note::
   If native Bluetooth support is not available in the ConnectCore device, the
   library can search for an XBee 3 BLE capable module attached to it to be
   used as the communication interface instead of the GATT server.

Once the connection between the service and the remote device is established,
the communication is authenticated and encrypted using the SRP protocol. For
this step, the same password is required by the remote device and the service.
The service takes care of the authentication and encryption process. You can,
however, change the authentication password at any time.

All this functionality is abstracted in the library in the form of a service
named **ConnectCoreBLEService**. You can instantiate this service and the
library will create the appropriate communication interface based on the
preferred BLE communication interface and the availability of native Bluetooth
and XBee 3 module attached to the device.

The user guide covers the following points:

* :ref:`serviceInstantiate`
* :ref:`serviceStartStop`
* :ref:`serviceConnectionEvents`
* :ref:`serviceDataAvailable`
* :ref:`serviceSendData`
* :ref:`serviceChangeAdvertising`
* :ref:`serviceChangePassword`


.. _serviceInstantiate:

Instantiate the service
-----------------------

The first step to start using the ConnectCore Bluetooth Low Energy library is
to instantiate a **ConnectCoreBLEService** service. This service allows you to
control the operating state, subscribe listeners to be notified on events, and
perform some configuration actions, such as change the authentication password
and advertising name.

The service does not have a constructor, instead it provides a static function
to generate a unique instance based on the preferred BLE interface:

+------------------------+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Class                  | Static method                   | Description                                                                                                                                                                                                            |
+========================+=================================+========================================================================================================================================================================================================================+
| ConnectCoreBLEService  | **get_instance(ble_interface)** | Checks the available Bluetooth interfaces of the device and generates a single instance of the class based on the preferred BLE interface. If an instance does already exist, the method simply returns that instance. |
+------------------------+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

The available Bluetooth Low Energy interfaces are the following:

* **``BLEInterface.BLE_NATIVE``**: Native Bluetooth adapter.
* **``BLEInterface.BLE_XBEE3``**: XBee 3 BLE module.
* **``BLEInterface.BLE_XBEE3_ANY``**: Native Bluetooth adapter, if available,
  otherwise XBee 3. This is the default option.

**Instantiate the ConnectCoreBLEService service**

.. code:: python

  [...]

  from digi.ccble.service import BLEInterface, ConnectCoreBLEService
  from digi.ccble.exceptions import BluetoothNotSupportedException

  [...]

  # Instantiate the ConnectCoreBLEService service.
  try:
      service = ConnectCoreBLEService(ble_interface=BLEInterface.ANY)
  except BluetoothNotSupportedException as exc:
      print("%s" % str(exc))

  [...]

The previous method may fail for the following reasons:

* No valid Bluetooth interface is found in the system, throwing a
  ``BluetoothNotSupportedException``.


.. _serviceStartStop:

Start and stop the service
--------------------------

Once the service is instantiated, you can control when to start and stop it
using the corresponding methods.

When the service starts, the advertisement process begins and the device is
discoverable by others accepting new connections. Stopping the server
interrupts the advertisement process. At this point, the device is no longer
discoverable and does not accept new connections.

+-------------------+------------------------------------------------+
| Method            | Description                                    |
+===================+================================================+
| **start()**       | Starts the service.                            |
+-------------------+------------------------------------------------+
| **stop()**        | Stops the service.                             |
+-------------------+------------------------------------------------+
| **is_running()**  | Returns whether the service is running or not. |
+-------------------+------------------------------------------------+

**Start/Stop the service**

.. code:: python

  [...]

  from digi.ccble.service import ConnectCoreBLEService
  from digi.ccble.exceptions import ConnectCoreBLEException

  [...]

  service = ...

  [...]

  # Start the service.
  try:
      service.start()
  except ConnectCoreBLEException as exc:
      print("%s" % str(exc))

  [...]

  if service.is_running():
      # Stop the service.
      try:
          service.stop()
      except ConnectCoreBLEException as exc:
          print("%s" % str(exc))

The previous methods may fail for the following reasons:

* There is an error starting the service, throwing a
  ``ConnectCoreBLEException``.
* There is an error stopping the service, throwing a
  ``ConnectCoreBLEException``.


.. _serviceConnectionEvents:

Receive device connection events
--------------------------------

When the service is running, it is very useful to receive device connection
events to take specific action when an external device connects or disconnects
from your device. The library provides methods to register callbacks for this
kind of events and also to check whether a device is connected or not.

To be notified on these events, register the proper callback in the service:

+------------------------------------------+-----------------------------------------------------------------------------------------------+
| Method                                   | Description                                                                                   |
+==========================================+===============================================================================================+
| **add_connect_callback(callback)**       | Adds a new callback to the list of callbacks that will be notified when a device connects.    |
+------------------------------------------+-----------------------------------------------------------------------------------------------+
| **remove_connect_callback(callback)**    | Removes the given callback from the list of ``connect`` callbacks.                            |
+------------------------------------------+-----------------------------------------------------------------------------------------------+
| **add_disconnect_callback(callback)**    | Adds a new callback to the list of callbacks that will be notified when a device disconnects. |
+------------------------------------------+-----------------------------------------------------------------------------------------------+
| **remove_disconnect_callback(callback)** | Removes the given callback from the list of ``disconnect`` callbacks.                         |
+------------------------------------------+-----------------------------------------------------------------------------------------------+
| **is_device_connected()**                | Returns whether there is any device connected to the service or not.                          |
+------------------------------------------+-----------------------------------------------------------------------------------------------+

**Connection callbacks**

.. code:: python

  [...]

  from digi.ccble.service import ConnectCoreBLEService

  [...]

  service = ...

  [...]

  # Device connected callback.
  def _connect_callback():
    """
    Callback to be notified when a new connection is established.
    """
    print("Device connected")

  # Device disconnected callback.
  def _disconnect_callback():
    """
    Callback to be notified when a new connection is established.
    """
    print("Device disconnected")

  [...]

  # Register connection callbacks.
  service.add_connect_callback(_connect_callback)
  service.add_disconnect_callback(_disconnect_callback)

  [...]

  if service.is_device_connected():
      # Take specific action.

  [...]

  # Remove connection callbacks.
  service.remove_connect_callback(_connect_callback)
  service.remove_disconnect_callback(_disconnect_callback)


.. _serviceDataAvailable:

Receive data from connected device
----------------------------------

After a device connects to the service, it might start sending data. Register a
callback to be notified when new data is received so that you can take specific
actions:

+---------------------------------------------+---------------------------------------------------------------------------------------------------------------------+
| Method                                      | Description                                                                                                         |
+=============================================+=====================================================================================================================+
| **add_data_received_callback(callback)**    | Adds a new callback to the list of callbacks that will be notified when data is received from the connected device. |
+---------------------------------------------+---------------------------------------------------------------------------------------------------------------------+
| **remove_data_received_callback(callback)** | Removes the given callback from the ``data_received`` callbacks list.                                               |
+---------------------------------------------+---------------------------------------------------------------------------------------------------------------------+

**Data received callback**

.. code:: python

  [...]

  from digi.ccble.service import ConnectCoreBLEService

  [...]

  service = ...

  [...]

  # Receive data callback.
  def _data_received_callback(data):
    """
    Callback to be notified when a new connection is established.
    """
    print("Data received: %s" % data.decode(encoding="utf-8"))

  [...]

  # Register data received callback.
  service.add_data_received_callback(_data_received_callback)

  [...]

  # Remove data received callback.
  service.remove_connect_callback(_data_received_callback)


.. _serviceSendData:

Send data to connected device
-----------------------------

It is also possible to send data to the connected device after the connection
is established. To do so, call the ``send_data()`` method with the data to
send:

+---------------------+-----------------------------------------------------------------------------------+
| Method              | Description                                                                       |
+=====================+===================================================================================+
| **send_data(data)** | Sends the given data to the connected device through the available BLE interface. |
+---------------------+-----------------------------------------------------------------------------------+

**Send data**

.. code:: python

  [...]

  from digi.ccble.service import ConnectCoreBLEService
  from digi.ccble.exceptions import ConnectCoreBLEException

  [...]

  DATA = "Hello world!"
  service = ...

  [...]

  # Send data to connected device.
  try:
      service.send_data(bytearray(DATA, encoding="utf-8"))
  except ConnectCoreBLEException as exc:
      print("%s" % str(exc))


The previous method may fail for the following reasons:

* There is error sending the data, throwing a ``ConnectCoreBLEException``.


.. _serviceChangeAdvertising:

Change advertising name
-----------------------

By default, the service uses `CONNECTCORE_XXXX` as the advertising name, where
`XXXX` are the last 4 characters of the Bluetooth interface MAC address. You
can change this name at any time by using the ``set_advertising_name()``
method of the service:

+--------------------------------+------------------------------------------------+
| Method                         | Description                                    |
+================================+================================================+
| **get_advertising_name()**     | Returns the currently advertised service name. |
+--------------------------------+------------------------------------------------+
| **set_advertising_name(name)** | Changes the currently advertised service name. |
+--------------------------------+------------------------------------------------+

**Change advertising name**

.. code:: python

  [...]

  from digi.ccble.service import ConnectCoreBLEService
  from digi.ccble.exceptions import ConnectCoreBLEException

  [...]

  service = ...

  [...]

  # Print current advertising name.
  try:
      print("Current advertising name: %s" % service.get_advertising_name())
  except ConnectCoreBLEException as exc:
      print("%s" % str(exc))

  [...]

  # Change the advertising name.
  try:
      service.set_advertising_name("New advertising name")
  except ConnectCoreBLEException as exc:
      print("%s" % str(exc))


The previous method may fail for the following reasons:

* There is error reading the advertising name, throwing a
  ``ConnectCoreBLEException``.
* There is error changing the advertising name, throwing a
  ``ConnectCoreBLEException``.

.. warning::
   If there is a device connected, the name change won't take effect until the
   service is stopped and started again, so it is recommended to change this
   value with the service stopped or without any active connection.


.. _serviceChangePassword:

Change authentication password
------------------------------

The SRP protocol requires the server and the client to use the same password to
authenticate and encrypt the connection data. By default, the service uses
`1234` as the SRP authentication password. You can change this password at any
time by using the ``set_password()`` method of the service:

+----------------------------+-------------------------------------------------------+
| Method                     | Description                                           |
+============================+=======================================================+
| **set_password(password)** | Sets the new authentication password for the service. |
+----------------------------+-------------------------------------------------------+

**Change authentication password**

.. code:: python

  [...]

  from digi.ccble.service import ConnectCoreBLEService
  from digi.ccble.exceptions import ConnectCoreBLEException

  [...]

  service = ...

  [...]

  # Change the authentication password.
  try:
      service.set_password("New password")
  except ConnectCoreBLEException as exc:
      print("%s" % str(exc))


The previous method may fail for the following reasons:

* There is error changing the authentication password, throwing a
  ``ConnectCoreBLEException``.

.. warning::
   If the password is changed with an active device connection, the
   communication with the device will start failing until it reconnects. It is
   recommended to change this value with the service stopped or without any
   device connected.
