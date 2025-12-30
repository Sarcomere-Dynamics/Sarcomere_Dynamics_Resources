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
from ...sensors import ForceSensor
class ArtusScorpion(BLDCRobot):
    def __init__(self,
                joint_max_angles=[50], # stroke mm
                joint_min_angles=[0],
                joint_default_angles=[],
                joint_rotation_directions=[1],
                joint_forces=[],
                joint_names=['gripper_joint'],
                number_of_joints=1,
                logger=None):
        super().__init__(joint_max_angles=joint_max_angles,
                         joint_min_angles=joint_min_angles,
                         joint_default_angles=joint_default_angles,
                         joint_rotation_directions=joint_rotation_directions,
                         joint_forces=joint_forces,
                         joint_names=joint_names,
                         number_of_joints=number_of_joints,
                         logger=logger)

        # set sensors
        self.available_feedback_types = ['feedback_position_start_reg', 'feedback_force_start_reg', 'feedback_velocity_start_reg']

        # force sensor init
        self.force_sensors = {}
        self.force_sensors['gripper_joint'] = {
            'data' : ForceSensor(),
            'indices' : [0]
        }

        self.logger = logger

    def set_joint_angles_by_name(self, joint_angles:dict):
        # verify that items are in order of index 
        available_control = 0

        # INSERT_YOUR_CODE
        target_data = None
        # look for gripper_joint in joint_angles
        if 'gripper_joint' not in joint_angles:
            self.logger.warning("Gripper joint not found in joint angles, defaulting to thumb_spread")
            target_data = joint_angles['thumb_spread'] # use the zero index joint as default
        else:
            target_data = joint_angles['gripper_joint']
        name = 'gripper_joint'
        # fill data based on control type
        if 'target_angle' in target_data:
            available_control |= 0b100
            self.hand_joints[name].target_angle = target_data['target_angle'] * self.hand_joints[name].joint_rotation_direction
            self.logger.info(f"Setting target angle for {name} to {target_data['target_angle']}")
        if 'target_velocity' in target_data:
            available_control |= 0b10
            self.hand_joints[name].target_velocity = target_data['velocity']
            self.logger.info(f"Setting target velocity for {name} to {target_data['velocity']}")
        if 'target_force' in target_data:
            available_control |= 0b1
            self.hand_joints[name].target_force = target_data['target_force']
            self.logger.info(f"Setting target force for {name} to {target_data['target_force']}")
    
        self._check_joint_limits(self.hand_joints)

        return available_control

    def set_joint_angles(self, joint_angles:dict):
        return self.set_joint_angles_by_name(joint_angles)