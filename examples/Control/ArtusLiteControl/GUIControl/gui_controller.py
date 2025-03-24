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

import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
from Sarcomere_Dynamics_Resources.examples.Control.configuration.configuration import ArtusLiteConfig
from Sarcomere_Dynamics_Resources.examples.Control.ArtusLiteControl.ArtusLiteJointStreamer.artusLite_jointStreamer import ArtusLiteJointStreamer
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.hand_tracking_data import HandTrackingData


class ArtusGUIController:
    def __init__(self):
        """
        Update the configuration file before running the controller
        """
        # Load robot configuration
        self.robot_config = ArtusLiteConfig()
        self.artusLite_jointStreamers = {'left': None, 'right': None}
        self._initialize_api()

        # Initialize hand tracking data
        self.hand_tracking_data = HandTrackingData(hand_tracking_method='gui')

        # run gui executable
        # self._run_gui_executable()

    def _run_gui_executable(self):
        # # Start GUI executable to receive data
        # os.startfile(r"C:\Users\yizho\Documents\Sarcomere\Artus\ArtusLite\ArtusLite\ArtusLite\bin\Debug\ArtusLite.exe")
        # time.sleep(5)
        pass

    def _initialize_api(self):
        # Check and print configuration for left hand robot
        if self.robot_config.config.robots.left_hand_robot.robot_connected:
            self.artusLite_jointStreamers['left'] = ArtusLiteJointStreamer(communication_method=self.robot_config.config.robots.left_hand_robot.communication_method,
                                                                            communication_channel_identifier=self.robot_config.config.robots.left_hand_robot.communication_channel_identifier,
                                                                            hand_type='left',
                                                                            reset_on_start=self.robot_config.config.robots.left_hand_robot.reset_on_start,
                                                                            streaming_frequency=self.robot_config.config.robots.left_hand_robot.streaming_frequency,
                                                                            start_robot=self.robot_config.config.robots.left_hand_robot.start_robot,
                                                                            calibrate=self.robot_config.config.robots.left_hand_robot.calibrate,
                                                                            robot_connected=self.robot_config.config.robots.left_hand_robot.robot_connected)
            
        # Check and print configuration for right hand robot
        if self.robot_config.config.robots.right_hand_robot.robot_connected:
            self.artusLite_jointStreamers['right'] = ArtusLiteJointStreamer(communication_method=self.robot_config.config.robots.right_hand_robot.communication_method,
                                                                            communication_channel_identifier=self.robot_config.config.robots.right_hand_robot.communication_channel_identifier,
                                                                            hand_type='right',
                                                                            reset_on_start=self.robot_config.config.robots.right_hand_robot.reset_on_start,
                                                                            streaming_frequency=self.robot_config.config.robots.right_hand_robot.streaming_frequency,
                                                                            start_robot=self.robot_config.config.robots.right_hand_robot.start_robot,
                                                                            calibrate=self.robot_config.config.robots.right_hand_robot.calibrate,
                                                                            robot_connected=self.robot_config.config.robots.right_hand_robot.robot_connected)

        

    def start_streaming(self):
        while True:
            try:
                print("1")
                self.hand_tracking_data.receive_joint_angles()
                print("2")
                joint_angles_left = self.hand_tracking_data.get_left_hand_joint_angles()
                joint_angles_right = self.hand_tracking_data.get_right_hand_joint_angles()
                print("3")
                self._send_joint_angles(joint_angles_left, joint_angles_right)
                print("4")
            except Exception as e:
                print(e)
                pass

    def _send_joint_angles(self, joint_angles_left=None, joint_angles_right=None):
        if joint_angles_left is not None:
            if self.artusLite_jointStreamers['left'] is not None:
                self.artusLite_jointStreamers['left'].stream_joint_angles(joint_angles=joint_angles_left)
        else:
            print("No joint angles received for left hand")

        if joint_angles_right is not None:
            if self.artusLite_jointStreamers['right'] is not None:
                self.artusLite_jointStreamers['right'].stream_joint_angles(joint_angles=joint_angles_right)
        else:
            print("No joint angles received for right hand")



def test_artus_gui_controller():
    artus_gui_controller = ArtusGUIController()
    artus_gui_controller.start_streaming()


if __name__ == "__main__":
    test_artus_gui_controller()