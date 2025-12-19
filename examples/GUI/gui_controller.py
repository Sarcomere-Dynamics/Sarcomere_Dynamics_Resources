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
import logging
import os
import sys

# Configure logging only if it hasn't been configured yet
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.propagate = True  # Ensure logs propagate to parent loggers

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger.info(f"Project Root: {PROJECT_ROOT}")
sys.path.append(PROJECT_ROOT)
from examples.config.configuration import ArtusConfig
from examples.Tracking.zmq_class.zmq_class import ZMQPublisher, ZMQSubscriber
from ArtusAPI.artus_api_new import ArtusAPI_V2
from ArtusAPI.artus_api import ArtusAPI


class ArtusGUIController:
    def __init__(self, feedbackPub_address="tcp://127.0.0.1:5555", jointSub_address="tcp://127.0.0.1:5556"):
        """
        Artus GUI Controller backend interaction that manages data IO to Artus API
        Interacts with ZMQ to and from the GUI Application
        Sends joint feedback to ZMQ Publisher
        Receives joint angles from ZMQ Subscriber
        """

        self.zmq_publisher = ZMQPublisher(address=feedbackPub_address)
        self.zmq_subscriber = ZMQSubscriber(address=jointSub_address, topics=["Target"])
        # Initialize logger for this instance
        self.logger = logging.getLogger(__name__)
        self.logger.propagate = True

        # sensor feedback type
        self.sensor_feedback = 'actuator'
        
        # Load robot configuration
        self.robot_config = ArtusConfig()
        self._initialize_api()


    def _initialize_api(self):
        """
        Initialize a single instance of the API class 
        The GUI can only control one robot at a time
        """
        self.artus_api = self.robot_config.get_api(logger=self.logger)

        # connect wake and calibrate the robot
        self.artus_api.connect()
        # wake if set in config
        if self.robot_config.get_robot_wake_up(hand_type=self.artus_api._robot_handler.hand_type):
            self.artus_api.wake_up()

        # calibrate if set in config
        if self.robot_config.get_robot_calibrate(hand_type=self.artus_api._robot_handler.hand_type):
            self.artus_api.calibrate()

        # test robot
        # self.artus_api = ArtusAPI_V2(robot_type='artus_talos',
        #                         communication_method='RS485_RTU',
        #                         communication_channel_identifier='/dev/ttyUSB0',
        #                         communication_frequency=20,
        #                         logger=self.logger)
        # self.logger.info("Robot connected")

    def _send_joint_angles(self,joint_angles:dict=None):
        """
        Send dict of joint angles
        """
        if joint_angles is not None:
            self.artus_api.set_joint_angles(joint_angles=joint_angles)
        else:
            self.logger.error("No joint angles received")
            return

    def _publish_feedback(self,feedback:dict=None):
        """
        Get all available feedback data from the robot and publish to the GUI
        """

        # Only include specific fields from each joint in the feedback
        allowed_fields = ["index", "feedback_angle", "feedback_force", "feedback_velocity", "feedback_current"]

        hand_joints_serializable = {
            joint_name: {field: getattr(joint, field, None) for field in allowed_fields}
            for joint_name, joint in self.artus_api._robot_handler.robot.hand_joints.items()
        }
        self.zmq_publisher.send(topic="Feedback",message=json.dumps(hand_joints_serializable))
        self.logger.info(f"Published feedback to ZMQ")


    def _receive_feedback(self):
        """
        Receive feedback data from the robot
        """
        try:
            # backward compatibility with v1 api
            if 'lite' in str(self.artus_api._robot_handler.robot_type):
                self.artus_api.get_joint_angles()
            else:
                self.artus_api.get_hand_feedback_data()
        except Exception as e:
            self.logger.error(f"Error in _receive_feedback: {e}")
            return None
        return None

    def _receive_joint_anglesZMQ(self):
        """
        Receive joint angles from the GUI Application
        """
        joint_angles = self.zmq_subscriber.receive()
        if joint_angles is not None:
            joint_angles = json.loads(joint_angles)
            for key,value in joint_angles.items():
                setattr(self.artus_api._robot_handler.robot.hand_joints[key], 'target_angle', int(value))
            return joint_angles
        else:
            self.logger.error("No joint angles received")
            return None

    def start_streaming(self):
        """
        Start streaming joint angles and feedback data
        """
        while True:
            try:
                if self._receive_joint_anglesZMQ() is not None:
                    None
                    # self._send_joint_angles(joint_angles=self.artus_api._robot_handler.robot.hand_joints)

                time.sleep(0.01)

                self._receive_feedback()
                self._publish_feedback(feedback=self.artus_api._robot_handler.robot.hand_joints)
                

                time.sleep(0.01)
            except Exception as e:
                self.logger.error(f"Error in start_streaming: {e}")
                continue

if __name__ == "__main__":
    gui_controller = ArtusGUIController()
    gui_controller.start_streaming()