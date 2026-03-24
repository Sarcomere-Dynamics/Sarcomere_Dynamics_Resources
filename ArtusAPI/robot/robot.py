"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

# Artus Lite Hands
from .artus_lite.artus_lite_left import ArtusLite_LeftHand
from .artus_lite.artus_lite_right import ArtusLite_RightHand
from .artus_lite.artus_lite_plus_right import ArtusLite_Plus_RightHand
from .artus_lite.artus_lite_plus_left import ArtusLite_Plus_LeftHand

# Artus Talos
from .artus_talos.artus_talos_left import ArtusTalos_Left
from .artus_talos.artus_talos_right import ArtusTalos_Right

# Artus Scorpion
from .artus_scorpion.artus_scorpion import ArtusScorpion

# Artus Dex
from .artus_dex.artus_dex_left import ArtusDex_Left
from .artus_dex.artus_dex_right import ArtusDex_Right

class Robot:
    def __init__(self,
                 robot_type='artus_lite',
                hand_type='left',logger=None):
        
        # initialize robot
        self.robot_type = robot_type
        self.hand_type = hand_type
        self.logger = logger
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
                self.robot = ArtusLite_LeftHand(logger=self.logger)
            elif self.hand_type == 'right':
                self.robot = ArtusLite_RightHand(logger=self.logger)
            else:
                raise ValueError("Unknown hand")

        elif self.robot_type == 'artus_lite_plus':
            if self.hand_type == 'right':
                self.robot = ArtusLite_Plus_RightHand(logger=self.logger)
            elif self.hand_type == 'left':
                self.robot = ArtusLite_Plus_LeftHand(logger=self.logger)
            else:
                raise ValueError("Unknown hand")
        elif self.robot_type == 'artus_talos':
            if self.hand_type == 'right':
                self.robot = ArtusTalos_Right(logger=self.logger)
            elif self.hand_type == 'left':
                self.robot = ArtusTalos_Left(logger=self.logger)
            else:
                raise ValueError("Unknown hand")
        elif self.robot_type == 'artus_scorpion':
            self.robot = ArtusScorpion(logger=self.logger)
        elif self.robot_type == 'artus_dex':
            if self.hand_type == 'right':
                self.robot = ArtusDex_Right(logger=self.logger)
            elif self.hand_type == 'left':
                self.robot = ArtusDex_Left(logger=self.logger)
            else:
                raise ValueError("Unknown hand")
        else:
            raise ValueError("Unknown robot type")
        

    def set_joint_angles(self, joint_angles:dict,name:bool):
        """
        Set the joint angles of the hand
        """
        if name: # scorpion has no name for joints because just 1 joint
            return self.robot.set_joint_angles_by_name(joint_angles)
        else:
            return self.robot.set_joint_angles(joint_angles)
    
    
    def set_home_position(self):
        """
        Set the hand to the home position
        """
        return self.robot.set_home_position()
    
    def get_joint_angles(self, joint_angles, feedback_type=None):
        """
        Get the joint angles of the hand.
        joint_angles: decoded feedback data (list).
        feedback_type: modbus key string (e.g. 'feedback_position_start_reg').
        """
        modbus_key = feedback_type if feedback_type is not None else 'feedback_position_start_reg'
        return self.robot.get_joint_angles(joint_angles, modbus_key=modbus_key)
    

def main():
    artus_robot = Robot(hand_type='left')

if __name__ == "__main__":
    main()