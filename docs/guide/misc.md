# Miscellaneous Methods

Beyond joint control and retrieving feedback, **artusapi** exposes the following methods.

## General

| Method                                  | Purpose                                                                                                 |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `get_robot_status()`                    | Reads and decodes the highest priority actuator and trajectory state across the hand.                   |
| `get_error_report()`                    | Reads the per-joint actuator error bitfield report.                                                     |
| `clear_errors()`                        | Explicitly clears any latched actuator errors.                                                          |
| `set_control_type(control_type)`        | Switch the hand's active control type (position/velocity/torque) without performing a full `wake_up()`. |
| `get_wifi_config(wifi_name, wifi_pass)` | Writes new WiFi credentials to the hand and reads back its assigned IP.                                 |

## Resetting Joints

If the hand becomes obstructed, the following methods may be used to force the actuators into an open position.
This makes it easier to perform inspection and maintennance on the device.

Once these methods are uesd, it is recommended to power cycle the device after returning the robot into an operable position.

| Method                | Description                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------- |
| `reset()`             | Pulses the actuators in the open direction.                                              |
| `soft_reset()`        | Opens the actuators towards the open endstop. Then, applies pretensioning if applicable. |
| `set_home_position()` | Moves the hand to its home position at the default velocity.                             |

## Firmware Updates

### Updating Actuators

Actuators may be updated independently from their control boards using the `update_actuator()` method.

`update_actuator()` requires the following arguments:

- `file_location`: A string containing the absolute path to a valid firmware image
- `drivers_to_flash`: An integer value referring to the **actuator index** to flash

### Updating Mainboards

While not explicitly part of the **artusapi**, [`mainboard_updater.py`](/artusapi/firmware_update/mainboard_updater.py) has been included for convenience.

As of **artusapi** V2.0.0, `mainboard_updater.py` is only compatible with ARTUS Lite and ARTUS Lite+ mainboards.
Compatibility with ARTUS Talos, ARTUS Scorpion, ARTUS Dex, and future products is under development.

## SD Card Interactions

> [!NOTE]
> **Not yet implemented in artusapi.**
> The onboard SD-card grasp workflow below (`save_grasp_onhand`, `execute_grasp`, `get_saved_grasps_onhand`) exists as firmware-level commands but is not yet exposed as public methods on `ArtusAPI`.
> This section describes the intended behavior once it lands.

Before using the ARTUS Lite's digital IO functionality to communicate with a robotic arm, there are two steps that need to be done.

1. Users must set the grasps that they want to call. This is done through the UI or general_example.py, using the `save_grasp_onhand` command. This command will save the last command sent to the hand in the designated position specified (1-6) on the SD card and persist through resets.
2. Users can use the `execute_grasp` command to call the grasps through the API.
3. Users can print to the terminal all 6 grasps saved to the SD Card using `get_saved_grasps_onhand`

Each of the above will print the target command saved on the SD card to the terminal.
