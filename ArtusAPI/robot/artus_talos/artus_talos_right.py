"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""
from .artus_talos import ArtusTalos
class ArtusTalos_Right(ArtusTalos):
    def __init__(self,logger):
        super().__init__(
                joint_max_angles=[35,90,90,90,90,90],
                joint_min_angles=[-35,0,0,0,0,0],
                joint_default_angles=[0,0,0,0,0,0],
                joint_rotation_directions=[1,1,1,1,1,1],
                joint_forces=[],
                number_of_joints=6,
                logger=logger)