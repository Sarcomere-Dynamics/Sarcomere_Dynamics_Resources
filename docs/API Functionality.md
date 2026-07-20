<img src='../data/images/SarcomereLogoHorizontal.svg'>

> **Note:** The legacy `ArtusAPI` class in `artus_api.py` has been **removed** from this repository. All examples here use **`ArtusAPI_V2`** in [`ArtusAPI/artus_api_new.py`](../ArtusAPI/artus_api_new.py). Import with `from ArtusAPI import ArtusAPI_V2`.

### Creating an `ArtusAPI_V2` object

Below is how to construct the API for a single hand. Common constructor arguments:

* `communication_method` — How the host talks to the hand (for example `RS485_RTU`; must match what [`NewCommunication`](../ArtusAPI/communication/new_communication.py) supports for your checkout).
* `communication_channel_identifier` — Port or device path (for example `COM7` on Windows or `/dev/ttyUSB0` on Linux).
* `robot_type` — Which hand model (for example `artus_lite`, `artus_talos`, `artus_scorpion`).
* `hand_type` — `left` or `right` where applicable.
* `communication_frequency` — Control/feedback loop rate in Hz (default in code is `50`).
* `logger` — Optional Python `logging.Logger`; if `None`, the API creates its own.
* `baudrate` — Serial baud rate (default `115200` in `ArtusAPI_V2`; match your harness and firmware).

The constructor calls `connect()` to open the transport. Then call `wake_up(control_type=...)` with `3` for position, `2` for velocity, or `1` for torque, consistent with your application.

#### Example (RS485-style serial)

```python
from ArtusAPI import ArtusAPI_V2

hand = ArtusAPI_V2(
    communication_method="RS485_RTU",
    communication_channel_identifier="COM7",
    robot_type="artus_lite",
    hand_type="right",
    communication_frequency=50,
    baudrate=115200,
)
hand.wake_up(control_type=3)  # position control
```

## Interacting with the API
To get the most out of the Artus hands, the functions you will call often are `set_joint_angles(joint_angles: dict)` and `get_joint_angles()`. Joint count and key names depend on **`robot_type`** (for example ARTUS Lite uses many joints; Talos or Scorpion differ). See [`data/hand_poses/grasp_example.json`](../data/hand_poses/grasp_example.json) for a sample pose dictionary and the [Artus Lite joint documentation](../ArtusAPI/robot/artus_lite/ARTUS_LITE.md) for mapping on Lite-class hands.

e.g. 
```python
artusapi.set_joint_angles(pinky_dict)
```
### Startup commands
* `connect()` opens the link for the configured communication method (also invoked from the `ArtusAPI_V2` constructor).
* `wake_up(control_type=...)` configures the hand and actuators for the selected control mode; wait until the hand reports ready before commanding motion.
* `calibrate()` runs the calibration sequence when required for your robot model.


### Setting joints
On models with many DOF (for example Artus Lite), joints can be set together or in a subset. If you only need to curl the pinky, a shorter dictionary can be passed to `set_joint_angles`:

```
pinky_dict = {"pinky_flex" : 
                            {
                                "index": 14,
                                "target_angle" : 90
                            },
              "pinky_d2" :
                            {
                                "index":15,
                                "target_angle" : 90
                            }
            }

hand.set_joint_angles(pinky_dict)
```

Notice that the above example does not include the `"target_velocity"` or `"target_force"` field that the json file has. These field are optional and will default to their respective nominal values based on the robot model.

### Input Units
* `target_angle`: the target angle is an integer value, usually in degrees, but see specific robot model for more information on units
* `target_velocity`: the target velocity is an integer value, usually in degrees per second, but see specific robot model for more information on units
* `target_force`: the target force is a float value, usually in Newtons, but see specific robot model for more information on units

### Getting feedback

With **`ArtusAPI_V2`**, request feedback with explicit getters such as `get_joint_angles()`, `get_joint_speeds()`, `get_joint_forces()`, and `get_joint_temperatures()`. The older “streaming vs request” toggle from legacy `ArtusAPI` does not apply the same way; `get_streamed_joint_angles()` is not implemented in V2 and will log an error if called.

After reads complete, updated values are reflected under `hand._robot_handler.robot.hand_joints` (field names depend on the robot model).

### SD Card Interactions

>[!NOTE]
>**Not yet implemented in `ArtusAPI_V2`.** The onboard SD-card grasp workflow below (`save_grasp_onhand`, `execute_grasp`, `get_saved_grasps_onhand`) exists as firmware-level commands but is not yet exposed as public methods on `ArtusAPI_V2`. This section describes the intended behavior once it lands.

Before using the Artus Lite's digital IO functionality to communicate with a robotic arm, there are two steps that need to be done. 
1. Users must set the grasps that they want to call. This is done through the UI or general_example.py, using the `save_grasp_onhand` command. This command will save the last command sent to the hand in the designated position specified (1-6) on the SD card and persist through resets.
2. Users can use the `execute_grasp` command to call the grasps through the API. 
3. Users can print to the terminal all 6 grasps saved to the SD Card using `get_saved_grasps_onhand`

Each of the above will print the target command saved on the SD card to the terminal.

### Changing Communication Methods
As of `v2.1`, all communications channels are active in parallel.

### Controlling multiple hands
The bottleneck for controlling multiple systems is their MODBUS ID which is currently hard-coded by default and specific to the robot model. Same handidness robot hands can be controlled from the same source through separate serial channels. 

### Special Commands

### Other API Methods

Beyond joint control and feedback, `ArtusAPI_V2` exposes:

| Method | Purpose |
|---|---|
| `set_control_type(control_type)` | Switch the hand's active control type (position/velocity/torque) without a full `wake_up()`. |
| `set_home_position()` | Moves the hand to its home position at the default velocity. |
| `get_robot_status()` | Reads and decodes the hand's current actuator and trajectory state. |
| `get_fingertip_forces()` | Reads fingertip force feedback (on hands with force sensors). |
| `get_avg_temperature()` | Reads the hand's average temperature feedback. |
| `get_error_report()` | Reads the per-joint actuator error bitfield report. |
| `clear_errors()` | Explicitly clears latched actuator errors. |
| `get_config(wifi_name, wifi_pass)` | Writes new WiFi credentials to the hand and reads back its assigned IP. |
| `update_firmware(file_location=None, drivers_to_flash=None)` | Flashes new firmware to one or all actuator drivers on the hand. See [`docs/COMPATIBILITY.md`](COMPATIBILITY.md) before updating. |
