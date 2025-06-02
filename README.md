<img src='data/images/SarcomereLogoHorizontal.svg'>

# Python ARTUS Robotic Hand API

This repository contains a Python API for controlling the ARTUS robotic hands by Sarcomere Dynamics Inc.

Please contact the team if there are any issues that arise through the use of the API. See [Software License](/Software%20License_24March%202025.pdf).

## Introduction
>[!IMPORTANT]
__Please read through the entire README and the _User Manual_ before using the ARTUS hand__

The user manual contains in-depth operational and troubleshooting guidelines for the device. 

This repository contains the following:
* [ARTUS API](/ArtusAPI/)
* [ROS2 Node](/ros2/)
* [Examples](/examples/)

Below is a list of the ARTUS hand-specific READMEs that are compatible with the API. This includes _electrical wiring specifics_, _joint maps_ and more:
* [ARTUS Lite Information](/ArtusAPI/robot/artus_lite/README.md)

### VERY IMPORTANT
* [Requirements](#requirements)
* [Normal Startup Procedure](#normal-startup-procedure)
* [Normal Shutdown Procedure](#normal-shutdown-procedure)

## Table of Contents
* [Getting Started](#1-getting-started)
  * [1.1 Requirements](#11-requirements)
  * [1.2 Python Requirements](#12-python-requirements)
    * [1.2.1 Use-as-Released](#121-use-as-released)
    * [1.2.2 Use Cloned Repository](#122-use-cloned-repository)
    * [1.3 Hardware Requirements](#13-hardware-requirements) 
* [Basic Usage](#2-basic-usage)
  * [2.1 Normal Startup Procedure](#21-normal-startup-procedure)
  * [2.2 Normal Shutdown Procedure](#22-normal-shutdown-procedure)
  * [2.3 Running _general_example.py_](#23-running-general_examplepy)
  * [2.3.1 Video Introduction](#231-video-introduction)
* [Control Examples](#artus-lite-control-examples-setup)
  * [GUIv2](#1-gui-setup)
  * [ROS2](#2-ros2-node-control-setup)
  * [Manus Glove Teleoperation](#3-manus-glove-setup)

See the [Appendix](#appendix) for additional links and information.

## Wiring Diagram
See below the wiring diagram with the circuit connection names and cable colours. You can use either the 8P nano M8 or the 4P nano M8. We recommend a 200W rated 24V power supply, please review the power requirements here: [ARTUS Lite Information](/ArtusAPI/robot/artus_lite/ARTUS_LITE.md) 

## 1. Getting Started 
__Sections__
* [1.1 Requirements](#11-requirements)
* [1.2 Python Requirements](#12-python-requirements)
  * [1.2.1 Use-as-Released](#121-use-as-released)
  * [1.2.2 Use Cloned Repository](#122-use-cloned-repository)
  * [1.3 Hardware Requirements](#13-hardware-requirements) 

The first step to working with the Artus Lite is to connect to the hand, and achieve joint control and joint feedback. It is highly recommended that this should be done for the first time via the [example program provided](#23-running-general_examplepy). In preparation for this example, please follow the subsequent sections step by step, outlining all requirements for working with both the initial example program, as well as the API as a whole.

### 1.1 Requirements
Below is a list of Requirements for the Artus to be compatible 
1. Python v3.10+ - Requires Python version >= 3.10 installed on the host system. Please visit the [Python website](https://www.python.org/downloads/) to install Python. Within the setup instructions, there will be a prompt that allows you to "disable PATH length limit". Please continue with this option selected.
2. FTDI USB Driver (Windows Only) - Necessary for the Artus Lite to be recognized as a USB device once it is connected over USBC, go to [FTDI Driver Download](https://ftdichip.com/drivers/vcp-drivers/) to install the virtual COM port driver. 

### 1.2 Python Requirements
There are two ways to install the Python API. The first is through Python's package manager, where the API can be imported as a library like any other. The second is through this cloned Github repository, using and importing the local files. 

>[!Note]
>If you have multiple Python installations (different versions) on your PC, ensure that your *pip* commands apply to the installation/version you intend to use to run the Artus API, and is the same one used later in any IDE used to create your own programs. You can ensure this by adding the path to the to-be-used python executable as a prefix to this command. An example of this is below.
>```
>C:\Users\zanem\AppData\Local\Programs\Python\Python311\python.exe -m pip install psutil
>```
>Take a look at [these steps on creating and using a virtual environment](https://www.freecodecamp.org/news/how-to-setup-virtual-environments-in-python/) to ensure that you are using the correct python at all times

#### 1.2.1 Use-as-Released
The ArtusAPI is available via pip [here](https://pypi.org/project/ArtusAPI/) using the following command:
```python
pip install ArtusAPI
```
Once this is complete, the software dependecies are all met!

#### 1.2.2 Use Cloned Repository
If you plan to eventually make changes to the source code, you will need to clone the GitHub *SARCOMERE_DYNAMICS_RESOURCES* repository. Once cloned, you can utilize the *requirements.txt* included in the package to install the dependencies. With a terminal open, execute the following command:
```
pip install -r path\to\requirements.txt
```
Alternatively, if your terminal is open in the cloned repo's folder, you can run the following simpler version of the above command. 
```
pip install -r requirements.txt
```

### 1.3 Hardware Requirements
1. Power and Data Harness connection (options below)
	1. __4P Nano M8 (Power) + USB-C (COM)__. These are the harnesses that should be connected when running the *general_example.py* script below. Out-of-the-box, the hand is set up to use USBC as the communication method. 
	2. 8P Nano M8 (Power + COM). This harness setup is reserved for more advanced use, once you are familiar with the hand. This harness allows for CAN or RS485 communication and power all-in-one.

<div align=center>
  <img src='data/images/wiring_diagram.png'>
</div>

## 2. Basic Usage
This section covers very basic usage of the Artus Lite using the Artus API.

__Sections__
* [2.1 Normal Startup Procedure](#21-normal-startup-procedure)
* [2.2 Normal Shutdown Procedure](#22-normal-shutdown-procedure)
* [2.3 Running _general_example.py_](#23-running-general_examplepy)
* [2.3.1 Video Introduction](#231-video-introduction)

### 2.1 Normal Startup Procedure
There is a standard series of commands that need to be followed before sending target commands or receiving feedback data is possible. 

Before any software, ensure that the power connector is secured and connected to the Artus hand and if using a wired connection (Serial or CANbus), ensure the connection/cable is good. 

First, to create a communication connection between the API and the Artus hand, `ArtusAPI.connect()` must be run to confirm communication is open on the selected communication type.

Second, the `ArtusAPI.wake_up()` function must be run to allow the hand to load it's necessary configurations.

Once these two steps are complete, optionally, you can run `ArtusAPI.calibrate()` to calibrate the finger joints. Otherwise, the system is now ready to start sending and receiving data!

>[!NOTE]
>If running version v1.0.1+, `wake_up` is called inside the `connect()` function_

### 2.2 Normal Shutdown Procedure
When getting ready to power off the device please do the following:
* Send a zero position command to all the joints so that the hand is opened
* Once the hand is in an open position, send the `artus.sleep()` command to save parameters to the SD Card.
* Once the LED turns yellow, then the device can be powered off. 

>[!NOTE]
>This is different than the mk8 where the SD Card would save periodically. Now, saving to SD Card is more intentional.

### 2.3 Running _general_example.py_
See the [General Example README to complete this task](/examples/general_example/README.md)

#### 2.3.1 Video Introduction
[![Getting Started Video](/data/images/thumbnail.png)](https://www.youtube.com/watch?v=30BkuA0EkP4)

## Artus Lite Control Examples Setup

### 1. GUI Setup
Please check the [Artus GUIV2 README](examples/Control/ArtusLiteControl/GUIControlV2/README.md) for a GUI setup to control the Artus Lite hand.

Also, check the video below for a demonstration of the GUI setup.
>[!NOTE]
>Video is for GUIv1, but GUIv1 is depracated. Please use GUIv2

<div align="center">
  <a href="https://www.youtube.com/watch?v=l_Sl6bAeGuc">
  <img src="./data/images/gui.png" alt="Watch the video" width="200" />
  </a>
</div>

### 2. ROS2 Node Control Setup
Please check the [Artus ROS2 Node README](ros2/artuslite_ws/README.md) for a ROS2 node setup to control the Artus Lite hand.

Also, check the video below for a demonstration of the ROS2 node setup.

<div align="center">
  <a href="https://www.youtube.com/watch?v=GHyG1NuuRv4">
  Watch the video
  </a>
</div>

### 3. Manus Glove Setup
Please check the [Manus Glove README](examples/Control/ArtusLiteControl/ManusGloveControl/README.md) for a Manus Glove setup to control the Artus Lite hand.

Also, check the video below for a demonstration of the Manus Glove setup.

<div align="center">
  <a href="https://www.youtube.com/watch?v=SPXJlxMaDVQ&list=PLNUrV_GAAyA8HNBAvwBlsmIqoWiJJLRwW&index=2">
  Watch the video
  </a>
</div>



## Revision Control
| Date  | Revision | Description | Pip Release |
| :---: | :------: | :---------: | :----------: |
| Nov. 14, 2023 | v1.0b | Initial release - Artus Lite Mk 5 | NA |
| Apr. 23, 2024 | v1.1b | Beta release - Artus Lite Mk 6 | NA |
| Oct. 9, 2024 | v1.0 | Artus Lite Release | v1.0 |
| Oct. 23, 2024 | v1.0.2 | awake parameter added, wake up function in connect | v1.0.1 |
| Nov. 14, 2024 | v1.1 | firmware v1.1 release | v1.1 |
| Apr. 22, 2025 | v1.1.1 | readmes/documentation updated | - |
| Jun.  2, 2025 | v1.3.10 | changes publish, see [changelog](/changelog/)  | v1.3.10 |

## Appendix
* [Artus API](ArtusAPI/artus_api.py) - The file containing all functions that interact with the Artus Lite.
* [API Docs](docs/API%20Functionality.md) - Contains a little more information on application and reasoning behind the API functions.
