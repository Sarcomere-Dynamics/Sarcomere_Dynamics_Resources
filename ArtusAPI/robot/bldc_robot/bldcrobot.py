"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import logging

"""Base robot model shared by all ARTUS BLDC-actuated hand variants."""

class BLDCRobot:
    """Base class defining joint layout, limits, and the ``Joint`` data model.

    Subclasses (ArtusTalos, ArtusLite, ArtusScorpion, ArtusDex, ...) extend
    this with force sensor configuration and velocity/force defaults.

    Attributes:
        force_sensors: Dict of per-finger force sensor data, or None if the
            variant has no force sensors.
        joint_max_angles: List of maximum angle limits per joint.
        joint_min_angles: List of minimum angle limits per joint.
        joint_default_angles: List of default (home) angles per joint.
        joint_rotation_directions: List of +1/-1 rotation direction
            multipliers per joint.
        joint_forces: List of per-joint force values (currently unused by
            base construction).
        joint_names: Ordered list of joint name strings.
        number_of_joints: Total number of joints on the hand.
        number_of_controllers: Number of actuator controllers (defaults to
            ``number_of_joints`` if not given).
        hand_joints: Dict mapping joint name to a ``Joint`` instance.
        Joint: Inner class used to represent a single joint's state.
    """
    def __init__(self,
                joint_max_angles=[55,90,90,90,90,90],
                joint_min_angles=[-55,0,0,0,0,0],
                joint_default_angles=[],
                joint_rotation_directions=[1,1,1,1,1,1],
                joint_forces=[],
                joint_names=['thumb_spread','thumb_flex','index_flex',
                            'middle_flex','ring_flex','pinky_flex'],
                number_of_joints=6,
                number_of_controllers=None,
                logger=None):
        """Initializes joint limits/defaults and builds the joint dictionary.

        Args:
            joint_max_angles: Maximum angle (or stroke) limit per joint.
            joint_min_angles: Minimum angle (or stroke) limit per joint.
            joint_default_angles: Default (home) angle per joint.
            joint_rotation_directions: +1/-1 multiplier applied to target
                angles per joint, used to mirror left/right hands.
            joint_forces: Per-joint force values (unused by base
                construction; freed after ``_create_hand``).
            joint_names: Ordered joint name strings.
            number_of_joints: Total number of joints on the hand.
            number_of_controllers: Number of actuator controllers. Defaults
                to ``number_of_joints`` if not provided.
            logger: Optional logger instance; a module logger is created if
                not provided.
        """

        self.force_sensors = None

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.available_feedback_types = ['feedback_position_start_reg', 'feedback_force_start_reg', 'feedback_velocity_start_reg','feedback_temperature_start_reg','feedback_voltage_start_reg']
                
        self.joint_max_angles = joint_max_angles
        self.joint_min_angles = joint_min_angles
        self.joint_default_angles = joint_default_angles
        self.joint_rotation_directions = joint_rotation_directions
        self.joint_forces = joint_forces
        self.joint_names = joint_names
        self.number_of_joints = number_of_joints

        if number_of_controllers is None:
            self.number_of_controllers = number_of_joints
        else:
            self.number_of_controllers = number_of_controllers

        class Joint:
            """Mutable state container for a single joint's targets and feedback."""
            def __init__(self, index, min_angle, max_angle, default_angle, target_angle, target_force, temperature, joint_rotation_direction):
                """Initializes a joint's limits, targets, and feedback fields.

                Args:
                    index: Zero-based joint index, matching Modbus ordering.
                    min_angle: Minimum allowed target angle (or stroke).
                    max_angle: Maximum allowed target angle (or stroke).
                    default_angle: Default (home) angle.
                    target_angle: Initial target angle.
                    target_force: Initial target force.
                    temperature: Initial feedback temperature value.
                    joint_rotation_direction: +1/-1 multiplier applied to
                        target angles.
                """
                self.index = index
                self.min_angle = min_angle
                self.max_angle = max_angle
                self.default_angle = default_angle
                self.target_angle = target_angle
                self.target_force = target_force
                self.target_velocity = None
                self.feedback_angle = 0
                self.feedback_current = 0
                self.feedback_velocity = 0
                self.feedback_force = 0.0
                self.feedback_temperature = temperature
                self.joint_rotation_direction = joint_rotation_direction

            def __str__(self):
                """Returns a short human-readable summary of index and target angle."""
                return "Index: " + str(self.index)+"Target Angle: " +str(self.target_angle)

        self.Joint = Joint

        self._create_hand()

    def _create_hand(self):
        """Builds ``self.hand_joints`` from the configured per-joint limit lists.

        Frees the now-unneeded configuration lists
        (``joint_max_angles``, ``joint_min_angles``, ``joint_default_angles``,
        ``joint_rotation_directions``, ``joint_forces``) after populating
        ``hand_joints``.
        """
        self.hand_joints = {}
        for joint_index,joint_name in enumerate(self.joint_names):
            self.hand_joints[joint_name] = self.Joint(index=joint_index,
                                                      min_angle=self.joint_min_angles[joint_index],
                                                      max_angle=self.joint_max_angles[joint_index],
                                                      default_angle=0,
                                                      target_angle=0,
                                                      target_force=0,
                                                      temperature=0,
                                                      joint_rotation_direction=self.joint_rotation_directions[joint_index])

        # free up mem
        del self.joint_max_angles, self.joint_min_angles, self.joint_default_angles, self.joint_rotation_directions, self.joint_forces
        


    def set_joint_angles(self, joint_angles:dict):
        """Sets target angle/velocity/force on joints, addressed by index.

        Sorts the input by joint index (skipping the sort for a single-item
        dict), applies each joint's rotation direction to target_angle, and
        clamps the results to the configured joint limits.

        Args:
            joint_angles: Dict keyed by arbitrary key, each value a dict
                containing an ``index`` and any combination of
                ``target_angle``, ``target_velocity``, ``target_force``.
                Entries whose index is out of range are skipped.

        Returns:
            Bitmask of which control types were set: bit 2 (0b100) for
            target_angle, bit 1 (0b10) for target_velocity, bit 0 (0b1) for
            target_force.
        """
        # verify that items are in order of index
        available_control = 0
        # INSERT_YOUR_CODE
        if len(joint_angles) == 1:
            sorted_items = joint_angles.items()
        else:
            sorted_items = sorted(joint_angles.items(), key=lambda x: x[1]['index'])
        # sorted_items = sorted(joint_angles.items(), key=lambda x:x[1]['index'])
        ordered_joint_angles = {key:value for key,value in sorted_items}
        # set values based on index
        for name,target_data in ordered_joint_angles.items():
            if target_data['index'] >= self.number_of_joints: # if trying to give more than the available joints, skip
                self.logger.debug(f"Trying to set joint {target_data['index']} which is greater than the available joints ({self.number_of_joints})")
                continue

            # fill data based on control type
            if 'target_angle' in target_data:
                available_control |= 0b100
                self.hand_joints[self.joint_names[target_data['index']]].target_angle = target_data['target_angle'] * self.hand_joints[self.joint_names[target_data['index']]].joint_rotation_direction
                self.logger.debug(f"Setting target angle for {self.joint_names[target_data['index']]} to {target_data['target_angle']}")
            if 'target_velocity' in target_data:
                available_control |= 0b10
                self.hand_joints[self.joint_names[target_data['index']]].target_velocity = target_data['target_velocity']
                self.logger.debug(f"Setting target velocity for {self.joint_names[target_data['index']]} to {target_data['target_velocity']}")
            if 'target_force' in target_data:
                available_control |= 0b1
                self.hand_joints[self.joint_names[target_data['index']]].target_force = target_data['target_force']
                self.logger.debug(f"Setting target force for {self.joint_names[target_data['index']]} to {target_data['target_force']}")
        self._check_joint_limits(self.hand_joints)

        return available_control

    def set_joint_angles_by_name(self, joint_angles:dict):
        """Sets target angle/velocity/force on joints, addressed by name.

        Applies each joint's rotation direction to target_angle and clamps
        the results to the configured joint limits.

        Args:
            joint_angles: Dict keyed by joint name, each value a dict
                containing any combination of ``target_angle``,
                ``target_velocity``, ``target_force``. Names not in
                ``self.joint_names`` are skipped.

        Returns:
            Bitmask of which control types were set: bit 2 (0b100) for
            target_angle, bit 1 (0b10) for target_velocity, bit 0 (0b1) for
            target_force.
        """
        available_control = 0
        # set values based on names
        for name,target_data in joint_angles.items():
            if name not in self.joint_names: # if trying to give more than the available joints, skip
                self.logger.debug(f"Trying to set joint {target_data['index']} which is greater than the available joints ({self.number_of_joints})")
                continue


            # fill data based on control type
            if 'target_angle' in target_data:
                available_control |= 0b100
                self.hand_joints[name].target_angle = target_data['target_angle'] * self.hand_joints[name].joint_rotation_direction
                self.logger.debug(f"Setting target angle for {name} to {target_data['target_angle']}")
            if 'target_velocity' in target_data:
                available_control |= 0b10
                self.hand_joints[name].target_velocity = target_data['target_velocity']
                self.logger.debug(f"Setting target velocity for {name} to {target_data['target_velocity']}")
            if 'target_force' in target_data:
                available_control |= 0b1
                self.hand_joints[name].target_force = target_data['target_force']
                self.logger.debug(f"Setting target force for {name} to {target_data['target_force']}")

        self._check_joint_limits(self.hand_joints)

        return available_control


    def _check_joint_limits(self, joint_angles):
        """Clamps each joint's target_angle to its configured min/max limits.

        Args:
            joint_angles: Dict mapping joint name to ``Joint`` instance
                (typically ``self.hand_joints``); mutated in place. Note the
                lookup for limits is keyed against ``self.hand_joints``
                regardless of the ``joint_angles`` argument passed in.

        Returns:
            The same ``joint_angles`` dict, with target_angle clamped.
        """
        for name,joint in self.hand_joints.items():
            if joint_angles[name].target_angle > joint.max_angle:
                joint_angles[name].target_angle = joint.max_angle
                self.logger.warning(f"Joint {name} target angle is greater than the max angle, setting to {joint.max_angle}")
                # TODO logging
            if joint_angles[name].target_angle < joint.min_angle:
                joint_angles[name].target_angle = joint.min_angle
                self.logger.warning(f"Joint {name} target angle is less than the min angle, setting to {joint.min_angle}")
                # TODO logging
        return joint_angles

    def _check_joint_forces(self, joint_angles):
        """Clamps joint force values to each joint's max_force/min_force.

        Note:
            Iterates ``self.hand_joints`` as ``Joint`` objects but indexes
            ``joint_angles`` positionally via ``joint.index`` and reads
            ``joint.max_force``/``joint.min_force``, which are not set by
            the base ``Joint`` class.

        Args:
            joint_angles: Indexable collection of force values, addressed by
                ``joint.index``; mutated in place.

        Returns:
            The same ``joint_angles`` collection, with values clamped.
        """
        for joint in self.hand_joints:
            if joint_angles[joint.index] > joint.max_force:
                joint_angles[joint.index] = joint.max_force
                # TODO logging
            if joint_angles[joint.index] < joint.min_force:
                joint_angles[joint.index] = joint.min_force
                # TODO logging
        return joint_angles

    def set_home_position(self):
        """Builds a joint command dict targeting each joint's default angle.

        Uses ``self.default_velocity`` (0 if not set by a subclass) as the
        velocity for every joint.

        Returns:
            Result of ``self.set_joint_angles`` for the generated command.
        """
        default_velocity = getattr(self, 'default_velocity', 0)
        joint_angles = {key: {'index': value.index, 'target_angle': value.default_angle, 'target_velocity': default_velocity} for key, value in self.hand_joints.items()}
        return self.set_joint_angles(joint_angles)
    
    def get_joint_angles(self, feedback_package:list,modbus_key:str='feedback_position_start_reg'):
        """Populates feedback fields in ``hand_joints`` from decoded data.

        Only named ``get_joint_angles`` for consistency with the v1 API.

        Args:
            feedback_package: Decoded feedback values. For
                ``feedback_force_sensor_start_reg`` this is a flat list of
                x/y/z triples per force sensor; otherwise it is indexed per
                joint via ``joint_data.index``.
            modbus_key: Which feedback field to populate -- one of
                'feedback_position_start_reg', 'feedback_force_start_reg',
                'feedback_temperature_start_reg',
                'feedback_velocity_start_reg', or
                'feedback_force_sensor_start_reg'.

        Returns:
            The ``feedback_package`` passed in (allows reading control
            registers too), or None if a TypeError or other exception
            occurred while populating.
        """
        # TODO logging
        try:

            if modbus_key == 'feedback_force_sensor_start_reg':
                # force sensor data is special, so we need to loop through the force sensors
                i = 0
                for key,value in self.force_sensors.items():
                    value['data'].x = feedback_package[i]
                    value['data'].y = feedback_package[i+1]
                    value['data'].z = feedback_package[i+2]
                    i+=3
            else:
                # normal loop through joint data and populate feedback fields
                for name,joint_data in self.hand_joints.items():
                    if modbus_key == 'feedback_position_start_reg':
                        joint_data.feedback_angle = feedback_package[joint_data.index]
                    elif modbus_key == 'feedback_force_start_reg':
                        joint_data.feedback_force = feedback_package[joint_data.index]
                    elif modbus_key == 'feedback_temperature_start_reg':
                        joint_data.feedback_temperature = feedback_package[joint_data.index]
                    elif modbus_key == 'feedback_velocity_start_reg':
                        joint_data.feedback_velocity = feedback_package[joint_data.index]

            # return feedback package no matter what -- ability to read control registers too
            return feedback_package
        except TypeError:
            # TODO logging
            return None
        except Exception as e:
            print(e)
            return None