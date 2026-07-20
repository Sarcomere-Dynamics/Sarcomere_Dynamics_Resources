<img src='../data/images/SarcomereLogoHorizontal.svg'>


# Update Log December 2025

This update is our biggest update yet. We are starting to release our new line of robotic end-effectors out which include the following:
* Artus Scorpion (Parallel Gripper)
* Artus Talos (6 Active DOF Gripper)

These new systems are full system updates from the Artus Lite, and have designed the systems keeping in mind the shortcomings of the Artus Lite. These systems utilize very similar control drives, which are our compact Brushless Motor Controllers. 

With this update, there is a bit of a mismatch in APIs between the legacy Artus Lite and the new products. The Artus Lite will run on the `ArtusAPI` whereas the new products will run on the `ArtusAPIV2`. In the new year, we are going to refresh the software for the Artus Lite to more similarly follow what the v2 API allows. However, for now, the Aruts Lite will run on the legacy `ArtusAPI`. There are some empty functions in both the v2 and v1 APIs which are mainly just there as placeholders for forward and backward compatability between the two APIs, for application level calls. 

This update is __NOT__ being pushed to PIP until everything has made the switch over to the new API and the software is more stable. Therefore, latest repo must be pulled at all times.

## List of Updates

Below is a list of updates in bullet form with a small description. 

* APIv1 remove stream flag for reliability. 
* Addition of MODBUS RTU - we were seeing some issues with communication over RS485 on the Artus Lite where the communication was becoming unreliable at greater frequencies and sending random commands. MODBUS RTU is a standard communication protocol, with some error checking which has removed the issue of random commands. Communication will follow this architecture for the immediate future. 
* MODBUS Map - Outlines how to set targets and read data from the systems. The registers are split up by type (i.e. target positions, target velocities, commands) and span the amount of joints available. So the Artus Scorpion will only have a single register for target position, while the Artus Talos has 6 values you can write to it.
* Addition of ACTUATOR STATE enumeration for more verbose understanding of states.

ArtusAPI V2
* Ability to control system via 3 control types, position control, velocity control and force control -- can set targets for velocity and force for position control as well, however currently just used as limits. Feedforward on the roadmap...
* Feedback data includes velocity, force and position.

* GUI Update - PySide6 from PyQT5, should be compatible with both APIs. Joint naming consistent with those outlined in the APIs, added textbox for position entry. Added different feedback visualization based on drop down menu. Created dynamically based on the amount of joints available to the robot. 
* Configuration - Single configuration file for all examples now - no need to look in different places. In provided examples, automatically find the API version needed for the robot in the `robot_config.YAML` file. 
* Removed `artuslitejointstreamer` - Functionality was very much the same as what was in the api. Double up didn't make sense.
* API - add the ability to set joint angles by list - similar to the `artuslitejointstreamer.stream_joint_angles` function. MUST know the joint list array of the robot. 
* working on making nomenclature/variables/naming across code consistent. 
* update project root in application scripts to be the root folder of the repo

## Additional Notes
* ROS2 node has not been updated for the new API - stay tuned. 
* This is a very early release - expect bugs. Please reach out and let the Sarcomere Dynamics team know. 