"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
import numpy as np
import json


import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("PROJECT_ROOT: ", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.gui_data_v2.feedback_visualization.display_class import RealTimePlots

class RealTimePlotsZMQ(RealTimePlots):
    """
    Same as RealTimePlots but with ZeroMQ subscriber for receiving feedback data from the robot
    """
    def __init__(self, rows = 4, cols = 5, win = None, zmq_feedback_subPort = 5555):
        super().__init__(rows, cols, win)
        self.zmq_feedback_subPort = zmq_feedback_subPort
        address = "tcp://127.0.0.1:" + str(self.zmq_feedback_subPort)
        self._initialize_zmq_subscriber(address=address)
        self.joint_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]


    def _initialize_zmq_subscriber(self, address="tcp://127.0.0.1:5555"):
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.zmq_class.zmq_class import ZMQSubscriber
        self.zmq_subscriber = ZMQSubscriber(address=address)


    # override _get_data
    def _get_data(self):
        """
        Get the data from the ZeroMQ subscriber
        """
        self.receive_joint_data()
        data = self.get_joint_data()
        print(data)
        return data


    def receive_joint_data(self):
        joint_data = self.zmq_subscriber.receive()
        print("Joint Data Received: ", joint_data)
        if joint_data == None:
            return None
        print(joint_data)
        # Parse the JSON data
        joint_data = json.loads(joint_data)
        self.joint_data = joint_data['data']
        return joint_data
    
    def get_joint_data(self):
        return self.joint_data
    


def main():
        # Set up the Qt application
    app = pg.mkQApp()
    real_time_plots = RealTimePlotsZMQ(rows = 4, cols = 5, win = None, zmq_feedback_subPort = 5555)
    app.exec_()

if __name__ == '__main__':
    main()



