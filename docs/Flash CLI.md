<img src='../data/images/SarcomereLogoHorizontal.svg'>

# ArtusAPI Flash CLI Tool Information

## Introduction
The ArtusAPI Flash CLI tool is used for updating firmware of the controllers on the Artus hands that the ArtusAPI supports.

## 1. Usage
### 1.1 Initial Arguments
Below is a list of arguments, required and optional, and their default values.

* port (-p or --port)
    * The COM port that the Artus hand is connected. 
    * no default and required
* robot (-r or --robot)
    * the robot type which includes artus_lite and artus_lite_plus.
    * defaults to artus_lite
* side (-s or --side)
    * the hand sideness between left and right
    * defaults to right

__Examples__:
```bash
# Example uses default value for robot (artus_lite) and specifies a left hand for Linux
artusapiflash -p /dev/ttyUSB0 -s left

# example uses default values artus lite right hand for Linux
artusapiflash -p /dev/ttyUSB0

# default example for Windows
artusapiflash -p COM3
```
### 1.2 Sub-system to flash
There are 3 subsystems to flash. The _master_, the _actuator_ and the _peripheral_ drivers. To flash the master, the artus lite and lite plus must be put into boot mode via the following methods.

1. Between the two M8 connectors, there is a silicone pad. This is a boot button, that puts the master into boot mode. __This button must be pressed when powered on__. This state can be determined by the LED staying blue for longer than the startup time (~3seconds)
 
To flash the actuator or peripheral drivers, the system can be powered on normally.

After starting the process with the `artusapiflash` command, the user must choose the subsystem to flash by typing in the terminal when the options are presented. 