<img src='../../../data/images/SarcomereLogoHorizontal.svg'>

# Artus Scorpion - Parallel Gripper

see [data>Getting Started](data/Scorpion%20Getting%20started.png) for __Wiring__.


A backdriveable single motor parallel gripper. 

## Power Requirements

The Artus Scorpion requires a 24V DC power supply, idle/nominal 2.4W, maximum 72W.

## Communication Methods

Shipped with RS485 communication. USBC to come.

## MODBUS RTU
The system utilizes MODBUS RTU communication protocol. 

## Startup Procedure
On Startup, the user must always run a `wake_up` command.
The robot needs to then run a `calibration` command before sending target commands. 

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


* See the [ModbusMap PDF](data/ModbusMap_Scorpion.pdf) if you are developing your own communication application.

<div align=center>
<img src='data/images/talos_hand_joint_map.png' width=800>
</div>