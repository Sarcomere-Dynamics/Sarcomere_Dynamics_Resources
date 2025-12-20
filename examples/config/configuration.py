"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import yaml
from types import SimpleNamespace

from ArtusAPI.artus_api import ArtusAPI
from ArtusAPI.artus_api_new import ArtusAPI_V2

import os
import sys
import logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

class ArtusConfig:
    """
    This class is used to load and convert the configuration file into a dictionary to be used by the ArtusAPI_V2 class.
    """
    def __init__(self, config_file = PROJECT_ROOT + f"/examples/config/robot_config.yaml"):
        self.config = self.load_and_convert_config(config_file)

    def load_and_convert_config(self, config_file):
        with open(config_file, 'r') as file:
            config_dict = yaml.safe_load(file)
        return self.dict_to_namespace(config_dict)

    def dict_to_namespace(self, d):
        if isinstance(d, dict):
            return SimpleNamespace(**{k: self.dict_to_namespace(v) for k, v in d.items()})
        elif isinstance(d, list):
            return [self.dict_to_namespace(i) for i in d]
        else:
            return d

    def check_and_print_robot_config(self, hand_type):
        # Get the robot config for the specified hand type (left or right)
        if hand_type == 'left':
            robot_config = self.config.robots.left_hand_robot
        elif hand_type == 'right':
            robot_config = self.config.robots.right_hand_robot
        else:
            raise ValueError("Invalid hand type. Choose 'left' or 'right'.")

        # Check if the robot is connected and print values if true
        if robot_config.robot_connected:
            print(f"//n{hand_type.capitalize()} Hand Robot Configuration:")
            for key, value in vars(robot_config).items():
                print(f"{key}: {value}")
        else:
            print(f"//n{hand_type.capitalize()} hand robot is not connected.")

    def find_single_robot_type(self)->str:
        if self.config.robots.left_hand_robot.robot_connected == True and self.config.robots.right_hand_robot.robot_connected == False:
            return self.config.robots.left_hand_robot.robot_type
        elif self.config.robots.right_hand_robot.robot_connected == True and self.config.robots.left_hand_robot.robot_connected == False:
            return self.config.robots.right_hand_robot.robot_type
        else:
            raise ValueError("No robot connected")
            return None

    def get_api(self, logger=None):
        """
        Returns an instance of the appropriate API (ArtusAPI or ArtusAPI_V2)
        based on the connected robot. Only one robot can be connected at a time.
        Checks the robot connected status and returns the appropriate API instance.
        """
        # Lazy import to avoid issues at class definition time
        from ArtusAPI.artus_api import ArtusAPI
        from ArtusAPI.artus_api_new import ArtusAPI_V2

        # Figure out which robot is connected
        if self.config.robots.left_hand_robot.robot_connected and not self.config.robots.right_hand_robot.robot_connected:
            robot_cfg = self.config.robots.left_hand_robot
            print(f"Left hand robot connected")
        elif self.config.robots.right_hand_robot.robot_connected and not self.config.robots.left_hand_robot.robot_connected:
            robot_cfg = self.config.robots.right_hand_robot
            print(f"Right hand robot connected")
        else:
            raise ValueError("No robot connected or multiple robots connected. Only one robot can be connected at a time.")

        # Choose API class based on robot_type or some convention if needed.
        # Here we assume artus_api_new for demonstration — modify as needed.
        # (You may want to base this on the robot_type field, or another field relevant to you)
        return self.return_api(robot_cfg=robot_cfg,logger=logger)
    
    def return_api(self,robot_cfg:dict=None,logger=None):
        """
        Return an instance of the appropriate API
        :param: robot_cfg: dictionary of robot configuration
        """
        if robot_cfg is None:
            return None
        if hasattr(robot_cfg, 'robot_type') and 'lite' in str(robot_cfg.robot_type).lower():
            # Use ArtusAPI_V2 for 'artus_talos', otherwise fallback to ArtusAPI
            return ArtusAPI(logger=logger,
                robot_type=robot_cfg.robot_type,
                communication_method=robot_cfg.communication_method,
                communication_channel_identifier=robot_cfg.communication_channel_identifier,
                hand_type=robot_cfg.hand_type,
                reset_on_start=robot_cfg.reset_on_start,
                communication_frequency=robot_cfg.streaming_frequency if hasattr(robot_cfg, "streaming_frequency") else 20
            )
        else:
            return ArtusAPI_V2(logger=logger,
                robot_type=robot_cfg.robot_type,
                communication_method=robot_cfg.communication_method,
                communication_channel_identifier=robot_cfg.communication_channel_identifier,
                hand_type=robot_cfg.hand_type,
                communication_frequency=robot_cfg.streaming_frequency if hasattr(robot_cfg, "streaming_frequency") else 20
            )
            

    def get_robot_calibrate(self, hand_type:str=None) -> bool:
        """
        Returns True if the robot calibrate flag is set in config, False otherwise
        """
        if hand_type is None:
            if self.config.robots.left_hand_robot.robot_connected:
                return self.config.robots.left_hand_robot.calibrate
            elif self.config.robots.right_hand_robot.robot_connected:
                return self.config.robots.right_hand_robot.calibrate
            else:
                return False
        elif hand_type == 'left':
            return self.config.robots.left_hand_robot.calibrate
        elif hand_type == 'right':
            return self.config.robots.right_hand_robot.calibrate

    def get_robot_wake_up(self, hand_type:str=None) -> bool:
        """
        Returns True if the robot wake up flag is set in config, False otherwise
        """
        if hand_type is None:
            if self.config.robots.left_hand_robot.robot_connected:
                return self.config.robots.left_hand_robot.start_robot
            elif self.config.robots.right_hand_robot.robot_connected:
                return self.config.robots.right_hand_robot.start_robot
            else:
                return False
        elif hand_type == 'left':
            return self.config.robots.left_hand_robot.start_robot
        elif hand_type == 'right':
            return self.config.robots.right_hand_robot.start_robot
        else:
            raise ValueError("Invalid hand type. Choose 'left' or 'right'.")

# Example usage
if __name__ == "__main__":
    robot_config = ArtusConfig()

    # Check and print configuration for left hand robot
    robot_config.check_and_print_robot_config('left')

    # Check and print configuration for right hand robot
    robot_config.check_and_print_robot_config('right')