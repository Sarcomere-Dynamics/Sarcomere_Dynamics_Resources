    
"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""


import re
import numpy as np
import threading
from collections import deque
import time


import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("Root: ",PROJECT_ROOT)

sys.path.append(str(PROJECT_ROOT))
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.manus_gloves_data.moving_average import MultiMovingAverage



class FingerTipData:
    
    def __init__(self, port='65432'):
        self.port = port
        self.order_of_fingers = ['index', 'middle', 'ring', 'pinky', 'thumb']
        self.decoded_data = {}
        
        self._initialize_tcp_server(port=port)
        self._setup_pose_transformer()
        
    
        
    def _initialize_tcp_server(self, port="65432"):
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.zmq_class.tcp_server import TCPServer

        self.tcp_server = TCPServer(port=int(port))
        self.tcp_server.create()
        
    def _setup_pose_transformer(self):
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.manus_finger_tip_data.finger_pose_transformer import FingerPoseTransformer
        self.pose_transformer = FingerPoseTransformer()
        
    def receive_fingerTip_data(self):
        raw_data = self.tcp_server.receive() # receive encoded data
        # print("1. Original Data: ", joint_angles)
        clean_data = self.parse_fingertip_data(raw_data) # parse the data
        
        if clean_data != {}:
            self.decoded_data = clean_data
        return clean_data


    def parse_fingertip_data(self, s: str) -> dict[int, tuple[tuple[float, float, float], tuple[float, float, float, float]]]:
        """
        Parse a string of the form:
        "... L_FingerTips[Node ID: 0 Pos=(0, 0, 0) Rot=(1, 0, 0, 0) Node ID: 1 Pos=(...) Rot=(...) ...]"
        into a dict mapping node_id -> (position_tuple, rotation_tuple).
        """
        if s is None:
            return {}
        # Normalize newlines (in case a number got split across lines)
        s = s.replace('\n', ' ')
        
        # Regex to capture Node ID, the three position values, and the four rotation values
        pattern = re.compile(
            r'Node ID:\s*(\d+)\s*'                  # capture node id
            r'Pos=\(\s*([^\)]+?)\s*\)\s*'           # capture everything inside Pos=(...)
            r'Rot=\(\s*([^\)]+?)\s*\)'              # capture everything inside Rot=(...)
        )
        
        result: dict[int, tuple[tuple[float, float, float], tuple[float, float, float, float]]] = {}
        for node_id_str, pos_str, rot_str in pattern.findall(s):
            node_id = int(node_id_str)
            # split on comma, strip whitespace, convert to float and round to 2 decimal places
            pos = tuple(round(float(x.strip()), 2) for x in pos_str.split(','))
            rot = tuple(round(float(x.strip()), 2) for x in rot_str.split(','))
            result[node_id] = (pos, rot)
        
        return result
    
    
    def get_finger_tip_data(self):
        """
        Get the finger tip data from the Manus gloves.
        Returns a dictionary with the following keys:
        'thumb', 'index', 'middle', 'ring', 'pinky'
        Each key maps to a tuple of the form (position, orientation).
        """
        self.receive_fingerTip_data()
        if self.decoded_data == {}:
            return {}
        absolute_poses = self.pose_transformer.compute_absolute_poses(self.decoded_data)
        return absolute_poses

# Example usage:
def main():
    fingertip_data = FingerTipData()
    node_id = 14
    
    MANUS_GLOVE_CONTROL = True
    # MANUS_GLOVE_CONTROL = False
    if MANUS_GLOVE_CONTROL:
        # Start Manus executable to receive data
        os.startfile(r"C://Users//General User//Downloads//MANUS_Core_2.3.0_SDK//ManusSDK_v2.3.0//SDKClient//Output//x64\Debug//Client//SDKClient.exe")
        time.sleep(2)
    current_time = time.perf_counter()
    while True:
        decoded = fingertip_data.receive_fingerTip_data()
        # print("Decoded Data Size: ",len(decoded))
        if decoded == {}:
            continue
        # print(node_id)
        # print("Pinky Tip Position: ", decoded[node_id][0], " Pinky Tip Orientation: ", decoded[node_id][1])
        
        # Print all nodes
                    
        print("\n=== Finger Tip Data for All Nodes ===")
        for node_id in sorted(decoded.keys()):
            position = decoded[node_id][0]
            orientation = decoded[node_id][1]
            print(f"Node {node_id:2d} - Position: {position}, Orientation: {orientation}")
        
        print("\n" + "="*40 + "\n")
        
        time.sleep(0.001)
        # if time.perf_counter() - current_time > 5:
        #     current_time = time.perf_counter()
        #     node_id += 1
        #     if node_id > 24:
        #         node_id = 0


def finger_tip_data():
    fingertip_data = FingerTipData()
    
    MANUS_GLOVE_CONTROL = True
    # MANUS_GLOVE_CONTROL = False
    if MANUS_GLOVE_CONTROL:
        # Start Manus executable to receive data
        os.startfile(r"C://Users//General User//Downloads//MANUS_Core_2.3.0_SDK//ManusSDK_v2.3.0//SDKClient//Output//x64\Debug//Client//SDKClient.exe")
        time.sleep(5)


    # sys.path.append(str(PROJECT_ROOT))
    # from Sarcomere_Dynamics_Resources.examples.Control.Tracking.manus_finger_tip_data.finger_pose_transformer import FingerPoseTransformer
    # transformer = FingerPoseTransformer()

    current_time = time.perf_counter()
    while True:
        # decoded = fingertip_data.receive_fingerTip_data()
        # # print("Decoded Data Size: ",len(decoded))
        absolute_poses = fingertip_data.get_finger_tip_data()
        if absolute_poses == {}:
            # print("No data received")
            continue

        # absolute_poses = fingertip_data.get_finger_tip_data()

        # print absolute_poses
        print("\n=== Finger Tip Data for All Fingers ===")
        print("Thumb Tip Position: ", absolute_poses['thumb'][0], " Thumb Tip Orientation: ", absolute_poses['thumb'][1])
        print("Index Tip Position: ", absolute_poses['index'][0], " Index Tip Orientation: ", absolute_poses['index'][1])
        print("Middle Tip Position: ", absolute_poses['middle'][0], " Middle Tip Orientation: ", absolute_poses['middle'][1])
        print("Ring Tip Position: ", absolute_poses['ring'][0], " Ring Tip Orientation: ", absolute_poses['ring'][1])
        print("Pinky Tip Position: ", absolute_poses['pinky'][0], " Pinky Tip Orientation: ", absolute_poses['pinky'][1])
        print("\n" + "="*40 + "\n")
    
if __name__ == "__main__":
    # main()
    finger_tip_data()
