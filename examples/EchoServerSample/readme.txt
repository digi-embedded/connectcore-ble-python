  Introduction
  ------------
  This sample Python application shows how to wait for incoming messages from
  the connected BLE device and answer back with the same message.


  Requirements
  ------------
  To run this example you will need:

    * A ConnectCore device with Bluetooth Low Energy support. This support
      can be either native or through an BLE XBee 3 capable device.
    * A mobile phone with the `Digi XBee Mobile` app installed.


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

  Start the 'Digi XBee Mobile' application and follow these steps:

    1) Select the device from the list. Enter the password (1234) when asked.

    2) In the device page open the options menu located at the top-right corner
       of the application and select the `Relay Console` option.

    3) In the Relay Console, click the `+` button of the `Send frames` section.

    3) Set the 'XBee interface' to 'BLUETOOTH' in the `Add new frame` popup.

    6) Set 'Hello World' as the `Data` to be sent and click 'Add' button.

    7) Now, select the frame that you have just added from the `Send frames`
       list and click `Send selected frame`. 

    8) The data should be received by the service and sent back to the mobile
       application. Verify that a new entry appears in the 'Frames log' list
       with this content:

       Hello World
