<img src='../../../data/images/SarcomereLogoHorizontal.svg'>

# Artus Scorpion - Parallel Gripper

A backdriveable single motor parallel gripper. Everything needed to wire, power, and command it is below. For general API usage (installing the library, `set_joint_angles`, feedback), see the [main repository README](/README.md) and [API Functionality](/docs/API%20Functionality.md) — this file covers what's specific to this hand model.

## Reference Documents
* [Getting Started (Wiring)](data/Scorpion%20Getting%20started.png)
* [ModbusMap PDF](data/ModbusMap_Scorpion.pdf) — if you are developing your own communication application.

## Table of Contents
* [Safety](#safety)
* [Power Requirements](#power-requirements)
* [Communication Methods](#communication-methods)
* [Startup Procedure](#startup-procedure)
* [Shutdown Procedure](#shutdown-procedure)
* [Control Units](#control-units)
* [Default Speed and Force Values](#default-speed-and-force-values)
* [LED States](#led-states)

## Safety
>[!IMPORTANT]
>The gripper is backdriveable but still capable of pinch injury while powered and closing. Keep fingers clear of the jaws while powered, and never reach into the gripper while it is executing a motion command. Disconnect power immediately if it behaves unexpectedly.

## Power Requirements

The Artus Scorpion requires a 24V DC power supply, idle/nominal 2.4W, maximum 72W.

## Communication Methods

Hands are shipped with USBC and RS485 capabilities.

The system utilizes the MODBUS RTU communication protocol. See the [ModbusMap PDF](data/ModbusMap_Scorpion.pdf) for register-level detail if you are developing your own communication application.

## Startup Procedure
On Startup, the user must always run a `wake_up` command.

>[!IMPORTANT]
>Unlike ARTUS Lite, Scorpion **requires** a `calibrate()` call after `wake_up()` before it will accept target commands.

## Shutdown Procedure
See [2.2 Normal Shutdown Procedure](/README.md#22-normal-shutdown-procedure) in the main repository README — the sequence is the same across all ARTUS hands.

## Control Units
Scorpion has a single gripper joint (no left/right, no hand joint map) with these units:
* Position : mm
* Velocity : mm/s
* Force : Newtons (N)

The starting position is 100mm wide (fully open, position 0). Since it is a single-drive gripper, driving 50mm closes it fully (subject to change).

## Default Speed and Force Values

| Parameter | Default | Range | Units |
|---|---|---|---|
| Velocity | 50 | 0 – 70 | mm/second |
| Force | 20 | 0 – 100 | Newtons (N) |

They live as attributes on the robot model, not as hardcoded constants in the API:
```python
hand._robot_handler.robot.default_velocity  # 50
hand._robot_handler.robot.default_force     # 20
```

>[!IMPORTANT]
>`set_joint_angles()` does **not** auto-fill `target_velocity`/`target_force` when the joint dictionary omits them — it only sends what you give it. If you want the nominal speed/force applied, read the two attributes above and merge them into your pose dict yourself before calling `set_joint_angles()`, the way [`general_example.py`](/examples/general_example/general_example.py) does. The one exception is `set_home_position()`, which applies `default_velocity` automatically when returning the gripper to its home pose (it does not set `target_force`).

## LED States
Here is a detailed table of the LED states during normal operation and a description of the states.

| LED Colour | Description |
| --- | --- |
| Blue | Power on (Ready for Startup Sequence) |
| Green | Idle |
| Flashing Green | Active mode |
| Red/LED OFF | Error state |
| Orange/Yellow | Shutdown/Sleep mode, may require power cycle for parameter changes to take effect |
| Yellow | Flashing Actuators |
