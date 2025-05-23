"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from .artus_lite.artus_lite_left import ArtusLite_LeftHand
from .artus_lite.artus_lite_right import ArtusLite_RightHand
from .artus_lite.artus_lite_plus_right import ArtusLite_Plus_RightHand
from .artus_lite.artus_lite_plus_left import ArtusLite_Plus_LeftHand
# Artus 3D Robots


class Robot:
    def __init__(self,
                 robot_type='artus_lite',
                hand_type='left'):
        
        # initialize robot
        self.robot_type = robot_type
        self.hand_type = hand_type
        # setup robot
        self.robot = None
        self._setup_robot()

    def _setup_robot(self):
        """
        Initialize robot based on the robot type and hand type
        """
        # setup robot based on the hand
        if self.robot_type == 'artus_lite':
            if self.hand_type == 'left':
                self.robot = ArtusLite_LeftHand()
            elif self.hand_type == 'right':
                self.robot = ArtusLite_RightHand()
            else:
                raise ValueError("Unknown hand")
        
        elif self.robot_type == 'artus_lite_plus':
            # if self.hand_type == 'left':
            #     self.robot = ArtusLite_LeftHand()
            if self.hand_type == 'right':
                self.robot = ArtusLite_Plus_RightHand()
            elif self.hand_type == 'left':
                self.robot = ArtusLite_Plus_LeftHand()
            else:
                raise ValueError("Unknown hand")
        else:
            raise ValueError("Unknown robot type")
        

    def set_joint_angles(self, joint_angles:dict,name:bool):
        """
        Set the joint angles of the hand
        """
        if name:
            return self.robot.set_joint_angles_by_name(joint_angles)
        else:
            return self.robot.set_joint_angles(joint_angles)
    
    
    def set_home_position(self):
        """
        Set the hand to the home position
        """
        return self.robot.set_home_position()
    
    def get_joint_angles(self, joint_angles):
        """
        Get the joint angles of the hand
        """
        return self.robot.get_joint_angles(joint_angles)
    

def main():
    artus_robot = Robot(hand_type='left')

if __name__ == "__main__":
    main()