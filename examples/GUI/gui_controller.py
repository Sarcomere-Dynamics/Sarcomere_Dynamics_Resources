"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

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


class ArtusGUIController:
    """Backend bridge between the ARTUS API and a ZMQ-connected GUI application.

    Manages data IO to the ArtusAPI: publishes joint/force-sensor feedback
    over a ZMQ publisher socket and receives target joint angles from a
    ZMQ subscriber socket.
    """

    def __init__(self, feedbackPub_address="tcp://127.0.0.1:5555", jointSub_address="tcp://127.0.0.1:5556"):
        """Sets up ZMQ sockets and initializes the ARTUS API connection.

        Args:
            feedbackPub_address: ZMQ address to publish feedback data on.
            jointSub_address: ZMQ address to subscribe to for incoming
                target joint angles (topic "Target").
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
        """Initializes a single ArtusAPI instance for the configured robot.

        The GUI can only control one robot at a time. Also fetches the
        initial robot status, and wakes up / calibrates the robot if those
        options are enabled in the configuration.
        """
        self.artus_api = self.robot_config.get_api(logger=self.logger)

        # always try to get data first 
        logger.info(self.artus_api.get_robot_status())

        
        # wake if set in config
        if self.robot_config.get_robot_wake_up(hand_type=self.artus_api._robot_handler.hand_type):
            self.artus_api.wake_up()
            time.sleep(0.5)

        # calibrate if set in config
        if self.robot_config.get_robot_calibrate(hand_type=self.artus_api._robot_handler.hand_type):
            self.artus_api.calibrate()
            time.sleep(0.5)
        # test robot
        # self.artus_api = ArtusAPI_V2(robot_type='artus_talos',
        #                         communication_method='RS485_RTU',
        #                         communication_channel_identifier='/dev/ttyUSB0',
        #                         communication_frequency=20,
        #                         logger=self.logger)
        # self.logger.info("Robot connected")

    def _send_joint_angles(self,joint_angles:dict=None):
        """Sends a dict of target joint angles to the robot.

        Args:
            joint_angles: Mapping of joint name/index to target angle
                data, as expected by ArtusAPI_V2.set_joint_angles. If
                None, logs an error and returns without sending anything.
        """
        if joint_angles is not None:
            self.artus_api.set_joint_angles(joint_angles=joint_angles)
        else:
            self.logger.error("No joint angles received")
            return

    def _publish_feedback(self,feedback:dict=None):
        """Publishes the robot's current feedback data to the GUI over ZMQ.

        Reads joint feedback (index, angle, force, velocity, current) and,
        when available, force sensor data directly from
        self.artus_api._robot_handler.robot, then publishes the combined
        payload as JSON on the "Feedback" ZMQ topic.

        Args:
            feedback: Accepted for interface compatibility but not used;
                feedback data is always read from self.artus_api directly.
        """

        # Only include specific fields from each joint in the feedback
        allowed_fields = ["index", "feedback_angle", "feedback_force", "feedback_velocity", "feedback_current"]

        robot = getattr(self.artus_api._robot_handler, "robot", None)
        hand_joints_serializable = {
            joint_name: {field: getattr(joint, field, None) for field in allowed_fields}
            for joint_name, joint in robot.hand_joints.items()
        }

        # Add force sensor feedback when present on the robot (e.g., Talos)
        force_sensor_payload = None
        force_sensors = getattr(robot, "force_sensors", None)
        if force_sensors:
            force_sensor_payload = {
                sensor_name: {
                    "x": getattr(sensor_info.get("data"), "x", None) if sensor_info else None,
                    "y": getattr(sensor_info.get("data"), "y", None) if sensor_info else None,
                    "z": getattr(sensor_info.get("data"), "z", None) if sensor_info else None,
                }
                for sensor_name, sensor_info in force_sensors.items()
            }

        payload = hand_joints_serializable.copy()
        if force_sensor_payload:
            payload["force_sensors"] = force_sensor_payload

        self.zmq_publisher.send(topic="Feedback",message=json.dumps(payload))
        self.logger.info(f"Published feedback to ZMQ")


    def _receive_feedback(self):
        """Triggers a feedback read from the robot for backward compatibility.

        Returns:
            None: Always returns None; the actual feedback is stored on
            self.artus_api's robot handler and read separately by
            _publish_feedback. Errors are logged and swallowed.
        """
        try:
            # backward compatibility with v1 api
            self.artus_api.get_hand_feedback_data()
        except Exception as e:
            self.logger.error(f"Error in _receive_feedback: {e}")
            return None
        return None

    def _receive_joint_anglesZMQ(self):
        """Receives target joint angles from the GUI over the ZMQ subscriber.

        Reads a JSON package containing joint_values, force, and speed,
        and reshapes it into the {joint_name: {target_angle, target_force,
        target_velocity}} format expected by ArtusAPI.

        Returns:
            dict | None: Mapping of joint name to target angle/force/
            velocity dict, or None if no package was available (logs an
            error in that case).
        """
        package = self.zmq_subscriber.receive()
        if package is not None:
            package = json.loads(package)
            joint_angles = package['joint_values']
            force = package['force']
            speed = package['speed']
            
            # joint angles with key and float value but I want key: {'target_angle': int(value)}
            joint_angles = {key: {'target_angle': int(value)} for key,value in joint_angles.items()}

            for key,value in joint_angles.items():
                joint_angles[key]['target_force'] = force
                joint_angles[key]['target_velocity'] = speed

            return joint_angles
        else:
            self.logger.error("No joint angles received")
            return None

    def start_streaming(self):
        """Runs the main loop forwarding joint commands and feedback via ZMQ.

        Continuously receives target joint angles from the GUI and sends
        them to the robot, then reads and publishes feedback data back to
        the GUI. Runs indefinitely; exceptions in a single iteration are
        logged and the loop continues.
        """
        while True:
            try:
                joint_angles = self._receive_joint_anglesZMQ()
                if joint_angles is not None:
                    self._send_joint_angles(joint_angles=joint_angles)

                time.sleep(0.02)

                self._receive_feedback()
                self._publish_feedback(feedback=self.artus_api._robot_handler.robot.hand_joints)
                

                # time.sleep(0.02)
            except Exception as e:
                self.logger.error(f"Error in start_streaming: {e}")
                continue

if __name__ == "__main__":
    gui_controller = ArtusGUIController()
    gui_controller.start_streaming()