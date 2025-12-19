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
from ...sensors import ForceSensor

class BLDCRobot:
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

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.available_feedback_types = ['feedback_position_start_reg', 'feedback_force_start_reg', 'feedback_velocity_start_reg']
                
        self.joint_max_angles = joint_max_angles
        self.joint_min_angles = joint_min_angles
        self.joint_default_angles = joint_default_angles
        self.joint_rotation_directions = joint_rotation_directions
        self.joint_forces = joint_forces
        self.joint_names = joint_names
        self.number_of_joints = number_of_joints

        class Joint:
            def __init__(self, index, min_angle, max_angle, default_angle, target_angle, target_force, temperature, joint_rotation_direction):
                self.index = index
                self.min_angle = min_angle
                self.max_angle = max_angle
                self.default_angle = default_angle
                self.target_angle = target_angle
                self.target_force = target_force
                self.feedback_angle = 0
                self.feedback_current = 0
                self.feedback_velocity = 0
                self.feedback_force = 0.0
                self.feedback_temperature = temperature
                self.joint_rotation_direction = joint_rotation_direction

            def __str__(self):
                return "Index: " + str(self.index)+"Target Angle: " +str(self.target_angle)

        self.Joint = Joint

        self._create_hand()

    def _create_hand(self):
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
        # verify that items are in order of index 
        available_control = 0
        sorted_items = sorted(joint_angles.items(), key=lambda x:x[1]['index'])
        ordered_joint_angles = {key:value for key,value in sorted_items}
        # set values based on index
        for name,target_data in ordered_joint_angles.items():
            if target_data['index'] >= self.number_of_joints: # if trying to give more than the available joints, skip
                self.logger.warning(f"Trying to set joint {target_data['index']} which is greater than the available joints ({self.number_of_joints})")
                continue

            # fill data based on control type
            if 'target_angle' in target_data:
                available_control |= 0b100
                self.hand_joints[self.joint_names[target_data['index']]].target_angle = target_data['target_angle'] * self.hand_joints[self.joint_names[target_data['index']]].joint_rotation_direction
                self.logger.info(f"Setting target angle for {self.joint_names[target_data['index']]} to {target_data['target_angle']}")
            if 'target_velocity' in target_data:
                available_control |= 0b10
                self.hand_joints[self.joint_names[target_data['index']]].target_velocity = target_data['velocity']
                self.logger.info(f"Setting target velocity for {self.joint_names[target_data['index']]} to {target_data['velocity']}")
            if 'target_force' in target_data:
                available_control |= 0b1
                self.hand_joints[self.joint_names[target_data['index']]].target_force = target_data['target_force']
                self.logger.info(f"Setting target force for {self.joint_names[target_data['index']]} to {target_data['target_force']}")
        self._check_joint_limits(self.hand_joints)

        return available_control

    def set_joint_angles_by_name(self, joint_angles:dict):
        """
        Set the joint angles of the hand by name
        """
        available_control = 0
        # set values based on names
        for name,target_data in joint_angles.items():
            if target_data['index'] >= self.number_of_joints: # if trying to give more than the available joints, skip
                self.logger.warning(f"Trying to set joint {target_data['index']} which is greater than the available joints ({self.number_of_joints})")
                continue


            # fill data based on control type
            if 'target_angle' in target_data:
                available_control |= 0b100
                self.hand_joints[self.joint_names[target_data['index']]].target_angle = target_data['target_angle'] * self.hand_joints[self.joint_names[target_data['index']]].joint_rotation_direction
                self.logger.info(f"Setting target angle for {self.joint_names[target_data['index']]} to {target_data['target_angle']}")
            if 'target_velocity' in target_data:
                available_control |= 0b10
                self.hand_joints[self.joint_names[target_data['index']]].target_velocity = target_data['velocity']
                self.logger.info(f"Setting target velocity for {self.joint_names[target_data['index']]} to {target_data['velocity']}")
            if 'target_force' in target_data:
                available_control |= 0b1
                self.hand_joints[self.joint_names[target_data['index']]].target_force = target_data['target_force']
                self.logger.info(f"Setting target force for {self.joint_names[target_data['index']]} to {target_data['target_force']}")

        self._check_joint_limits(self.hand_joints)

        return available_control


    def _check_joint_limits(self, joint_angles):
        """
        Check if the joint angles are within the limits
        """
        for name,joint in self.hand_joints.items():
            if joint_angles[name].target_angle > joint.max_angle:
                joint_angles[name].target_angle = joint.max_angle
                # TODO logging
            if joint_angles[name].target_angle < joint.min_angle:
                joint_angles[name].target_angle = joint.min_angle
                # TODO logging
        return joint_angles

    def _check_joint_forces(self, joint_angles):
        """
        Check if the joint velocities are within limits
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
        """
        Set the hand to the home position at default velocity
        """
        # create new target dictionary with default velocity and default angle
        
        joint_angles = {key: {'index': value.index, 'target_angle':value.default_angle,'velocity':self.joint_velocities[value.index]} for key,value in self.hand_joints.items()}
        # print(self.hand_joints['thumb_spread'])
        return self.set_joint_angles(joint_angles)
    
    def get_joint_angles(self, feedback_package:list,modbus_key:str='feedback_position_start_reg'):
        """
        only named get_joint_angles for consistency with v1 api
        Get the joint angles and feedback list data
        and populate the feedback fields in the hand_joints dictionary
        """
        # TODO logging
        try:

            if modbus_key == 'feedback_force_sensor_start_reg':
                # force sensor data is special, so we need to loop through the force sensors
                for key,value in self.force_sensors.items():
                    value['data'].x = feedback_package[value['indices'][0]]
                    value['data'].y = feedback_package[value['indices'][1]]
                    value['data'].z = feedback_package[value['indices'][2]]
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