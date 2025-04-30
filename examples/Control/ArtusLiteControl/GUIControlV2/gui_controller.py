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
import json

import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
from Sarcomere_Dynamics_Resources.examples.Control.configuration.configuration import ArtusLiteConfig
try:
    from ArtusAPI.artus_api import ArtusAPI  # Attempt to import the pip-installed version
    print("Using pip-installed version of ArtusAPI")
except ModuleNotFoundError:
    from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI  # Fallback to the local version
    print("Using local version of ArtusAPI")
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.hand_tracking_data import HandTrackingData


class ArtusGUIController:
    def __init__(self, feedbackPub_address="tcp://127.0.0.1:5555"):
        """
        Update the configuration file before running the controller
        """
        # Load robot configuration
        self.robot_config = ArtusLiteConfig()
        self.artusLite_jointStreamers = {'left': None, 'right': None}
        self._initialize_api()

        # Initialize hand tracking data (for getting joint angles from GUI)
        self.hand_tracking_data = HandTrackingData(hand_tracking_method='guiV2')

        # ZMQ publisher to publish force feedback to GUI
        self.zmq_publisher = None
        self._initialize_zmq_publisher(address=feedbackPub_address)

        # run gui executable
        # self._run_gui_executable()

    def _initialize_zmq_publisher(self,  address="tcp://127.0.0.1:5555"):
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.zmq_class.zmq_class import ZMQPublisher
        self.zmq_publisher = ZMQPublisher(address=address)

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

    # -------------------------------------------------------
    # Stream joint angles from hand tracking GUI to Artus API 
    # -------------------------------------------------------
    def start_streaming(self):
        current_time_feedback = time.perf_counter()
        current_time_command = time.perf_counter()
        publishing_delay = 0.001
        while True:
            try:
                if time.perf_counter() - current_time_command > publishing_delay:
                    current_time_command = time.perf_counter()
                    # print("1")
                    # print("Receiving joint angles from GUI")
                    self.hand_tracking_data.receive_joint_angles()
                    # print("2")
                    joint_angles_left = self.hand_tracking_data.get_left_hand_joint_angles()
                    joint_angles_right = self.hand_tracking_data.get_right_hand_joint_angles()
                    # print("3")
                    # print("Sending joint angles to Artus Robot")
                    self._send_joint_angles(joint_angles_left, joint_angles_right)
                    data = self._receive_force_feedback()
                if data is not None:
                    pass
                # print("4")
                if time.perf_counter() - current_time_feedback > publishing_delay:
                    current_time_feedback = time.perf_counter()
                    self.publish_force_feedback(data)

            except Exception as e:
                print(e)
                pass
    def _send_joint_angles(self, joint_angles_left=None, joint_angles_right=None):
        if joint_angles_left is not None:
            print("Joint Angles Left: ", joint_angles_left)
            if self.artusLite_jointStreamers['left'] is not None:
                self.artusLite_jointStreamers['left'].stream_joint_angles(joint_angles=joint_angles_left)
        else:
            print("No joint angles received for left hand")

        if joint_angles_right is not None:
            print("Joint Angles Right: ", joint_angles_right)
            if self.artusLite_jointStreamers['right'] is not None:
                self.artusLite_jointStreamers['right'].stream_joint_angles(joint_angles=joint_angles_right)
        else:
            print("No joint angles received for right hand")



    # -------------------------------------------------------
    # Publish force feedback to GUI
    # -------------------------------------------------------
    def publish_force_feedback(self,data):
        """
        This function:
            - receives force feedback data using artusAPI
            - publishes force feedback to a port which GUI has subscribed to

        GUI uses this data to display force feedback
        """
        # while True:
        print("1: Receiving force feedback")
        # data = self._receive_force_feedback()
        print("2: Publishing force feedback")
        # fix the order for the GUI
        if data is not None:
            data = {"data": [data[0], data[4], data[7], data[10], data[13], # joint 1s
                            data[1], data[5], data[8], data[11], data[14], # joint 2s
                            data[2], data[6], data[9], data[12], data[15],  # joint 3s
                            data[3]]}                                       # joint 4 (thumb)
            # data = {"data": data}
            # print(data)
            self.zmq_publisher.send(topic="ForceFeedback",
                            message=json.dumps(data))
            # self.zmq_publisher.send(message=json.dumps(data))
            
            print("3: Published force feedback")

    def _receive_force_feedback(self):
        """
        We can only control one hand at a time when doing both control and feedback
        """
        if self.artusLite_jointStreamers['left'] is not None:
            force_feedback_left = self.artusLite_jointStreamers['left'].receive_force_feedback()
            # print("Force Feedback Left: ", force_feedback_left)
            return force_feedback_left

        if self.artusLite_jointStreamers['right'] is not None:
            force_feedback_right = self.artusLite_jointStreamers['right'].receive_force_feedback()
            # print("Force Feedback Right: ", force_feedback_right)
            return force_feedback_right
        else:
            return None


# def test_artus_gui_controller():
#     artus_gui_controller = ArtusGUIController()
#     artus_gui_controller.start_streaming()


# run streaming joint angles and force feedback in parallel
def main():
    artus_gui_controller = ArtusGUIController()
    artus_gui_controller.start_streaming()


if __name__ == "__main__":
    # test_artus_gui_controller()
    main()