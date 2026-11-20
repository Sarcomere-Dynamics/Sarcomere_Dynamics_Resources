# General Example for ARTUS API

![Sarcomere Dynamics Inc. Logo](/docs/assets/images/common/logo.svg)

The general example is a command-line introduction to **`ArtusAPI`** for ARTUS robot hands: connect / disconnect, wake and sleep, calibration, joint targets, and feedback. The legacy `ArtusAPI` class in `artus_api.py` is not used in this repository anymore.

## Requirements

Make sure you have read through and installed the requirements for the ARTUS API. Refer back to the [Repository Readme](../../README.md).

## Finding the USB Device

- On Windows, find the port name by navigating to "Device Manager">"Ports". It should show up as a COM port. (e.g. COM3)
- On Linux, use the command `dmesg | grep ttyUSB` to find the usb device. (e.g. /dev/ttyUSB1)
  - If a permission error is encountered, use the command `sudo chmod 777 /dev/ttyUSB1`

## Configuration

Before running the example, ensure that the [configuratino file](../config/robot_config.yaml) is set to the correct settings. Pay close attention to the following:

- There are 2 robots listed in the yaml file. For this example, only a single robot should have the `robot_connected: true` field set to true. The other should be false.
- The `communication_channel_identifier` field will most likely need to be updated.

## Using the example with different robots

This example is design to work with all of the ARTUS hands/end effectors. Please refer to the robots respective documents for startup procedure requirements.

- [ARTUS Lite](../../ArtusAPI/robot/artus_lite/ARTUS_LITE.md)
- [ARTUS Talos](../../ArtusAPI/robot/artus_talos/ARTUS_TALOS.md)
- [ARTUS Scorpion](../../ArtusAPI/robot/artus_scorpion/ARTUS_SCORPION.md)

### Reading errors and diagnostics

Options 17-20 read the master's status registers (700-812). They need master firmware from November 2026 or later; older firmware returns meaningless values here.

- **17 Fault report**: when the hand reports `ACTUATOR_ERROR`, says why (`reason`, e.g. `STROKE_CAL_FAILED`, `COMM_LOST`, `ESTOP`), which state it was in, which motor was blamed and that motor's calibration result and error word. Works even when every joint error word is 0.
- **18 Last command result**: whether the last command was `ACCEPTED`, `REJECTED_STATE` (not valid in the current state, or not handled by this firmware) or `REJECTED_ERROR` (hand in ERROR: send `c` to clear errors first).
- **19 / 20 Motor diagnostics**: per motor board (23 on the ARTUS Dex), its own error word decoded into flag names, axis state, last calibration result and the master's flags (`LL_FAILED`, `STROKE_FAILED`, `COMM_LOST`, `NO_RESPONSE`). 19 lists only motors with a problem, 20 lists all. Not available for ARTUS Lite / Lite+.

Code meanings are in `artusapi/common/protocol_codes.py`.

### Emergency stop

`e` sends ESTOP: every motor stops and the hand goes to `ACTUATOR_ERROR` with fault reason `ESTOP` (rejected in SLEEP, where the motors are already off). To recover, send `c` to clear errors, then `3` to wake the hand up again.

### Setting targets

The example uses two main json files to set the targets for the robot. They are located in the `data/hand_poses` folder. These files are set up for the **ARTUS Lite** hand, with all 16 joints.
For other grippers, such as the **ARTUS Talos**, there are varying amounts of active degrees of freedom.

To utilize the files for the different hands, please set the targets in the json file to match the joint names of the robot.

e.g. for the **ARTUS Talos**, the joint names are available in the [ARTUS Talos Joint Map](../../ArtusAPI/robot/artus_talos/data/images/talos_hand_joint_map.png). Setting the targets in the json file with keys that match the joint names will ensure that the correct targets are set for the robot. The other joints are parsed out, and will not be sent to the robot.

For the **ARTUS Scorpion**, there is only a single active degree of freedom, and the gripper uses the `thumb_spread` joint key from the available json files.
