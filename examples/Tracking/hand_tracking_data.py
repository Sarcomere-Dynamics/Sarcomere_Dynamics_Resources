"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Top-level hand tracking data facade used by the application logic.

Wraps a specific hand tracking backend (e.g. Manus gloves) behind a single
interface for retrieving per-hand joint angles.
"""

import re
import numpy as np
import threading
from collections import deque
import time

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Root: ",PROJECT_ROOT)
# sys.path.append(PROJECT_ROOT)
# from RMD_Actuator_Control.RMD_Actuator_Control.Application.helpers.Path_Smoothener.moving_average import MultiMovingAverage

class HandTrackingData:
    """Receives joint angles from a configurable hand tracking backend.

    Acts as a thin facade in front of the concrete tracking implementation
    (currently only Manus gloves) so the application logic can request joint
    angles without depending on the backend's specifics.
    """
    def __init__(self,
                 hand_tracking_method='manus_gloves', # 'manus_gloves', 'gui'
                 port='65432'):
        """Initializes the facade and sets up the configured tracking backend.

        Args:
            hand_tracking_method: Name of the tracking backend to use.
                Currently only 'manus_gloves' is supported.
            port: TCP port used by the underlying tracking backend to
                receive streamed data.

        Raises:
            ValueError: If hand_tracking_method is not a supported backend.
        """
        self.hand_tracking_method = hand_tracking_method
        self.port = port
        self._setup_hand_tracking()




    def _setup_hand_tracking(self):
        """Instantiates the concrete hand tracking backend.

        Raises:
            ValueError: If self.hand_tracking_method is not a supported
                backend.
        """
        if self.hand_tracking_method == 'manus_gloves':
            sys.path.append(PROJECT_ROOT)
            from examples.Tracking.manus_gloves_data.manus_gloves_hand_tracking_data import ManusGlovesHandTrackingData
            self.hand_tracking = ManusGlovesHandTrackingData(port=self.port)
        else:
            raise ValueError('Invalid hand tracking method')
        

    def receive_joint_angles(self):
        """Receives and decodes the latest joint angle data from the backend.

        Returns:
            The raw or decoded joint angle data returned by the configured
            hand tracking backend's receive_joint_angles method.
        """
        return self.hand_tracking.receive_joint_angles()

    def get_left_hand_joint_angles(self):
        """Gets the most recently decoded left-hand joint angles.

        Returns:
            The left-hand joint angles as maintained by the underlying
            hand tracking backend.
        """
        return self.hand_tracking.get_left_hand_joint_angles()

    def get_right_hand_joint_angles(self):
        """Gets the most recently decoded right-hand joint angles.

        Returns:
            The right-hand joint angles as maintained by the underlying
            hand tracking backend.
        """
        return self.hand_tracking.get_right_hand_joint_angles()



def test_hand_tracking_data():
    """Manually exercises HandTrackingData by polling and printing joint angles."""
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