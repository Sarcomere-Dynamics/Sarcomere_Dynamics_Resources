# ArtusLite ROS2 API

## Overview

The `artuslite_ros_api` is a ROS2 package designed to provide an API for interacting with the ArtusLite hand.

> **Python API change:** This repository’s `ArtusAPI` package now exposes **`ArtusAPI_V2`** from [`artus_api_new.py`](../../ArtusAPI/artus_api_new.py); **`artus_api.py` has been removed.** The node implementation under `artuslite_ros_api/artuslite_ros_api.py` still reflects the older `ArtusAPI` constructor and is **not aligned** with current sources until it is ported to `ArtusAPI_V2`. Use [`examples/general_example/`](../../examples/general_example/) as the reference for supported startup and command patterns.

## Directory Structure

```sh
artuslite_ws/
├── src/
│   └── artuslite_ros_api/
│       ├── config/                    
│       │   └── artus_params.yaml         # Parameter file
│       ├── launch/
│       │   └── artus_launch.py           # Launch file to load parameters
│       ├── resource/
│       ├── test/
│       ├── artuslite_ros_api/            # ROS2 node package
│       │   ├── __init__.py
│       │   └── artuslite_ros_api.py
│       ├── package.xml
│       ├── setup.cfg
│       └── setup.py
└── requirements.txt
```

## Installation

To install the `artuslite_ros_api` package, follow these steps:

1. Clone the repository:
    ```sh
    git clone https://github.com/Sarcomere-Dynamics/Sarcomere_Dynamics_Resources.git
    cd artuslite_ws
    ```

2. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Build the package:
    ```sh
    colcon build
    ```

4. Source the setup script:
    ```sh
    source install/setup.bash
    ```

## Usage

1. Configure the parameters in the `artuslite_ws/src/artuslite_ros_api/config/artuslite_params.yaml` file.
 ```yaml
artuslite_ros_node:
  ros__parameters:
    hand_type: "left"
    communication_method: "UART"
    communication_channel_identifier: "/dev/ttyUSB0"
    communication_frequency: 50
    wake_up: true
    calibrate: false # Set to true to calibrate the hand
    reset: false 
    feedback: false

 ```
2. Launch the `artuslite_ros_api` nodes using the launch file:
    ```sh
    ros2 launch artuslite_ros_api artuslite_launch.py
    ```

3. To control the hand, publish messages to the `/artuslite_joint_command` topic (int array of length 16):
    ```sh
    ros2 topic pub /artuslite_joint_command sensor_msgs/JointState "{name: ['thumb1', 'thumb2', 'thumb3', 'thumb4', 'index1', 'index2', 'index3', 'middle1', 'middle2', 'middle3', 'ring1', 'ring2', 'ring3', 'pinky1', 'pinky2', 'pinky3'], position: [10, 20, 15, 40, 10, 35, 45, 10, 50, 55, 10, 65, 70, 10, 50, 55]}"
    ```


4. To receive feedback from the hand, subscribe to the `/artuslite_joint_feedback` topic:
    ```sh
    ros2 topic echo /artuslite_joint_feedback
    ```
