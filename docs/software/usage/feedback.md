# Retrieving feedback

Within **`ArtusAPI`**, every getter is a thin wrapper around the `get_feedback_data(start_reg)` method.

It is the single entry point for retrieving all feedback fields, which accepts either a `ModbusMap` key name or its corresponding Modbus register address.

For example:

```python
# Instantiate an ARTUS product
hand = ArtusAPI(...)

# This line...
hand.get_joint_forces()

# Is functionally equivalent to...
hand.get_feedback_data("feedback_force_start_reg")

# Is functionally equivalent to...
hand.get_feedback_data(2)
```

The return shape depends on the field: whole-hand scalars (`feedback_voltage_start_reg`, `feedback_avg_temperature_start_reg`, `slave_id_reg`) return a single value.
`feedback_force_sensor_start_reg` returns a dict keyed by finger name with `x`/`y`/`z` values, and every other field returns a dict keyed by joint name.

An unrecognized key or address raises `ValueError`.

When any getter is called, the updated values are reflected under `<ArtusAPI object>._robot_handler.robot.hand_joints`; fingertip sensor readings under `<ArtusAPI object>.__robot__handler.robot.force_sensors`.
These values are identifiable by their corresponding joint labels, which may differ between products.

## Configuration Feedback

| Method                  | Description |
| ----------------------- | ----------- |
| `get_robot_wake_up()`   | Returns     |
| `get_robot_calibrate()` | Returns     |

## Global hand Feedback

| Method                  | Description                                               |               Units               |
| ----------------------- | --------------------------------------------------------- | :-------------------------------: |
| `get_robot_status()`    | Returns the hand's actuator and trajectory state          | Unitless. Refers to an enum type. |
| `get_voltage`           | Returns float representing bus supply voltage             |             **Volts**             |
| `get_avg_temperature()` | Returns float representing the hand's average temperature |            **Celsius**            |

## Per-joint Feedback

| Method                     | Description                                                                                                 |                                  Units                                  |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------: |
| `get_joint_angles()`       | Returns dictionary mapping joint name to angular position at each joint                                     |        **degrees** (Lite) OR **radians** (Talos, Scorpion, Dex)         |
| `get_joint_speeds()`       | Returns dictionary mapping joint name to angular velocity at each joint                                     | **degrees per second** OR **radians per second** (Talos, Scorpion, Dex) |
| `get_joint_forces()`       | Returns dictionary mapping joint name to angular force at each joint                                        |                               **Newtons**                               |
| `get_joint_temperatures()` | Returns dictionary mapping joint name to temperature at each joint                                          |                               **Celsius**                               |
| `get_fingertip_forces()`   | Returns dictionary mapping joint name to dictionary of force values retrieved from dedicated force sensors. |                               **Newtons**                               |
| `get_error_report()`       | Returns the hand's actuator and trajectory state                                                            |                                    -                                    |

## Next Steps: Miscellaneous Methods

[The following document describes all other methods of interacting with an ARTUS product.](/docs/software/usage/misc.md)
