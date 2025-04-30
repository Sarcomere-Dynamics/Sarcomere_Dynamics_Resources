### Creating an ArtusAPI Class Object
Below are some examples of instantiating the ArtusAPI class to control a single hand. Below is a description of the parameters and what they mean.

* `__communication_method__` : The communication method between the host system and the Artus hand
* `__communication_channel_identifier__` : The identifying parameter of the communication method such as COM port over Serial or network name over WiFi
* `__robot_type__` : The Artus robot hand name 
* `__hand_type__` : left or right hand
* `__stream__` : whether streaming feedback data is required or not. Default: `False`
* `__communication_frequency__` : The frequency of the feedback and command communication. Default: `200` Hz
* `__logger__` : If integrating the API into control code, you may already have a logger. THis will allow for homogeneous logging to the same files as what you currently have. Default: `None`
* `__reset_on_start__` : If the hand is not in a closed state when last powered off, setting to `1` will open the hand before ready to receive commands. This _MUST_ be set if powered off in a closed state, and a calibrate may need to be run before sending accurate target commands
* `__baudrate__` : required to differentiate between Serial over USB-C and Serial over RS485, default `921600`
* `__awake__` : False by default - if the hand is already in a ready state (LED is green) when starting or restarting a control script, set woken to `True` to bypass resending the `wake_up` function, which could lead to lost calibration.

#### Serial Example
```python
from ArtusAPI.artus_api import ArtusAPI
artus_lite = ArtusAPI(robot_type='artus_lite', communication_type='UART',hand_type='right',communication_channel_identifier='COM7',reset_on_start=0)

artus_lite.connect()
```

## Interacting with the API
To get the most out of the Artus hands, the functions that will likely be most interacted with are `set_joint_angles(self, joint_angles:dict)` and `get_joint_angles(self)`. The `set_joint_angles` function allows the user to set 16 independent joint values with a desired velocity/force value in the form of a dictionary. See the [grasp_close file](data/hand_poses/grasp_close.json) for an example of a full 16 joint dictionary for the Artus Lite. See the [Artus Lite README](ArtusAPI/robot/artus_lite/README.md) for joint mapping.

e.g. 
```python
artusapi.set_joint_angles(pinky_dict)
```
### Startup Commands
* `connect` is used to start a connection between the API and the hand via the communication method chosen. It will then send a `wake_up` command if `awake == False`. 
* The `wake_up` command properly configures the hand and the actuators. Once an `ack` is returned, the hand is now ready to be controlled 
* `calibrate` sends a full calibration command sequence for all the fingers. 


### Setting Joints
As mentioned above, there are 16 independent degrees of freedom for the Artus Lite, which can be set simultaneously or independently. If, for example, a user need only curl the pinky, a shorter dictionary like the following could be used as a parameter to the function:

```
pinky_dict = {"pinky_flex" : 
                            {
                                "index": 14,
                                "input_angle" : 90
                            },
              "pinky_d2" :
                            {
                                "index":15,
                                "input_angle" : 90
                            }
            }

ArtusAPI.set_joint_angles(pinky_dict)
```

Notice that the above example does not include the `"input_speed"` field that the json file has. The `"input_speed"` field is optional and will default to the nominal speed.

### Input Units
* Input Angle: the input angle is an integer value in degrees
* velocity: the velocity is in a percentage unit 0-100. Minimum movement requirement is around 30. This value pertains to the gripping force of the movement. 

### Getting Feedback
There are two ways to get feedback data depending on how the class is instantiated.

1. In streaming mode (`stream = True`), after sending the `wake_up()` command, the system will start streaming feedback data which will populate the `ArtusAPI._robot_handler.robot.hand_joints` dictionary. Fields that hold feedback data are named with `feedback_X` where _X_ could be angle, current or temperature.
2. In Request mode (`stream = False`), sending a `get_joint_angles()` command will request the feedback data before anything is sent from the Artus hand. This communication setting is slower than the streaming mode, but for testing purposes and getting familiar with the Artus hand, we recommend starting with this setting. 
3. Feedback message has the following data: ACK, Feedback angle (degrees), Motor Current (mA), Temperature. The following is a table for the ACK value. 

| ACK Value  | Meaning | 
| :---: | :------: | 
| 2 | ACK_RECEIVED FOR BLOCKING COMMANDS | 
| 9 | ERROR |
| 25 | TARGET ACHIEVED |


### SD Card Intersactions
Before using the Artus Lite's digital IO functionality to communicate with a robotic arm, there are two steps that need to be done. 
1. Users must set the grasps that they want to call. This is done through the UI or general_example.py, using the `save_grasp_onhand` command. This command will save the last command sent to the hand in the designated position specified (1-6) on the SD card and persist through resets.
2. Users can use the `execute_grasp` command to call the grasps through the API. 
3. Users can print to the terminal all 6 grasps saved to the SD Card using `get_saved_grasps_onhand`

Each of the above will print the target command saved on the SD card to the terminal.

### Changing Communication Methods
To change the communication method between USBC, RS485 and CAN, use the `update_param` command. __Additional steps have to be taken to switch to CAN__. Please reach out to the Sarcomere Dynamics team.

### Controlling multiple hands
We can define two instances of hands with different `communication_channel_identifier`. In theory, it can spin up an unlimited amount of hands, bottlenecked by the amount of wifi controllers and COM ports associated with the machine.

### Special Commands
The following commands are to be used in only certain circumstances with the help of the Sarcomere Dynamics Team. __THESE COMMANDS ARE NOT TO BE USED WITHOUT INSTRUCTION FROM SARCOMERE DYNAMICS INC.__

* `reset` command is to be used when a finger is jammed in an closed state and won't respond to a open command, requiring the index of the joint and the motor. 
* `hard_close` command is used when a joint is fully opened and isn't responding to closing command, requiring the index of the joint and the motor.
