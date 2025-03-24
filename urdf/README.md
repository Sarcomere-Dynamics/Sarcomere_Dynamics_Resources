# Mapping URDF Joint Positions to Real Robot Joint Positions

This guide explains the process of mapping URDF joint positions to real robot joint positions for Artus Lite hand robot.
The URDF model contains 20 joints, whereas the real robot has 16 joints.
URDF joint positions are represented in radians, while real robot joint positions are represented in degrees (as integers).

## URDF Joint Names and Order
The URDF joint names and their order are as follows:

```yaml
index_01
middle_01
pinky_01
ring_01
thumb_01
index_12
middle_12
pinky_12
ring_12
thumb_12
index_23
middle_23
pinky_23
ring_23
thumb_23
index_34
middle_34
pinky_34
ring_34
thumb_34
```
## Real Robot Joint Names and Order
For the real robot joint names and their order, please refer to the [real robot joint names and order](https://github.com/Sarcomere-Dynamics/Sarcomere_Dynamics_Resources/tree/main/ArtusAPI/robot/artus_lite) in the ArtusAPI repository.

## Mapping Details
### Units Conversion
- URDF: Joint positions are in radians.
- Real Robot: Joint positions are in degrees (integers).

### Abduction Angles
For the right hand, the abduction angles are negative for the following fingers:
- Index
- Middle
- Ring
- Pinky

## Mapping Process
### 1. Extract URDF Joint Positions:
Extract the joint positions from the URDF model in radians.
### 2. Convert to Degrees:
Convert the joint positions from radians to degrees.
### 3. Map to Real Robot Joints:
Map the URDF joint positions to the corresponding real robot joints.

### 4. Adjust Abduction Angles:
For the right hand, ensure the abduction angles for the index, middle, ring, and pinky fingers are negative.

### 5. Convert to Integers:
Convert the joint positions to integers for the real robot.