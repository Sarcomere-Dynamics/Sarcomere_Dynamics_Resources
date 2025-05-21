
class ArtusLite:

    def __init__(self,
                joint_max_angles=[40, 90, 90, 90, # thumb
                                17, 90, 90, # index
                                17, 90, 90, # middle
                                17, 90, 90, # ring
                                17, 90, 90], # pinky
                joint_min_angles=[-40, 0, 0, 0, # thumb
                                -17, 0, 0, # index
                                -17, 0, 0, # middle
                                -17, 0, 0, # ring
                                -17, 0, 0], # pinky

                joint_default_angles=[0, 0, 0, 0, # thumb
                                    0, 0, 0, # index
                                    0, 0, 0, # middle
                                    0, 0, 0, # ring
                                    0, 0, 0], # pinky

                joint_rotation_directions=[1, 1, 1, 1, # thumb
                                        1, 1, 1, # index
                                        1, 1, 1, # middle
                                        1, 1, 1, # ring
                                        1, 1, 1], # pinky

                joint_velocities=[80, 80, 80, 80, # thumb
                                  80, 80, 80, # index
                                  80, 80, 80, # middle
                                  80, 80, 80, # ring
                                  80, 80, 80], # pinky
                joint_names=['thumb_spread', 'thumb_flex', 'thumb_d2', 'thumb_d1', # thumb
                                'index_spread', 'index_flex', 'index_d2', # index
                                'middle_spread', 'middle_flex', 'middle_d2', # middle
                                'ring_spread', 'ring_flex', 'ring_d2', # ring
                                'pinky_spread', 'pinky_flex', 'pinky_d2'], # pinky,

                number_of_joints=16
    ):

        self.joint_max_angles = joint_max_angles
        self.joint_min_angles = joint_min_angles
        self.joint_default_angles = joint_default_angles
        self.joint_rotation_directions = joint_rotation_directions
        self.joint_velocities = joint_velocities
        self.number_of_joints = number_of_joints
        self.joint_names = joint_names

        class Joint:
            def __init__(self, index, min_angle, max_angle, default_angle, target_angle, rotation_direction, velocity, temperature):
                self.index = index
                self.min_angle = min_angle
                self.max_angle = max_angle
                self.default_angle = default_angle
                self.target_angle = target_angle
                self.rotation_direction = rotation_direction
                self.velocity = velocity
                self.feedback_angle = 0
                self.feedback_current = 0
                self.feedback_force = 0.0
                self.feedback_temperature = temperature
                
            def __str__(self):
                return "Index: " + str(self.index)+"Target Angle: " +str(self.target_angle)

        self.Joint = Joint

        self._create_hand()



    def _create_hand(self):
        """
        Creates the hand with all its fingers and joints into a dict
        """
        self.hand_joints = {}
        for joint_index,joint_name in enumerate(self.joint_names):
            joint = self.Joint(index=joint_index,
                            min_angle=self.joint_min_angles[joint_index],
                            max_angle=self.joint_max_angles[joint_index],
                            default_angle=self.joint_default_angles[joint_index],
                            target_angle=self.joint_default_angles[joint_index],
                            rotation_direction=self.joint_rotation_directions[joint_index],
                            velocity=self.joint_velocities[joint_index],
                            temperature=0)
            self.hand_joints[joint_name] = joint

        # free up mem
        del self.joint_max_angles
        del self.joint_min_angles
        del self.joint_rotation_directions
        # self.joint_velocities
        del self.number_of_joints

        def __str__(self):
            return str(self.hand_joints)
        
    """
    @param joint_angles dict requires at least one joint struct with 3 fields in item, __don't care__ about key: 
    1. index : [ 0 <-> 15 ] -- REQUIRED
    2. target_angle: [ -30 <-> 90 ] depending on joint -- REQUIRED
    3. velocity: [60 <-> 100]
    """
    def set_joint_angles(self, joint_angles:dict):
        """
        Set the joint angles of the hand by index
        """
        # verify that items are in order of index 
        sorted_items = sorted(joint_angles.items(), key=lambda x:x[1]['index'])
        ordered_joint_angles = {key:value for key,value in sorted_items}
        # set values based on index
        for name,target_data in ordered_joint_angles.items():
            self.hand_joints[self.joint_names[target_data['index']]].target_angle = target_data['target_angle'] * self.hand_joints[self.joint_names[target_data['index']]].rotation_direction
            
            if 'velocity' in target_data:
                self.hand_joints[self.joint_names[target_data['index']]].velocity = target_data['velocity']
            else: # fill default velocity
                self.hand_joints[self.joint_names[target_data['index']]].velocity = self.joint_velocities[target_data['index']]
        self._check_joint_limits(self.hand_joints)

    """
    @param joint_angles dict requires at least one joint struct with 2 fields in item, with __correct__ key: 
    1. key: joint_name from self.joint_names -- REQUIRED
    2. target_angle: [ -30 <-> 90 ] depending on joint -- REQUIRED
    3. velocity: [60 <-> 100]
    """
    def set_joint_angles_by_name(self, joint_angles:dict):
        """
        Set the joint angles of the hand by name
        """
        # set values based on names
        for name,target_data in joint_angles.items():
            self.hand_joints[name].target_angle = target_data['target_angle']*self.hand_joints[name].rotation_direction
            
            if 'velocity' in target_data:
                self.hand_joints[name].velocity = target_data['velocity']
            else: # fill default velocity
                self.hand_joints[name].velocity = self.joint_velocities[self.hand_joints[name].index]
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
    
    def _check_joint_velocities(self, joint_angles):
        """
        Check if the joint velocities are within limits
        """
        for joint in self.hand_joints:
            if joint_angles[joint.index] > 100:
                joint_angles[joint.index] = 100
                # TODO logging
            if joint_angles[joint.index] < 0:
                joint_angles[joint.index] = 0
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
        """
        Get the joint angles and feedback list data
        and populate the feedback fields in the hand_joints dictionary
        """
        # print(f'FB PACKAGE = {feedback_package}')
        try:
            for name,joint_data in self.hand_joints.items():
                joint_data.feedback_angle = feedback_package[1][joint_data.index]
                joint_data.feedback_current = feedback_package[1][joint_data.index+15]
                joint_data.feedback_force = round(feedback_package[1][joint_data.index+15] * 0.0035904, 2) # take current value and convert to force
                joint_data.feedback_temperature = feedback_package[1][joint_data.index+31]

                if joint_data.index in [1,5,8,11,14] and joint_data.feedback_angle < 0:
                    joint_data.feedback_angle = -joint_data.feedback_angle
                    feedback_package[1][joint_data.index] = -feedback_package[1][joint_data.index]

            return feedback_package
        except TypeError:
            # print(f'feedback_package is None')
            return None
        except Exception as e:
            print(e)
            return None


def main():
    artus_lite = ArtusLite()
    print(artus_lite)
    print(artus_lite.hand_joints)
    print(len(artus_lite.hand_joints))


def print_finger_joint_limits():
    artus_lite = ArtusLite()
    for joint in artus_lite.hand_joints:
        print(joint.index, joint.min_angle, joint.max_angle)
if __name__ == "__main__":
    # main()
    print_finger_joint_limits()
