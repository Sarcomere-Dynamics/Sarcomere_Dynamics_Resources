<img src='../data/images/SarcomereLogoHorizontal.svg'>

# ArtusAPI CLI 
## Introduction
The artusapi CLI is a easy to use command line interface for the following:
* running a calibration (c)
* changing the communication method (p)
* send all flex joint angles to 30 (m)
* send all angles to 0 (h)
* wipe sd card (w)

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
artusapi -p /dev/ttyUSB0 -s left

# example uses default values artus lite right hand for Linux
artusapi -p /dev/ttyUSB0

# default example for Windows
artusapi -p COM3
```

### 1.2 Command Menu
```
====================
Flash CLI Tool Menu:
==================== 
c - calibrate
h - (home) set home position
m - (move) set joint angles
q - quit
r - (reset) reset joint
p - (param) update communication method
w - wipe sd
Enter command: 
```
Above is a snippet of the CLI tool menu. Here is a little more information on the command options.

* c : fully calibrate the hand
* h : set home position (zero position). If already open, nothing will happen.
* m : set all flex angles to 30 deg. If angles set already to 30 deg, nothing will happen.
* q : quit cli. Send a sleep command which saves the positions to SD Card. LED will flash yellow. 
* r : reset a joint. Requires a joint index (from the joint map) and a motor number. __Please reach out to the team before using this command__.
* p : update commmunication parameter. The options are wifi, rs485, can, usbc. __Make sure that you have a system set up to communicate over the selected communication method because this will change the hardcoded option saved on the SD card. 
* w : wipe sd. This will reset the SDCard to empty, resetting parameters to defaults. The hand will need to be fully calibrated after this. 