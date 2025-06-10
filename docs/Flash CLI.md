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

#### Master Driver
A. Between the two M8 connectors, there is a silicone pad. This is a boot button, that puts the master into boot mode. __This button must be pressed when powered on__. This state can be determined by the LED staying blue for longer than the startup time (~3seconds)

[Here](https://sarcomere-my.sharepoint.com/:i:/g/personal/ryan_lee_sarcomeredynamics_com/EaRgIujdOupLmXu5p2fHF-kBT2_uakjZ6yqSocXMBUAnow?e=ZnBW2U) is an image showing a user pressing the button. You should be able to feel the tactile button pressed down. Make sure that the button is _down_ when powering on.

B. The boot mode can also be asserted through the boot toggle switch on the master board. Please remove the 6x base plate Hex bolts. On the connector side, [here is an image of the bolts circled in red](https://sarcomere-my.sharepoint.com/:i:/g/personal/ryan_lee_sarcomeredynamics_com/EaSrkZUUi3dNjmCLcg_06aIBWZ0LvUbPqenTTg6ea9031Q?e=qCtPo2). Remove the bolts at the same position on the opposite side. 

C. [Here is a video of the flashing procedure example on a linux machine](https://sarcomere-my.sharepoint.com/:v:/g/personal/ryan_lee_sarcomeredynamics_com/EVqZAh1sDblDv3EXWk0-lPkBFPpJyu2px3ARVWI8UvYrdg?e=eeiInd)

D. Once this is complete, please power cycle the device. If boot mode was activated through the boot switch, please toggle the switch back to the original position to boot it into normal mode. 

### Actuator + Peripheral Driver
To flash the actuator or peripheral drivers, the system can be powered on normally.

A. [Here is a video of the flashing procedure example on a linux machine](https://sarcomere-my.sharepoint.com/:v:/g/personal/ryan_lee_sarcomeredynamics_com/EZc3XdjitGZDmLn4BGAFAjkBmVBTnST78S9en-v-EBZyfw)

>You must power cycle the device between flashing the actuator driver and the peripheral driver
