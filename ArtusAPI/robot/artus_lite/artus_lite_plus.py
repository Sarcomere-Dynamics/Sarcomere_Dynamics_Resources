from .artus_lite import ArtusLite
from ...sensors import ForceSensor

class ArtusLite_Plus(ArtusLite):
    """
    Artus Lite Plus class
    """
    def __init__(self,num_fingers_force=5,                
                 joint_rotation_directions=[1, 1, 1, 1, # thumb
                                        1, 1, 1, # index
                                        1, 1, 1, # middle
                                        1, 1, 1, # ring
                                        1, 1, 1]):
        super().__init__(joint_rotation_directions=joint_rotation_directions)
        self.robot_type = 'artus_lite_plus'
        self.command_len = 33
        self.recv_len = 76

        # force sensor init
        self.force_sensors = {}
        fingers = ['thumb', 'index', 'middle', 'ring', 'pinky']
        indices = [[0,1,2],[3,4,5],[6,7,8],[9,10,11],[12,13,14]]
        
        for i in range(num_fingers_force):
            self.force_sensors[fingers[i]] = {
                'data' : ForceSensor(),
                'indices' : indices[i]
            }

    def get_joint_angles(self, feedback_package:list):
        """
        Get the joint angles and feedback list data
        and populate the feedback fields in the hand_joints dictionary
        """
        # print(f'FB PACKAGE = {feedback_package}')
        try:
            for name,joint_data in self.hand_joints.items():
                # get feedback angles
                joint_data.feedback_angle = feedback_package[1][joint_data.index]

                if joint_data.index in [1,5,8,11,14] and joint_data.feedback_angle < 0:
                    joint_data.feedback_angle = -joint_data.feedback_angle
                    feedback_package[1][joint_data.index] = -feedback_package[1][joint_data.index]

            i = 0
            feedback_slice = feedback_package[1][16:]
            if all(isinstance(val, float) for val in feedback_slice):
                feedback_slice = [round(val, 3) for val in feedback_slice]
                feedback_package[1][16:] = feedback_slice
            # num_vals = len(feedback_slice)
            for key, object in self.force_sensors.items():
                object['data'].x = feedback_slice[i]
                object['data'].y = feedback_slice[i+1]
                object['data'].z = feedback_slice[i+2]
                i += 3
                    
            return feedback_package
        except TypeError:
            # print(f'feedback_package is None')
            return None
        except Exception as e:
            print(e)
            return None