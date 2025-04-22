# Artus Lite Manus Gloves Control

This guide provides instructions on how to use the GUI to control the Artus Lite hand robot.

## Table of Contents

- [Artus Lite Manus Gloves Control](#artus-lite-manus-gloves-control)
  - [Table of Contents](#table-of-contents)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Control](#running-the-control)

## Requirements

- Python >= 3.10
- Requirements: Manus Glove SDK 
- Artus Lite hand robot
- Windows OS
- Visual Studio

## Installation


1. Download the **MANUS Core - SDK (2.3.0.1)** and the **MANUS Core - Version Locked Installer (2.3.0)** from the [Manus website](https://my.manus-meta.com/resources/downloads/quantum-metagloves)

2. Extract the zip files

3. In the **MANUS_Core_2.3.0.1_SDK** folder, Open the solution file in Visual Studio (P1 Video): `\MANUS_Core_2.3.0.1_SDK\MANUS_Core_2.3.0.1_SDK\ManusSDK_v2.3.0.1\SDKClient\SDKClient.sln`

4. Copy the contents of the **SDKClient.cpp** and **SDKClient.hpp** files with the respective files in this repository (P2 Video)

5. Build Solution in Visual Studio. The output terminal should display the following messages:

```
  
   3>Done building project "SDKClient.vcxproj".

   ========== Build: 2 succeeded, 1 failed, 0 up-to-date, 0 skipped ==========

```

5. An updated exe file should be produced at this location: `\MANUS_Core_2.3.0.1_SDK\MANUS_Core_2.3.0.1_SDK\ManusSDK_v2.3.0.1\SDKClient\Output\x64\Debug\Client\SDKClient.exe`

   You can now close Visual Studio

6. Launch the **MANUS Core - Installer** and follow the set up instructions

7. Launch the **MANUS Core Application** and connect the dongle to the computer

8. Turn on the glove tracker and make sure it is connected to the MANUS Core

9. Clone the Sarcomere Dynamics Resources repository and navigate to the manus_glove_controller.py file (P3 Video): (`\Sarcomere_Dynamics_Resources\examples\Control\ArtusLiteControl\ManusGloveControl\manus_glove_controller.py`)

10. In the manus_glove_controller.py file, change the path in line 36 to the path on your computer for the SDKClient.exe file (P4 Video)

11. Install the required Python packages: (P5 Video)
    ```sh
    pip install pyyaml
    pip install psutil
    ```
   
## Configuration

Before running the GUI, ensure that the configuration file is updated with the correct settings for your Artus Lite hand robot. The configuration file is located at `Sarcomere_Dynamics_Resources/Control/configuration/robot_config.yaml`.

## Running the Control

To start the Manus Glove control for controlling the Artus Lite hand robot, follow these steps:

1. Navigate to the directory containing the python script:
    ```sh
    Sarcomere_Dynamics_Resources/examples/Control/ArtusLiteControl/ManusGloveControl
    ```

2. Run python script:

    ```sh
    python manus_glove_controller.py
    ```


## Troubleshooting

Increase the value of 'TCP_DATA_RATE' (10 - 500) in the **SDKClient.cpp** and build the project again if you laggy behavior during control of Artus Lite hand using Manus Data Gloves
```
#define TCP_DATA_RATE 50
```
