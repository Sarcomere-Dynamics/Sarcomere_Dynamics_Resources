<img src='data/images/SarcomereLogoHorizontal.svg'>

# Google MediaPipe Control

This guide provides instructions on how to use the Google MediaPipe Control to control the Artus robots. 

## Requirements

* Python >=3.10
* Update the [configuration file](../config/robot_config.yaml) with your physical robot.

>[!NOTE]
>There must only be a _single_ robot connected (robot_connected: true) in the `robot_config.yaml` file.

## Usage

On launch, the following will happen:
1. the terminal will require an input from the user to choose the webcam device to use. 
2. the robot will go through the startup sequence
3. the user will be required to do a calibration sequence where the camera will take samples of the users hand to identify finger lengths. 
4. The robot will not move/receive commands from the mediapipe process until it has completed the calibration sequence. 

Ctrl+C will stop the mediapipe process and the robot will go into a sleep state. 