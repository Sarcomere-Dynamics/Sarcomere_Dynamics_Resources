import time
import numpy as np


import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
from Sarcomere_Dynamics_Resources.examples.Control.configuration.configuration import ArtusLiteConfig
from Sarcomere_Dynamics_Resources.examples.Control.ArtusLiteControl.ArtusLiteJointStreamer.artusLite_jointStreamer import ArtusLiteJointStreamer
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.hand_tracking_data import HandTrackingData
        
class ManusGloveController:
    def __init__(self):
        """
        Update the configuration file before running the controller
        """
        # Load robot configuration
        self.robot_config = ArtusLiteConfig()
        self.artusLite_jointStreamers = {'left': None, 'right': None}
        self._initialize_api()



        # Initialize hand tracking data
        self.hand_tracking_data = HandTrackingData(hand_tracking_method='manus_gloves')

                
        # run manus executable
        self._run_manus_executable()


    def _run_manus_executable(self):
        # Start Manus executable to receive data
        #  os.startfile(r"C://Users//General User//Downloads//MANUS_Core_2.3.0_SDK//ManusSDK_v2.3.0//SDKClient//Output//x64\Debug//Client//SDKClient.exe")
        os.startfile(r"C://Users//Gagan//Downloads//MANUS_Core_2.3.0_SDK//ManusSDK_v2.3.0//SDKClient//Output//x64//Debug//Client//SDKClient.exe")
        time.sleep(5)

    

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
    


def both_hands_control_manus_gloves():
    manus_glove_joint_angles_streamer = ManusGloveController()
    manus_glove_joint_angles_streamer.start_streaming()


if __name__ == '__main__':
    both_hands_control_manus_gloves()

# "C:\Users\General User\AppData\Local\ov\pkg\isaac_sim-2022.2.1\python.bat" "c:/Users/General User/Desktop/github_files/Isaac_Sim_Work/Hand_Simulation/handTracking_simulation_robotControl/artus3d_joint_angles_streamer/joint_angles_streamer.py"