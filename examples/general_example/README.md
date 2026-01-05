<img src='data/images/SarcomereLogoHorizontal.svg'>

# General Example for Artus API

The general example is a command-line tool introduction to the Artus API to control the Artus robot hands, including start-up sequence commands and the ability to retrieve feedback states.

## Requirements
Make sure you have read through and installed the requirements for the Artus API. Refer back to the [Repository Readme](../../README.md).

## Finding the USB Device
* On Windows, find the port name by navigating to "Device Manager">"Ports". It should show up as a COM port. (e.g. COM3)
* On Linux, use the command `dmesg | grep ttyUSB` to find the usb device. (e.g. /dev/ttyUSB1)
    * If a permission error is encountered, use the command `sudo chmod 777 /dev/ttyUSB1` 

## Configuration
Before running the example, ensure that the [configuratino file](../config/robot_config.yaml) is set to the correct settings. Pay close attention to the following:
* There are 2 robots listed in the yaml file. For this example, only a single robot should have the `robot_connected: true` field set to true. The other should be false. 
* The `communication_channel_identifier` field will most likely need to be updated. 