"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

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

"""Factory that instantiates the correct robot model from robot/hand type strings."""

class Robot:
    """Factory/facade that instantiates and wraps a specific hand model.

    Attributes:
        robot_type: Robot variant string (e.g. 'artus_talos', 'artus_lite').
        hand_type: Hand side string (e.g. 'left', 'right').
        robot: The instantiated hand model (subclass of ``BLDCRobot``).
    """
    def __init__(self,
                 robot_type='artus_lite',
                hand_type='left',logger=None):
        """Initializes the factory and builds the concrete robot instance.

        Args:
            robot_type: Robot variant, e.g. 'artus_lite', 'artus_lite_plus',
                'artus_talos', 'artus_scorpion', 'artus_dex'.
            hand_type: Hand side, e.g. 'left' or 'right' (ignored for
                'artus_scorpion').
            logger: Optional logger passed through to the robot model.
        """
        # initialize robot
        self.robot_type = robot_type
        self.hand_type = hand_type
        self.logger = logger
        # setup robot
        self.robot = None
        self._setup_robot()
        
    def _setup_robot(self):
        """Instantiates ``self.robot`` based on ``self.robot_type`` and ``self.hand_type``.

        Raises:
            ValueError: If ``robot_type`` is unrecognized, or if
                ``hand_type`` is unrecognized for a robot type that requires
                a left/right hand.
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
        """Sets the joint angles of the hand.

        Args:
            joint_angles: Dictionary of target joint data, keyed by joint
                name or index depending on ``name``.
            name: If True, dispatches by joint name (used for hands with
                named joints, e.g. Scorpion which has a single unnamed
                joint). If False, dispatches by joint index.

        Returns:
            Bitmask of available control types that were set (see
            ``BLDCRobot.set_joint_angles``).
        """
        if name: # scorpion has no name for joints because just 1 joint
            return self.robot.set_joint_angles_by_name(joint_angles)
        else:
            return self.robot.set_joint_angles(joint_angles)


    def set_home_position(self):
        """Moves the hand to its home position.

        Returns:
            Result of the underlying robot's ``set_home_position`` call.
        """
        return self.robot.set_home_position()

    def get_joint_angles(self, joint_angles, feedback_type=None):
        """Populates the robot's joint feedback fields from decoded data.

        Args:
            joint_angles: Decoded feedback data (list).
            feedback_type: Modbus key string (e.g.
                'feedback_position_start_reg'). Defaults to
                'feedback_position_start_reg' if not provided.

        Returns:
            Result of the underlying robot's ``get_joint_angles`` call.
        """
        modbus_key = feedback_type if feedback_type is not None else 'feedback_position_start_reg'
        return self.robot.get_joint_angles(joint_angles, modbus_key=modbus_key)


def main():
    """Demo entry point: instantiates a default (artus_lite, left) Robot."""
    artus_robot = Robot(hand_type='left')

if __name__ == "__main__":
    main()