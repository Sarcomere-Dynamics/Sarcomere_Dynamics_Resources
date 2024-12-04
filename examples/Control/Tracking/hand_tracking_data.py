
import re
import numpy as np
import threading
from collections import deque
import time

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
print("Root: ",PROJECT_ROOT)
# sys.path.append(PROJECT_ROOT)
# from RMD_Actuator_Control.RMD_Actuator_Control.Application.helpers.Path_Smoothener.moving_average import MultiMovingAverage

class HandTrackingData:
    def __init__(self,
                 hand_tracking_method='manus_gloves', # 'manus_gloves', 'gui'
                 port='65432'):
        self.hand_tracking_method = hand_tracking_method
        self.port = port
        self._setup_hand_tracking()

      
    
    
    def _setup_hand_tracking(self):
        """
        Set up the hand tracking method
        """
        if self.hand_tracking_method == 'manus_gloves':
            sys.path.append(PROJECT_ROOT)
            from Sarcomere_Dynamics_Resources.examples.Control.Tracking.manus_gloves_data.manus_gloves_hand_tracking_data import ManusGlovesHandTrackingData
            self.hand_tracking = ManusGlovesHandTrackingData(port=self.port)

        elif self.hand_tracking_method == 'gui':
            # print("Root: ",PROJECT_ROOT)
            sys.path.append(PROJECT_ROOT)
            from Sarcomere_Dynamics_Resources.examples.Control.Tracking.gui_data.artus_lite_gui_subscriber import ArtusLiteGUISubscriber
            self.hand_tracking = ArtusLiteGUISubscriber()

        else:
            raise ValueError('Invalid hand tracking method')
        

    def receive_joint_angles(self):
        """
        Receive joint angles from the hand tracking method
        """
        return self.hand_tracking.receive_joint_angles()
    
    def get_left_hand_joint_angles(self):
        return self.hand_tracking.get_left_hand_joint_angles()
    
    def get_right_hand_joint_angles(self):
        return self.hand_tracking.get_right_hand_joint_angles()
    


def test_hand_tracking_data():
    # hand_tracking_data = HandTrackingData(hand_tracking_method='gui')
    hand_tracking_data = HandTrackingData(hand_tracking_method='manus_gloves',
                                      port='65432')
    while True:
        try:
            joint_angles = hand_tracking_data.receive_joint_angles()
            print(joint_angles)
            time.sleep(0.5)
        except:
            pass

if __name__ == "__main__":
    test_hand_tracking_data()