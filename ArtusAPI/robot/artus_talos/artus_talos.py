"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

class ArtusTalos:
    def __init__(self,
                joint_max_angles=[],
                joint_min_angles=[],
                joint_default_angles=[],
                joint_rotation_directions=[],
                joint_torques=[],
                joint_names=['thumb_spread','thumb_flex','index_flex',
                            'middle_flex','ring_flex','pinky_flex'],
                number_of_joints=6):
        
        self.joint_max_angles = joint_max_angles
        self.joint_min_angles = joint_min_angles
        self.joint_default_angles = joint_default_angles
        self.joint_rotation_directions = joint_rotation_directions
        self.joint_torques = joint_torques
        self.joint_names = joint_names
        self.number_of_joints = number_of_joints
        
        
        class Joint:
            def __init__(self, index, min_angle, max_angle, default_angle, target_angle, torque, temperature, joint_rotation_direction):
                self.index = index
                self.min_angle = min_angle
                self.max_angle = max_angle
                self.default_angle = default_angle
                self.target_angle = target_angle
                self.target_torque = torque
                self.feedback_angle = 0
                self.feedback_current = 0
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
                                                      target_torque=0,
                                                      temperature=0)

        # free up mem
        del self.joint_max_angles, self.joint_min_angles, self.joint_default_angles, self.joint_rotation_directions, self.joint_torques
        
    def set_joint_angles(self, joint_angles:dict)
        # verify that items are in order of index 
        sorted_items = sorted(joint_angles.items(), key=lambda x:x[1]['index'])
        ordered_joint_angles = {key:value for key,value in sorted_items}
        # set values based on index
        for name,target_data in ordered_joint_angles.items():
            self.hand_joints[self.joint_names[target_data['index']]].target_angle = target_data['target_angle'] * self.hand_joints[self.joint_names[target_data['index']]].joint_rotation_direction
            if 'target_torque' in target_data:
                self.hand_joints[self.joint_names[target_data['index']]].target_torque = target_data['target_torque']
            else:
                self.hand_joints[self.joint_names[target_data['index']]].target_torque = self.joint_torques[target_data['index']]

        self._check_joint_limits(self.hand_joints)

    def set_joint_angles_by_name(self, joint_angles:dict):
        """
        Set the joint angles of the hand by name
        """
        # set values based on names
        for name,target_data in joint_angles.items():
            self.hand_joints[name].target_angle = target_data['target_angle'] * self.hand_joints[name].joint_rotation_direction
            if 'target_torque' in target_data:
                self.hand_joints[name].target_torque = target_data['target_torque']
            else:
                self.hand_joints[name].target_torque = self.joint_torques[self.hand_joints[name].index]
        self._check_joint_limits(self.hand_joints)


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

    def _check_joint_torques(self, joint_angles):
        """
        Check if the joint velocities are within limits
        """
        for joint in self.hand_joints:
            if joint_angles[joint.index] > joint.max_torque:
                joint_angles[joint.index] = joint.max_torque
                # TODO logging
            if joint_angles[joint.index] < joint.min_torque:
                joint_angles[joint.index] = joint.min_torque
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

    def get_joint_angles(self, feedback_package:list):
        for name,joint in self.hand_joints.items():
            