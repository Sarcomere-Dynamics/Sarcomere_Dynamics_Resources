"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import time
import numpy as np


import os
import sys
import logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
from examples.config.configuration import ArtusConfig
from examples.Tracking.hand_tracking_data import HandTrackingData

# set up logger
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
logger = logging.getLogger(__name__)
logger.propagate = True  # Ensure logs propagate to parent loggers

class ManusGloveController:
    def __init__(self):
        """
        Update the configuration file before running the controller
        """
        # Load robot configuration
        self.robot_config = ArtusConfig()
        self.artusLite_jointStreamers = {'left': None, 'right': None}
        self._initialize_api()

        # Initialize hand tracking data
        self.hand_tracking_data = HandTrackingData(hand_tracking_method='manus_gloves')

        # run manus executable
        self._run_manus_executable()

    def _run_manus_executable(self):
        # Start Manus executable to receive data
        os.startfile(r"C://Users//General User//Downloads//MANUS_Core_2.3.0_SDK//ManusSDK_v2.3.0//SDKClient//Output//x64\Debug//Client//SDKClient.exe")
        # os.startfile(r"c:\\Users\\rleeu\\Documents\\Github\\MANUS_Core_2.3.0.1_SDK\\ManusSDK_v2.3.0.1\\SDKClient\\Output\\x64\\Debug\\Client\\SDKClient.exe")
        time.sleep(5)

    def _initialize_api(self):
        # Check and print configuration for left hand robot
        if self.robot_config.config.robots.left_hand_robot.robot_connected:
            self.artus_api = self.robot_config.return_api(robot_cfg=self.robot_config.config.robots.left_hand_robot,logger=logger)
            
        # Check and print configuration for right hand robot
        if self.robot_config.config.robots.right_hand_robot.robot_connected:
            self.artus_api = self.robot_config.return_api(robot_cfg=self.robot_config.config.robots.right_hand_robot,logger=logger)

    def start_streaming(self):
        while True:
            try:
                self.hand_tracking_data.receive_joint_angles()
                joint_angles_left = self.hand_tracking_data.get_left_hand_joint_angles()
                joint_angles_right = self.hand_tracking_data.get_right_hand_joint_angles()
                self._send_joint_angles(joint_angles_left, joint_angles_right)
            except Exception as e:
                logging.error(e)
                pass

    def _send_joint_angles(self, joint_angles_left=None, joint_angles_right=None):
        if joint_angles_left is not None:
            if self.artus_api is not None:
                self.artus_api.set_joint_angles_by_list(joint_angles_list=joint_angles_left)
        else:
            logging.warning("No joint angles received for left hand")

        if joint_angles_right is not None:
            if self.artus_api is not None:
                self.artus_api.set_joint_angles_by_list(joint_angles_list=joint_angles_right)
        else:
            logging.warning("No joint angles received for right hand")
    


def both_hands_control_manus_gloves():
    manus_glove_joint_angles_streamer = ManusGloveController()
    manus_glove_joint_angles_streamer.start_streaming()


if __name__ == '__main__':
    both_hands_control_manus_gloves()

# "C:\Users\General User\AppData\Local\ov\pkg\isaac_sim-2022.2.1\python.bat" "c:/Users/General User/Desktop/github_files/Isaac_Sim_Work/Hand_Simulation/handTracking_simulation_robotControl/artus3d_joint_angles_streamer/joint_angles_streamer.py"