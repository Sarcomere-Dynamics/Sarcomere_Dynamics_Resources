# Artus Lite GUI Control

This guide provides instructions on how to use the GUI to control the Artus Lite hand robot.

## Table of Contents

- [Artus Lite GUI Control](#artus-lite-gui-control)
  - [Table of Contents](#table-of-contents)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the GUI](#running-the-gui)
  - [Usage](#usage)

## Requirements

- Python >= 3.10
- Required Python packages: `pyzmq`, `PyQt5`, `numpy`, `pyqtgraph`, `pyyaml`, `psutil`, `pyserial`, `esptool`, `tqdm`
- Artus Lite hand robot
- Windows OS (for running the GUI executable)

## Installation


1. Create a virutal environment
```
python3 -m venv vevn
```
2. Activate the virtual environment

On Ubuntu:
```
source venv/bin/activate
```

On Windows:
```
venv\Scripts\activate
```
3. Install the required Python packages:
    ```sh
    pip install numpy pyzmq pyqtgraph PyQT5 pyyaml psutil pyserial esptool tqdm
    ```

4. Update the PYTHON_PATH in the gui.bat (windows) or gui.sh (ubuntu) files accordingly using your virtual environment's python path

5. Run gui.bat (windows) or gui.sh (ubuntu)


## Configuration

Before running the GUI, ensure that the configuration file is updated with the correct settings for your Artus Lite hand robot. The configuration file is located at `Sarcomere_Dynamics_Resources/Control/configuration/robot_config.yaml`.

## Running the GUI

To start the GUI for controlling the Artus Lite hand robot, follow these steps:

1. Navigate to the directory containing the `gui.bat` script:
    ```sh
    Sarcomere_Dynamics_Resources/examples/Control/ArtusLiteControl/GUIControlV2
    ```

2. Run the `gui.bat` script:
    ```sh
    gui.bat
    ```


## Usage

Once the GUI is running, you can control the Artus Lite hand robot using the following features:

- **Start Streaming**: Begin streaming joint angles from the GUI in continuous mode.
- **Send Joint Angles**: Send the joint angles to the Artus Lite hand robot once.
