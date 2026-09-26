# ARTUS GUI Controller

![Sarcomere Dynamics Inc. Logo](/docs/assets/images/logo.svg)

This guide provides instructions on how to use the GUI to control the ARTUS robots.

## Requirements

- Python >=3.10 virtual environment (see [these steps on creating and using a virtual environment](https://www.freecodecamp.org/news/how-to-setup-virtual-environments-in-python/))
- Update the PYTHON_PATH in gui.sh (ubuntu) or gui.bat (windows)
- Update the [configuration file](../config/robot_config.yaml) with your physical robot.

> [!NOTE]
> There must only be a _single_ robot connected (robot_connected: true) in the `robot_config.yaml` file.

## Usage

On launch, the GUI will be shown first. After 5 seconds, the backend control will startup. **Please do not start sending data or interacting with the GUI until the second terminal has popped up.**
Another indication that the system is ready, is seeing the feedback data start to be shown on the right-hand side.

### Features

- **Set Joint Angles**: Using the sliders or the input box to set the input target angle.
- **Send Joint Angles**: Send one-shot inputs to the robot using the send button.
- **Stream**: Stream joint angles to the robot without the need to press the send button.
- **Feedback Graphs**: Feedback graphs can be switched between Position, Velocity, and Force. Feeedback is specific to the ARTUS robot model and may not be the same across all models. If the robot is equipped with fingertip force sensors, the data will also be shown on in their own graphs.
