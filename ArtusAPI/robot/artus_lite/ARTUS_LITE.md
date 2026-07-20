<img src='../../../data/images/SarcomereLogoHorizontal.svg'>

# Artus Lite

Everything needed to wire, power, and command the ARTUS Lite (and Lite+) hand. For general API usage (installing the library, `set_joint_angles`, feedback), see the [main repository README](/README.md) and [API Functionality](/docs/API%20Functionality.md) — this file covers what's specific to this hand model.

## Reference Documents
* [Quick Start PDF (Wiring Diagram)](data/Artus%20Lite.pdf)
* [Technical Specification Sheet](data/Artus%20Lite%20Technical%20Specification%20Sheet.pdf)

## Table of Contents
* [Safety](#safety)
* [Power Requirement](#power-requirement)
* [Communication Methods](#communication-methods)
* [Startup Procedure](#startup-procedure)
* [Shutdown Procedure](#shutdown-procedure)
* [Hand Joint Map](#hand-joint-map)
* [Joint Limits](#joint-limits)
* [Default Speed and Force Values](#default-speed-and-force-values)
* [LED States](#led-states)

## Safety
>[!IMPORTANT]
>The hand contains pinch points at every joint. Keep fingers, hair, and loose clothing clear while powered, and never reach into the hand while it is executing a motion command. Disconnect power immediately if a joint behaves unexpectedly.

## Power Requirement

The Artus Lite should be connected to a 24 VDC power supply, requiring a maximum instantaneous draw of 200W, minimum 48W and typical 100W.

## Communication Methods

Hands have the following communication channels available in parallel (from v10.0.0):
* USBC
* RS485
* WiFi TCP

## Startup Procedure
On Startup, the user must always run a `wake_up` command.

Afterwards, if all joints are at their starting position, then the system does not need to run a `calibration` before sending target commands.

## Shutdown Procedure
See [2.2 Normal Shutdown Procedure](/README.md#22-normal-shutdown-procedure) in the main repository README — the sequence is the same across all ARTUS hands.

## Hand Joint Map
Below is a joint index guide mapped to a normal human hand, with the naming convention and joint indices used for control purposes.

<div align=center>
<img src='data/images/hand_joint_map.png' width=800>
</div>

## Joint Limits

* D2, D1 and Flex joints have a range of [0,90]
* Spread joints are normally [-17,17] with the thumb being the exception [-40,40]
* For spreading, the positive spread value will be towards the right hand thumb, negative spread value is towards the pinky

## Default Speed and Force Values

| Parameter | Default | Range | Units |
|---|---|---|---|
| Velocity | 150 | 0 – 300 | degrees/second |
| Force | 10 | 0 – 20 | Newtons (N) |

These apply to both **ARTUS Lite** and **ARTUS Lite+** — Lite+ inherits them unchanged from the base Lite model.

They live as attributes on the robot model, not as hardcoded constants in the API:
```python
hand._robot_handler.robot.default_velocity  # 150
hand._robot_handler.robot.default_force     # 10
```

>[!IMPORTANT]
>`set_joint_angles()` does **not** auto-fill `target_velocity`/`target_force` when a joint's dictionary omits them — it only sends what you give it. If you want the nominal speed/force applied, read the two attributes above and merge them into your pose dict yourself before calling `set_joint_angles()`, the way [`general_example.py`](/examples/general_example/general_example.py) does. The one exception is `set_home_position()`, which applies `default_velocity` automatically when returning the hand to its home pose (it does not set `target_force`).

## LED States
Here is a detailed table of the LED states during normal operation and a description of the states.

| LED Colour | Description |
| --- | --- |
| Blue | Power on |
| Green | Idle (Ready to connect, ready for commands) |
| Red | Error state |
| Orange/Yellow | Shutdown/Sleep mode, may require power cycle for parameter changes to take effect |
| Purple | Flashing Actuators |
