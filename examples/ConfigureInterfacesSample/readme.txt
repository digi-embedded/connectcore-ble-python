  Introduction
  ------------
  This sample Python application shows how to read and write a set of several
  interface parameters in JSON format using BLE as the communication transport
  in ConnectCore devices.

  The application uses text files to store fake network interfaces parameters
  that can be read and set from a mobile application using the ConnectCore
  Bluetooth Low Energy service.


  Requirements
  ------------
  To run this example you will need:

    * A ConnectCore device with Bluetooth Low Energy support. This support
      can be either native or through a BLE XBee 3 capable device.
    * A mobile phone with the BLENetworkConfigurationSample mobile application
      from the Digi IoT Mobile SDK.


  Example setup
  -------------
    1) Power on the ConnectCore device.

    2) Ensure that Bluetooth is enabled in the device or the XBee 3 BLE device
       is correctly attached.

    3) Ensure that the BLENetworkConfigurationSample application is correctly
       installed in the mobile phone.


  Running the example
  -------------------
  First, copy the application to the ConnectCore device and execute it. The
  output console displays the following message:

    Service started, hit <ENTER> to stop and exit.
    Advertisement registered
    >

  Start the BLENetworkConfigurationSample mobile phone application. When the
  application starts, follow these steps:

    1) Select the device from the list. Enter the password (1234) when asked.

    2) In the device page, click the interface you want to configure, for
       example "Ethernet".

    3) When the "Ethernet" page loads, all the settings are read.

    6) Modify one setting, for example toggle the "Enabled" switch button to
       "On".

    7) Click the "Save" button.

    8) Verify that the "interfaces/Ethernet.txt" demo file of the ConnectCore
       device has been updated and the value of the "Disabled" setting has
       changed to "true".

  To stop the application running in the ConnectCore device, just hit <ENTER>.
