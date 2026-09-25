# Startup Procedures

## Cascaded PID Control

Let us review the [previous example](/docs/software/usage/usage.md#example-rs485-style-serial):

```python
from artusapi import ArtusAPI

# Instantiate a right-handed Artus Lite
hand = ArtusAPI(
    communication_method="RS485_RTU",
    communication_channel_identifier="/dev/ttyUSB0",
    robot_type="artus_lite",
    hand_type="right",
    communication_frequency=30,
    baudrate=115200,
)

# control_type=3 for position, 2 for velocity, or 1 for torque
hand.wake_up(control_type=3)
```

As of **artusapi** v2.0.0 and onwards, all ARTUS products implement a cascaded PID control scheme.

> [!CAUTION]
> TODO: Add PID control asset image

By implementing cascaded PID control, operators may have precise, accurate, and reliable control over the motion behaviour of their robot hands.

| Control Mode | Description                                                                                                           |
| :----------: | --------------------------------------------------------------------------------------------------------------------- |
|  Torque (1)  | Moves the actuators with a **specified torque**                                                                       |
| Velocity (2) | Moves the actuators with a **constant velocity** and a **maximum torque setpoint**                                    |
| Position (3) | Moves the actuators to the **target position** at the **target velocity setpoint** with a **maximum torque setpoint** |

## Calibration

The `calibrate()` method runs the calibration sequence corresponding to each ARTUS product.

This typically consists of the following steps:

- Verify and prepare the initial electrical state of the actuators
- Find the minimum and maximum mechanical position bounds for each hand joint
- Report any anomalies in actuator health

> [!IMPORTANT]
> ARTUS Talos and ARTUS Scorpion robots **must** be calibrated before performing any further operations.
>
> While this method is not explicitly required for the ARTUS Lite to function when powered on,
> it is **highly recommended** to perform a calibration on boot regardless.

## Disconnect/Connect

As mentioned previously, the `connect()` method is automatically invoked when an **ArtusAPI** instance is constructed.

Thus, `connect()` must only be explicitly called **after** the `disconnect()` method has been invoked.

## Resets



## Next steps: Preparing for motion

[The following document describes the next steps to move an ARTUS product.](/docs/software/usage/motion.md)
