  Introduction
  ------------
  This sample Python application shows how to wait for incoming messages from
  the connected BLE device and answer back with the same message.


  Requirements
  ------------
  To run this example you will need:

    * A ConnectCore device with Bluetooth Low Energy support. This support
      can be either native or through an BLE XBee 3 capable device.
    * A mobile phone with the RelayConsoleSample mobile application from the
      `Digi XBee Mobile SDK`.


  Example setup
  -------------
    1) Power on the ConnectCore device.

    2) Ensure that Bluetooth is enabled in the device or the XBee 3 BLE device
       is correctly attached.

    3) Ensure that the RelayConsoleSample application is correctly installed
       in the mobile phone.


  Running the example
  -------------------
  First, copy the application to the ConnectCore device and execute it. The
  output console displays the following message:

    Service started, hit <ENTER> to stop and exit.
    Advertisement registered
    >

  At this point, the application has started the service and the advertising
  process. It is now waiting for incoming connections.

  Start the 'XBee Realy Console Sample' mobile phone application and follow
  these steps:

    1) Select the device from the list. Enter the password (1234) when asked.

    2) In the Relay Frames console, click "SEND USER DATA RELAY" button.

    3) Set the 'Destination interface' to 'BLUETOOTH' in the new window.

    6) Set 'Hello World' as the data to be sent and click 'SEND' button.

    7) The data should be received by the service and sent back to the mobile
       application. Verify that a new entry appears in the 'Received User Data
       Relay messages' list with this content:

       [Bluetooth Low Energy] Hello World
