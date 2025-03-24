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
import re
import json
import ast


import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("Root: ",PROJECT_ROOT)

class ArtusLiteGUISubscriber:
    def __init__(self, address="tcp://127.0.0.1:5556"):
                 
        self._initialize_zmq_subscriber(address=address)

        self.joint_angles_left = None
        self.joint_angles_right = None

    def _initialize_zmq_subscriber(self, address="tcp://127.0.0.1:5556"):
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.zmq_class.zmq_class import ZMQSubscriber
        self.zmq_subscriber = ZMQSubscriber(address=address)


    def receive_joint_angles(self):

        joint_angles = self.zmq_subscriber.receive()
        if joint_angles == None:
            return None
        # print(joint_angles)
        # data = json.loads(joint_angles)
        # print(data["right_hand"])
        # print("Joint Angles Received: ", joint_angles)
        self._joint_angles_gui_to_joint_streamer(joint_angles)
        return joint_angles
    
    def get_left_hand_joint_angles(self):
        return self.joint_angles_left
    def get_right_hand_joint_angles(self):
        return self.joint_angles_right

    def _joint_angles_gui_to_joint_streamer(self, data):
        """
        Convert joint angles from GUI to Artus API format
        """
        # Parse the JSON data
        data = json.loads(data)
        # Extract the joint angles in the specified order
        self.joint_angles_right = [
                                    # Thumb joints first
                                    data["right_hand"]["right hand_thumb_1"],
                                    data["right_hand"]["right hand_thumb_2"],
                                    data["right_hand"]["right hand_thumb_3"],
                                    data["right_hand"]["right hand_thumb_4"],

                                    # Index finger joints
                                    data["right_hand"]["right hand_index_1"],
                                    data["right_hand"]["right hand_index_2"],
                                    data["right_hand"]["right hand_index_3"],

                                    # Middle finger joints
                                    data["right_hand"]["right hand_middle_1"],
                                    data["right_hand"]["right hand_middle_2"],
                                    data["right_hand"]["right hand_middle_3"],

                                    # Ring finger joints
                                    data["right_hand"]["right hand_ring_1"],
                                    data["right_hand"]["right hand_ring_2"],
                                    data["right_hand"]["right hand_ring_3"],

                                    # Pinky finger joints
                                    data["right_hand"]["right hand_pinky_1"],
                                    data["right_hand"]["right hand_pinky_2"],
                                    data["right_hand"]["right hand_pinky_3"]
                                ]
        # Repeat for the left hand

        self.joint_angles_left = [
                                    # Thumb joints
                                    data["left_hand"]["left hand_thumb_1"],
                                    data["left_hand"]["left hand_thumb_2"],
                                    data["left_hand"]["left hand_thumb_3"],
                                    data["left_hand"]["left hand_thumb_4"],

                                    # Index finger joints
                                    data["left_hand"]["left hand_index_1"],
                                    data["left_hand"]["left hand_index_2"],
                                    data["left_hand"]["left hand_index_3"],

                                    # Middle finger joints
                                    data["left_hand"]["left hand_middle_1"],
                                    data["left_hand"]["left hand_middle_2"],
                                    data["left_hand"]["left hand_middle_3"],

                                    # Ring finger joints
                                    data["left_hand"]["left hand_ring_1"],
                                    data["left_hand"]["left hand_ring_2"],
                                    data["left_hand"]["left hand_ring_3"],

                                    # Pinky finger joints
                                    data["left_hand"]["left hand_pinky_1"],
                                    data["left_hand"]["left hand_pinky_2"],
                                    data["left_hand"]["left hand_pinky_3"]
                                ]

        return self.joint_angles_left, self.joint_angles_right



def test_receive_joint_values():
    artus_lite_gui_subscriber = ArtusLiteGUISubscriber()
    while True:
        joint_values = artus_lite_gui_subscriber.receive_joint_angles()
        if joint_values == None:
            continue
        # print(joint_values)
        print("Left Hand: ", artus_lite_gui_subscriber.joint_angles_left)
        print("Right Hand: ", artus_lite_gui_subscriber.joint_angles_right)
        time.sleep(0.1)


if __name__ == "__main__":
    test_receive_joint_values()