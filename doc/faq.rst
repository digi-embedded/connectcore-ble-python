Frequently Asked Questions (FAQs)
=================================

The FAQ section contains answers to general questions related to the
ConnectCore Bluetooth Low Energy library.


Do I need a BLE XBee 3 module to use the library?
------------------------------------------------

No, the library is able to use ConnectCore Bluetooth native interface to
emulate the XBee 3 GATT server and communicate with connected devices. Only
in the case that the ConnectCore does not have a native BLE interface, the
library will need a BLE XBee 3 module attached to the ConnectCore to
communicate with connected devices.


Can I use the ConnectCore Bluetooth Low Energy library in a computer?
---------------------------------------------------------------------

The library is intended to be used in ConnectCore devices, but it should be
possible also to run it on a personal computer using a Bluetooth dongle or
attaching an XBee 3 device.
