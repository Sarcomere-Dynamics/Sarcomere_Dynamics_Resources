# General Example for Artus API

The general example demonstrates how to use the Artus API to control the Artus Lite hand robot. It provides a simple command-line interface to connect to the robot, send commands, and retrieve robot states.

## Requirements
- Python >= 3.10
- Required Python packages: `pyyaml`
- Artus Lite hand robot
- Make sure you have installed the requirements for Artus API. Refer to the [README](../../README.md) for more information.

## Finding the USB Device
* On Windows, find the port name by navigating to "Device Manager">"Ports". It should show up as a COM port. (e.g. COM3)
* On Linux, use the command `dmesg | grep ttyUSB` to find the usb device. (e.g. /dev/ttyUSB1)
    * If a permission error is encountered, use the command `sudo chmod 777 /dev/ttyUSB1` 


## Installation

1. Install the required Python packages:
    ```sh
    pip install pyyaml
    ```

## Configuration

Before running the example, ensure that the configuration file is updated with the correct settings for your Artus Lite hand robot. The configuration file is located at [`examples/general_example/config/artus_config.yaml`](/examples/general_example/config/artus_config.yaml).

```yaml
robot:
  artusLite:
    hand_type: 'left'
    robot_connected: true
    communication_method: 'UART'               # 'UART' or 'WiFi'
    communication_channel_identifier: 'COM11'  # 'COM*' on windows, '/dev/ttyUSB*' on linux
    start_robot: true
    reset_on_start: 0
    calibrate: false                           # calibrate the robot joints
    awake: false
    streaming_frequency: 20                    # data/seconds
```

## Running the Example

To run the general example, execute the following command:
```sh
python3 path/to/general_example.py
```

The following menu will be shown once the script is run. The proper procedure is to choose `1` to start the connection to the hand. Out of the box, it will also run the `wake_up` function. Once the menu is shown again, it is ready to have a command sent to it. Try sending the command `6`! `grasp_example` does not close the hand fully, but puts it into a pincher type grip.

When shutting down the device, send `4` to sleep the hand and initiate the shut down sequence. 
```
"""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                          Artus API 2.0                           ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║ Command Options:                                                 ║
    ║                                                                  ║
    ║   1 -> Start connection to hand                                  ║
    ║   2 -> Disconnect from hand                                      ║
    ║   3 -> Wakeup hand                                               ║
    ║   4 -> Enter hand sleep mode                                     ║
    ║   5 -> Calibrate                                                 ║
    ║   6 -> Send command from data/hand_poses/grasp_example           ║
    ║   7 -> Get robot states                                          ║
    ║   8 -> Send command from data/hand_poses/grasp_open              ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    >> Input Command Code (1-8): """
```