"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from ..bldc_robot.bldcrobot import BLDCRobot
from ...sensors import ForceSensor
class ArtusScorpion(BLDCRobot):
    """ARTUS Scorpion gripper model: single gripper joint with two force sensors."""
    def __init__(self,
                joint_max_angles=[50], # stroke mm
                joint_min_angles=[0],
                joint_default_angles=[],
                joint_rotation_directions=[1],
                joint_forces=[],
                joint_names=['gripper_joint'],
                number_of_joints=1,
                logger=None):
        """Initializes the Scorpion gripper joint model and defaults.

        Args:
            joint_max_angles: Maximum stroke in mm (single-element list).
            joint_min_angles: Minimum stroke in mm.
            joint_default_angles: Default (home) stroke.
            joint_rotation_directions: +1/-1 rotation multiplier.
            joint_forces: Per-joint force values (unused by base
                construction).
            joint_names: Joint name strings (single 'gripper_joint').
            number_of_joints: Total number of joints (1).
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

        # set sensors
        self.available_feedback_types = ['feedback_position_start_reg', 'feedback_force_start_reg', 'feedback_velocity_start_reg']

        # force sensor init
        self.force_sensors = {}
        fingers = ['gripper_join_left', 'gripper_join_right']
        indices = [[0],[1]]

        for i in range(len(fingers)):
            self.force_sensors[fingers[i]] = {
                'data' : ForceSensor(),
                'indices' : indices[i]
            }

        # add force sensor feedback type
        self.available_feedback_types.append('feedback_force_sensor_start_reg')

        self.logger = logger

        # speeds
        self.max_velocity = 70 # mm/s
        self.min_velocity = 0
        self.default_velocity = 50 # mm/s

        # forces
        self.max_force = 100 # N
        self.min_force = 0 # N
        self.default_force = 20 # N

        # pwm (legacy)
        self.default_pwm = None
        self.max_pwm = None
        self.min_pwm = None

    def set_joint_angles_by_name(self, joint_angles:dict):
        """Sets target angle/velocity/force on the single gripper joint.

        Looks up ``'gripper_joint'`` in ``joint_angles``; if absent, falls
        back to using the ``'thumb_spread'`` entry as the target data
        (compatibility with generic multi-finger joint dicts).

        Args:
            joint_angles: Dict keyed by joint name, expected to contain
                'gripper_joint' (or 'thumb_spread' as a fallback key) mapped
                to a dict with any combination of ``target_angle``,
                ``target_velocity``, ``target_force``.

        Returns:
            Bitmask of which control types were set: bit 2 (0b100) for
            target_angle, bit 1 (0b10) for target_velocity, bit 0 (0b1) for
            target_force.
        """
        # verify that items are in order of index
        available_control = 0

        # INSERT_YOUR_CODE
        target_data = None
        # look for gripper_joint in joint_angles
        if 'gripper_joint' not in joint_angles:
            self.logger.info("Gripper joint not found in joint angles, defaulting to thumb_spread")
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
            self.hand_joints[name].target_velocity = target_data['target_velocity']
            self.logger.info(f"Setting target velocity for {name} to {target_data['target_velocity']}")
        if 'target_force' in target_data:
            available_control |= 0b1
            self.hand_joints[name].target_force = target_data['target_force']
            self.logger.info(f"Setting target force for {name} to {target_data['target_force']}")
    
        self._check_joint_limits(self.hand_joints)

        return available_control

    def set_joint_angles(self, joint_angles:dict):
        """Sets target joint data for the gripper (delegates by name).

        The Scorpion has a single named joint, so index-based addressing is
        not meaningful; this simply forwards to
        ``set_joint_angles_by_name``.

        Args:
            joint_angles: Dict keyed by joint name (see
                ``set_joint_angles_by_name``).

        Returns:
            Bitmask of which control types were set (see
            ``set_joint_angles_by_name``).
        """
        return self.set_joint_angles_by_name(joint_angles)