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
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Root: ",PROJECT_ROOT)

class ArtusLiteGUISubscriber:
    def __init__(self, address="tcp://127.0.0.1:5556"):
                 
        self._initialize_zmq_subscriber(address=address)
        self.joint_angles = None

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
    
    def get_joint_angles(self):
        return self.joint_angles

    def _joint_angles_gui_to_joint_streamer(self, data):
        """
        Convert joint angles from GUI to Artus API format
        """
        # Parse the JSON data
        data = json.loads(data)
        # Extract the joint angles in the specified order
        self.joint_angles = [
                                    # Thumb joints first
                                    data["Thumb_1"],
                                    data["Thumb_2"],
                                    data["Thumb_3"],
                                    data["Thumb_4"],
                                    # Index finger joints next
                                    data["Index_1"],
                                    data["Index_2"],
                                    data["Index_3"],
                                    # Middle finger joints next
                                    data["Middle_1"],
                                    data["Middle_2"],
                                    data["Middle_3"],
                                    # Ring finger joints next
                                    data["Ring_1"],
                                    data["Ring_2"],
                                    data["Ring_3"],
                                    # Pinky finger joints next
                                    data["Pinky_1"],
                                    data["Pinky_2"],
                                    data["Pinky_3"]
                                ]

        return self.joint_angles


def test_receive_joint_values():
    artus_lite_gui_subscriber = ArtusLiteGUISubscriber()
    while True:
        joint_values = artus_lite_gui_subscriber.receive_joint_angles()
        if joint_values == None:
            continue
        # print(joint_values)
        print("Joint Angles: ", artus_lite_gui_subscriber.joint_angles)
        time.sleep(0.1)


if __name__ == "__main__":
    test_receive_joint_values()