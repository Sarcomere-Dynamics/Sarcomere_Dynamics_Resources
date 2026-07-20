"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from curses import has_key
from ...sensors import ForceSensor
from ..bldc_robot.bldcrobot import BLDCRobot
import logging

class ArtusTalos(BLDCRobot):
    """ARTUS Talos hand model: 6 joints with per-finger force sensors."""
    def __init__(self,
                joint_max_angles=[55,90,90,90,90,90],
                joint_min_angles=[-55,0,0,0,0,0],
                joint_default_angles=[],
                joint_rotation_directions=[1,1,1,1,1,1],
                joint_forces=[],
                joint_names=['thumb_spread','thumb_flex','index_flex',
                            'middle_flex','ring_flex','pinky_flex'],
                number_of_joints=6,
                logger=None):
        """Initializes the ARTUS Talos joint model, force sensors, and defaults.

        Args:
            joint_max_angles: Maximum angle per joint (6 values: thumb
                spread/flex, index, middle, ring, pinky flex).
            joint_min_angles: Minimum angle per joint.
            joint_default_angles: Default (home) angle per joint.
            joint_rotation_directions: +1/-1 rotation multiplier per joint.
            joint_forces: Per-joint force values (unused by base
                construction).
            joint_names: Ordered joint name strings.
            number_of_joints: Total number of joints (6).
            logger: Optional logger instance passed through to ``BLDCRobot``.
        """
        super().__init__(joint_max_angles=joint_max_angles,
                         joint_min_angles=joint_min_angles,
                         joint_default_angles=joint_default_angles,
                         joint_rotation_directions=joint_rotation_directions,
                         joint_forces=joint_forces,
                         joint_names=joint_names,
                         number_of_joints=number_of_joints,
                         logger=logger)

        # force sensor init
        self.force_sensors = {}
        fingers = ['thumb', 'index', 'middle', 'ring', 'pinky']
        indices = [[0,1],[2],[3],[4],[5]]

        for i in range(len(fingers)):
            self.force_sensors[fingers[i]] = {
                'data' : ForceSensor(),
                'indices' : indices[i]
            }

        # add force sensor feedback type
        self.available_feedback_types.append('feedback_force_sensor_start_reg')

        # speeds
        self.max_velocity = 300
        self.min_velocity = 0
        self.default_velocity = 200

        # forces
        self.max_force = 40
        self.min_force = 2
        self.default_force = 16

        # pwm (legacy)
        self.default_pwm = None
        self.max_pwm = None
        self.min_pwm = None
