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
    def __init__(self, config_file = PROJECT_ROOT + "//Sarcomere_Dynamics_Resources//examples//general_example//config//artus_config.yaml"):
        self.config = self.load_and_convert_config(config_file)

    def load_and_convert_config(self, config_file):
        with open(config_file, 'r') as file:
            config_dict = yaml.safe_load(file)
        return self.dict_to_namespace(config_dict)

    def dict_to_namespace(self, d):
        """
        Recursively converts a dictionary to a namespace (SimpleNamespace) to access
        nested configurations as attributes.
        """
        if isinstance(d, dict):
            return SimpleNamespace(**{k: self.dict_to_namespace(v) for k, v in d.items()})
        elif isinstance(d, list):
            return [self.dict_to_namespace(i) for i in d]
        else:
            return d

    def check_and_print_robot_config(self):
        """
        Checks and prints the robot configuration based on the 'hand_type' defined
        in the configuration. Raises an error if the 'hand_type' is invalid.
        """
        # Determine the hand type from the config
        hand_type = self.config.robot.artusLite.hand_type
        if hand_type not in ['left', 'right']:
            raise ValueError("Invalid hand type in configuration. Choose 'left' or 'right'.")

        # Get the robot configuration for the specified hand type
        robot_config = self.config.robot.artusLite

        # Check if the robot is connected and print its configuration
        if robot_config.robot_connected:
            print(f"\n{hand_type.capitalize()} Hand Robot Configuration:")
            for key, value in vars(robot_config).items():
                print(f"{key}: {value}")
        else:
            print(f"\n{hand_type.capitalize()} hand robot is not connected.")

# Example usage
if __name__ == "__main__":
    robot_config = ArtusLiteConfig()

    # Check and print the robot configuration
    robot_config.check_and_print_robot_config()