# Miscellaneous Methods

Beyond joint control and retrieving feedback, `ArtusAPI` exposes the following methods.

| Method                                                       | Purpose                                                                                                                           |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `get_robot_status()`                                         | Reads and decodes the highest priority actuator and trajectory state across the hand.                                             |
| `get_error_report()`                                         | Reads the per-joint actuator error bitfield report.                                                                               |
| `clear_errors()`                                             | Explicitly clears any latched actuator errors.                                                                                    | s   |
| `set_control_type(control_type)`                             | Switch the hand's active control type (position/velocity/torque) without performing a full `wake_up()`.                           |
| `get_wifi_config(wifi_name, wifi_pass)`                      | Writes new WiFi credentials to the hand and reads back its assigned IP.                                                           |
| `update_firmware(file_location=None, drivers_to_flash=None)` | Flashes new firmware to one or all actuator drivers on the hand. See [`docs/COMPATIBILITY.md`](COMPATIBILITY.md) before updating. |

## SD Card Interactions

> [!NOTE]
> **Not yet implemented in artusapi.**
> The onboard SD-card grasp workflow below (`save_grasp_onhand`, `execute_grasp`, `get_saved_grasps_onhand`) exists as firmware-level commands but is not yet exposed as public methods on `ArtusAPI`.
> This section describes the intended behavior once it lands.

Before using the Artus Lite's digital IO functionality to communicate with a robotic arm, there are two steps that need to be done.

1. Users must set the grasps that they want to call. This is done through the UI or general_example.py, using the `save_grasp_onhand` command. This command will save the last command sent to the hand in the designated position specified (1-6) on the SD card and persist through resets.
2. Users can use the `execute_grasp` command to call the grasps through the API.
3. Users can print to the terminal all 6 grasps saved to the SD Card using `get_saved_grasps_onhand`

Each of the above will print the target command saved on the SD card to the terminal.
