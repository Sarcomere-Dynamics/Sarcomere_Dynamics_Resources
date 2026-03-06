"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import logging
from ..bldc_robot.bldcrobot import BLDCRobot


class ArtusLite(BLDCRobot):
    def __init__(self,
                 joint_max_angles=[40, 90, 90, 90,  # thumb
                                  17, 90, 90,  # index
                                  17, 90, 90,  # middle
                                  17, 90, 90,  # ring
                                  17, 90, 90],  # pinky
                 joint_min_angles=[-40, 0, 0, 0,  # thumb
                                  -17, 0, 0,  # index
                                  -17, 0, 0,  # middle
                                  -17, 0, 0,  # ring
                                  -17, 0, 0],  # pinky
                 joint_default_angles=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                 joint_rotation_directions=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                 joint_forces=[],
                 joint_names=['thumb_spread', 'thumb_flex', 'thumb_d2', 'thumb_d1',
                              'index_spread', 'index_flex', 'index_d2',
                              'middle_spread', 'middle_flex', 'middle_d2',
                              'ring_spread', 'ring_flex', 'ring_d2',
                              'pinky_spread', 'pinky_flex', 'pinky_d2'],
                 number_of_joints=16,
                 logger=None):
        super().__init__(joint_max_angles=joint_max_angles,
                         joint_min_angles=joint_min_angles,
                         joint_default_angles=joint_default_angles,
                         joint_rotation_directions=joint_rotation_directions,
                         joint_forces=joint_forces,
                         joint_names=joint_names,
                         number_of_joints=number_of_joints,
                         logger=logger)

        # speeds (deg/s)
        self.max_velocity = 300
        self.min_velocity = 0
        self.default_velocity = 150

        # forces (N)
        self.max_force = 20
        self.min_force = 0
        self.default_force = 10

        # pwm (legacy)
        self.max_pwm = 100
        self.min_pwm = 40
        self.default_pwm = 70
