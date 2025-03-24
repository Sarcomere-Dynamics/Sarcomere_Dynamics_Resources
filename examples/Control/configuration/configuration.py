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


import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

class ArtusLiteConfig:
    def __init__(self, config_file = PROJECT_ROOT + "//Sarcomere_Dynamics_Resources//examples//Control//configuration//robot_config.yaml"):
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

# Example usage
if __name__ == "__main__":
    robot_config = ArtusLiteConfig()

    # Check and print configuration for left hand robot
    robot_config.check_and_print_robot_config('left')

    # Check and print configuration for right hand robot
    robot_config.check_and_print_robot_config('right')
