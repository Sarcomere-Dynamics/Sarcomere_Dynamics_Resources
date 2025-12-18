"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from ..bldc_robot.bldcrobot import BLDCRobot

class ArtusScorpion(BLDCRobot):
    def __init__(self,
                joint_max_angles=[21], # stroke mm
                joint_min_angles=[0],
                joint_default_angles=[],
                joint_rotation_directions=[1],
                joint_torques=[],
                joint_names=['gripper_joint'],
                number_of_joints=1,
                logger=None):
        super().__init__(joint_max_angles=joint_max_angles,
                         joint_min_angles=joint_min_angles,
                         joint_default_angles=joint_default_angles,
                         joint_rotation_directions=joint_rotation_directions,
                         joint_torques=joint_torques,
                         joint_names=joint_names,
                         number_of_joints=number_of_joints,
                         logger=logger)

        # set sensors
        self.available_feedback_types = ['feedback_position_start_reg', 'feedback_torque_start_reg', 'feedback_velocity_start_reg']