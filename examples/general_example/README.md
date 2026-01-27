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

## Using the example with different robots
This example is design to work with all of the Artus hands/end effectors. Please refer to the robots respective documents for startup procedure requirements.
* [Artus Lite](../../ArtusAPI/robot/artus_lite/ARTUS_LITE.md)
* [Artus Talos](../../ArtusAPI/robot/artus_talos/ARTUS_TALOS.md)
* [Artus Scorpion](../../ArtusAPI/robot/artus_scorpion/ARTUS_SCORPION.md)

### Setting targets 
The example uses two main json files to set the targets for the robot. They are located in the `data/hand_poses` folder. These files are set up for the __Artus Lite__ hand, with all 16 joints.
For other grippers, such as the __Artus Talos__, there are varying amounts of active degrees of freedom.

To utilize the files for the different hands, please set the targets in the json file to match the joint names of the robot. 

e.g. for the __Artus Talos__, the joint names are available in the [Artus Talos Joint Map](../../ArtusAPI/robot/artus_talos/data/images/talos_hand_joint_map.png). Setting the targets in the json file with keys that match the joint names will ensure that the correct targets are set for the robot. The other joints are parsed out, and will not be sent to the robot.

For the __Artus Scorpion__, there is only a single active degree of freedom, and the gripper uses the `thumb_spread` joint key from the available json files. 