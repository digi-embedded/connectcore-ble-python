Changelog
=========

v1.0.4 - 05/08/2023
-------------------

Initial release of ConnectCore Bluetooth Low Energy Python library. The main
features of the library include:

* Support to communicate ConnectCore devices and mobile phone applications
  using Bluetooth Low Energy and the 'Digi XBee Mobile SDK'.
* Allow external devices to connect to the ConnectCore module using the native
  Bluetooth Low Energy support.
* Allow external devices to connect to the ConnectCore module using an XBee 3
  device attached to the ConnectCore module.
* Support for SRP authentication to encrypt/decrypt Bluetooth Low Energy
  messages between the ConnectCore module and the connected device.

The API calls allow to:

* Start/stop Bluetooth Low Energy service.
* Update Bluetooth Low Energy service SRP authentication password.
* Update Bluetooth Low Energy service advertising name.
* Register for device connect events.
* Register for device disconnect events.
* Register for data received events.
* Send data to connected device.