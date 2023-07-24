ConnectCore Bluetooth Low Energy Python Library
===============================================

Release v\ |version|. (:ref:`Installation <gsgInstall>`)

.. image:: https://pepy.tech/badge/digi-connectcore-ble
    :target: https://pepy.tech/project/digi-connectcore-ble
.. image:: https://badge.fury.io/py/digi-connectcore-ble.svg
    :target: https://pypi.org/project/digi-connectcore-ble/
.. image:: https://img.shields.io/pypi/pyversions/digi-connectcore-ble.svg
    :alt: PyPI - Python Version
    :target: https://pypi.org/project/digi-connectcore-ble/


The ConnectCore Bluetooth Low Energy Python library (from now ConnectCore BLE
Python library) allows your Digi International's `ConnectCore <https://www.digi.com/products/browse/connectcore>`_
modules to interact with mobile applications using the `Digi IoT Mobile SDK
<https://www.digi.com/resources/documentation/digidocs/90002568>`_
through Bluetooth Low Energy.

The library makes use of the native Bluetooth support of the ConnectCore
devices to create a GATT server that emulates the one existing in XBee 3
devices. This GATT server exposes an RX and TX characteristic to send and
receive data from the connected devices. This is specially useful when
developing mobile applications using the 'Digi IoT Mobile SDK'. If native
Bluetooth support is not available in the ConnectCore device, the library
can search for a compatible XBee 3 module attached to the ConnectCore device
and use its Bluetooth Low Energy support as the communication interface.

The ConnectCore BLE Python library includes the following features:

* Support to communicate ConnectCore devices and mobile phone applications
  using Bluetooth Low Energy and the 'Digi IoT Mobile SDK'.
* Allow external devices to connect to the ConnectCore module using the native
  Bluetooth Low Energy support.
* Allow external devices to connect to the ConnectCore module using an XBee 3
  device attached to the ConnectCore module.
* Support for SRP authentication to encrypt/decrypt Bluetooth Low Energy
  messages between the ConnectCore module and the connected device.

This portal provides the following documentation to help you with the different
development stages of your Python applications using the ConnectCore BLE Python
library.


Requirements
============

The ConnectCore BLE Python library requires **Python 3.8** or greater to work.
You can get it from https://www.python.org/getit/

When installing the library using pip, all requirements will be automatically
installed:

``pip install digi-connectcore-ble``

If you prefer to install them manually, these are the required modules:

* **PySerial 3**. Install it with pip (``pip install pyserial``)
* **XBee Python**. Install it with pip (``pip install xbee-python``).
* **D-Bus Python**. Install it with pip (``pip install dbus-python``).
* **Pycairo**. Install it with pip (``pip install pycairo``).
* **PyGobject**. Install it with pip (``pip install PyGObject``).
* **Bluezero**. Install it with pip (``pip install bluezero``).
* **Six**  Install it with pip (``pip install six``).
* **PyCryptodome**  Install it with pip (``pip install pycryptodome``).
* **SRP**  Install it with pip (``pip install srp``).


Contents
========

The ConnectCore BLE Python library documentation is split in different
sections:

* :ref:`indexGSG`
* :ref:`indexUserDoc`
* :ref:`indexExamples`
* :ref:`indexFAQ`
* :ref:`indexReleaseNotes`
* :ref:`indexAPI`


.. _indexGSG:

Getting Started
---------------

Perform your first steps with the ConnectCore BLE Python library. Learn how to
start the server and communicate with connected devices.

* :doc:`getting_started`


.. _indexUserDoc:

User Documentation
------------------

Access detailed information about the different features and capabilities
provided by the library and how to use them.

* :doc:`user_guide`


.. _indexExamples:

Examples
--------

The library includes examples that demonstrate most of the functionality that
it provides.

* :doc:`examples`


.. _indexFAQ:

FAQ
---

Find the answer to the most common questions or problems related to the
ConnectCore BLE Python library in the FAQ section.

* :doc:`faq`


.. _indexReleaseNotes:

Release notes
-------------

* :ref:`Latest release notes <../release_notes.txt>`


.. _indexAPI:

API reference
-------------

The API reference contains more detailed documentation about the API for
developers who are interested in using and extending the library functionality.

* :doc:`api/modules`


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Getting Started

   getting_started


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: User Documentation

   user_guide


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Examples

   examples


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: FAQs

   faq


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Changelog

   changelog


.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: API reference

   api/modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


License
=======

Copyright 2022, 2023, Digi International Inc.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, you can obtain one at http://mozilla.org/MPL/2.0/.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

Digi International Inc. 11001 Bren Road East, Minnetonka, MN 55343
