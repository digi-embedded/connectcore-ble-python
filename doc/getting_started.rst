Get started with ConnectCore Bluetooth Low Energy Python library
================================================================

This getting started guide describes how to set up your environment and use
the ConnectCore Bluetooth Low Energy library to communicate your Digi
ConnectCore devices with mobile applications. It explains how to install
the software and write your first application.

The guide is split into 2 main sections:

* :ref:`gsgInstall`
* :ref:`gsgRunApp`


.. _gsgInstall:

Install your software
---------------------

The following software components are required to write and run your first
application:

* :ref:`gsgInstallPython3`
* :ref:`gsgInstallBluezero`
* :ref:`gsgInstallXBeePython`
* :ref:`gsgInstallSRP`
* :ref:`gsgInstallLibrarySoftware`


.. _gsgInstallPython3:

Python 3
````````

The ConnectCore Bluetooth Low Energy Python library requires Python 3. If you
don't have Python 3, you can get it from https://www.python.org/getit/.

.. warning::
   The XBee Python library is currently only compatible with Python 3.


.. _gsgInstallBluezero:

Bluezero
````````

When Bluetooth is natively supported in your ConnectCore device, the library
will make use of it through the D-Bus communication interface. For that
functionality, the ConnectCore BLE Python library uses the **Bluezero** module,
which provides an abstraction layer to access and interact with Bluetooth over
this bus.

This module is automatically downloaded when you install the library.


.. _gsgInstallXBeePython:

XBee Python
```````````

If Bluetooth is not natively supported in your ConnectCore device, the library
will try to find a valid BLE capable XBee 3 module attached to your device and
use it as the communication interface. For that functionality, the ConnectCore
BLE Python library uses the **XBee Python** module.

This module is automatically downloaded when you install the library.


.. _gsgInstallSRP:

SRP
```

The ConnectCore BLE Python library uses the **SRP** module to authenticate with
mobile applications over Bluetooth Low Energy.

This module is automatically downloaded when you install the ConnectCore BLE
Python library.


.. _gsgInstallLibrarySoftware:

ConnectCore Bluetooth Low Energy library software
`````````````````````````````````````````````````

The best way to install the ConnectCore Bluetooth Low Energy library is with
the `pip <https://pip.pypa.io/en/stable>`_ tool (which is what Python uses to
install packages). The pip tool comes with recent versions of Python.

To install the library, run this command in your terminal application:

.. code::

  $ pip install digi-connectcore-ble

The library is automatically downloaded and installed in your Python
interpreter.


Get the source code
*******************

The ConnectCore Bluetooth Low Energy python library is actively developed on
GitHub, where the code is `always available <https://github.com/digidotcom/connectcore-ble-python>`_.
You can clone the repository with:

.. code::

  $ git clone git@github.com:digidotcom/connectcore-ble-python.git


.. _gsgRunApp:

Run your first ConnectCore Bluetooth Low Energy application
-----------------------------------------------------------

The ConnectCore BLE Python application demonstrated in the guide waits for
incoming data from the connected device and prints it in the console.

For this guide, you will need a mobile phone with the `RelayConsoleSample`
application from the `Digi XBee Mobile SDK` already installed to test.

Follow these steps to register the data callback and start the service:

#. Open the Python interpreter and write the application commands.

   #. Import the ``ConnectCoreBLEService`` class by executing the following
      command:

      .. code::

        > from digi.ccble.service import ConnectCoreBLEService

   #. Instantiate the ConnectCore BLE service:

      .. code::

        > cc_ble_service = ConnectCoreBLEService.get_instance()

   #. Define the data received callback function:

      .. code::

        > data_callback = lambda data: print("Received data: %s" % data.decode())

   #. Register a data received callback:

      .. code::

        > cc_ble_service.add_data_received_callback(data_callback)

   #. Start the service:

      .. code::

        > cc_ble_service.start()

Follow these steps to test the above code with the `RelayConsoleSample` mobile
application:

#. Open the RelayConsoleSample application.

#. Select the device from the list. Enter the password (1234) when asked.

#. In the Relay Frames console, click "SEND USER DATA RELAY" button.

#. Set the 'Destination interface' to 'BLUETOOTH' in the new window.

#. Set 'Hello World' as the data to be sent and click 'SEND' button.

#. The data should be received by the service and printed int the console:

   Received data: Hello World
