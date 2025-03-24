"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import numpy as np
import time
import json

import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)


class FeedbackDataPublisher:
    """
    (Not used in the main application logic)
    """

    def __init__(self, address="tcp://127.0.0.1:5555"):
        self._initialize_zmq_publisher(address=address)


    def _initialize_zmq_publisher(self,  address="tcp://127.0.0.1:5555"):
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.zmq_class.zmq_class import ZMQPublisher
        self.zmq_publisher = ZMQPublisher(address=address)


    def send_feedback_data(self, data):
        """
        Send feedback data to the ZeroMQ publisher
        # """
        self.zmq_publisher.send(topic="GUI",
                                message=json.dumps(data))
        # self.zmq_publisher.send(topic="GUI",
        #                         message="Hello World")
        
def test_data_generator():
    data = np.random.rand(16).tolist()
    # print("Data Generated: ", data)
    return data
        

def main():
    feedback_data_publisher = FeedbackDataPublisher(address="tcp://127.0.0.1:5555")
    while True:
        data = test_data_generator()
        # convert data to dict
        data = {"data": data}
        feedback_data_publisher.send_feedback_data(data)
        print("Data Sent: ", data)
        time.sleep(1)


if __name__ == '__main__':
    main()