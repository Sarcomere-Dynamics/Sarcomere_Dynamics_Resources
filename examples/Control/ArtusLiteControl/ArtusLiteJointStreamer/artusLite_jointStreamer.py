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
import os
import sys
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
sys.path.append(PROJECT_ROOT)

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.propagate = True  # Ensure logs propagate to parent loggers

# from artus_3d_api.Artus3DAPI import Artus3DAPI
# sys.path.append(PROJECT_ROOT)
try:
    from ArtusAPI.artus_api import ArtusAPI  # Attempt to import the pip-installed version
    logger.info("Using pip-installed version of ArtusAPI")
except ModuleNotFoundError:
    from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI  # Fallback to the local version
    logger.info("Using local version of ArtusAPI")

from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api_new import ArtusAPI_New

# 1, 6, 8, 4
class ArtusLiteJointStreamer:

    def __init__(self,                 
                communication_method= 'UART',
                robot_type='artus_lite',
                communication_channel_identifier='COM7',
                hand_type = 'left',
                reset_on_start = 0,
                
                streaming_frequency = 30, # data/seconds
                start_robot=True,
                calibrate= False,
                robot_connected=True,
                logger=None):
        
        # Use the passed logger or create a new one that inherits from the root logger
        self.logger = logger if logger else logging.getLogger(__name__)
        self.logger.propagate = True  # Ensure logs propagate to parent loggers
        if robot_type == 'artus_lite':
            self.artusLite_api = ArtusAPI(communication_method=communication_method,
                                        communication_channel_identifier=communication_channel_identifier,
                                        robot_type=robot_type,
                                        hand_type=hand_type,
                                        reset_on_start=reset_on_start,
                                        communication_frequency = streaming_frequency,
                                        stream = True,
                                        logger=self.logger)
        else:
            self.artusLite_api = ArtusAPI_New(communication_method=communication_method,
                                        communication_channel_identifier=communication_channel_identifier,
                                        robot_type=robot_type,
                                        hand_type=hand_type,
                                        communication_frequency = streaming_frequency,
                                        logger=self.logger)
                                    
        
        self.communication_channel_identifier = communication_channel_identifier
        self.robot_start = start_robot
        self.calibrate = calibrate
        # Initialize Artus Lite API
        if robot_connected:
            self._initialize_api()
        

        self.streaming_frequency  = streaming_frequency
        self.previous_time = 0 
  
      
    def _initialize_api(self):
        self.artusLite_api.connect()
        time.sleep(1)
        if self.robot_start:
            self.artusLite_api.wake_up()
            # time.sleep(2)
        if self.calibrate:
            self.artusLite_api.calibrate()
        # time.sleep(2)
    
    def _disconnect_api(self):
        self.artusLite_api.set_home_position()
        time.sleep(1)
        self.artusLite_api.sleep()
        self.artusLite_api.disconnect()
        self.logger.info("Disconnected from Artus Lite API")

    def _go_to_zero_position(self):
        self.artusLite_api.set_home_position()
        

    def stream_joint_angles(self, joint_angles = []):
         # make sure all ints
        hand_joints = {0:'0',1:'0',2:'0',3:'0',4:'0',5:'0',6:'0',7:'0',8:'0',9:'0',10:'0',11:'0',12:'0',13:'0',14:'0',15:'0'}
        joint_angles = [int(i) for i in joint_angles]
        
        for i in range(16):
            joint = {'index':i, 'target_angle': joint_angles[i], 'velocity' : 60}
            hand_joints[i] = joint
            
        # set joint angles
        # if self._check_streaming_rate():
            # print(f"Sending {self.communication_channel_identifier}...{hand_joints}")
            # print(f'******************************** hand joints : ************************************************/n {hand_joints}')
            # print(f'hand joints sent to hand: {hand_joints[0:4]}')
        self.artusLite_api.set_joint_angles(joint_angles=hand_joints)
            # return joint_angles
        # else:
            # print(f'missed {self.communication_channel_identifier}')
            # return None
        
    def _check_streaming_rate(self):
        """
        This function checks if the streaming rate is within the specified streaming frequency.
        """
        self.current_time = time.perf_counter()
        time_difference = self.current_time - self.previous_time
        
        # check if the time difference is greater than the streaming frequency
        if time_difference > 1/self.streaming_frequency:
            # print("time difference: ", time_difference)
            # print(f"Streaming rate for {arm} arm is correct")
            self.previous_time = self.current_time
            return True
        # print("Time difference: ", time_difference)
        return False
    
    def get_joint_feedback_force(self):
        """
        This function returns the feedback force of all the joints in the hand, in a joint list of integers
        """
        return [joint.feedback_force for joint in self.artusLite_api._robot_handler.robot.hand_joints.values()]

    def receive_force_feedback(self):
        joint_angles = self.artusLite_api.get_streamed_joint_angles()
  
        if joint_angles is None:
            self.logger.debug("No joint angles received")
            return  # Exit early if there's no data to process
        
        self.logger.info(f"Joint Angles: {joint_angles}")
        
        position = []
        current = []
        temperature = []

        for i in range(len(self.artusLite_api._robot_handler.robot.joint_names)):
            name = self.artusLite_api._robot_handler.robot.joint_names[i]
            position.append(self.artusLite_api._robot_handler.robot.hand_joints[name].feedback_angle)
            if self.artusLite_api._robot_handler.robot_type == 'artus_lite':
                current.append(self.artusLite_api._robot_handler.robot.hand_joints[name].feedback_current)
                temperature.append(self.artusLite_api._robot_handler.robot.hand_joints[name].feedback_temperature)
    
        if self.artusLite_api._robot_handler.robot_type == 'artus_lite_plus':
            sensor_names_local = ['thumb', 'index', 'middle', 'ring', 'pinky']

            for i in range(len(sensor_names_local)):
                name = sensor_names_local[i]
                current.append(round(self.artusLite_api._robot_handler.robot.force_sensors[name]['data'].x,2))
                current.append(round(self.artusLite_api._robot_handler.robot.force_sensors[name]['data'].y,2))
                current.append(round(self.artusLite_api._robot_handler.robot.force_sensors[name]['data'].z,2))
            if len(current) == 15:
                current.append(0)

        self.logger.info(f"Current: {current}")
        return current

def test_artus_joint_streamer():
    artus_joint_streamer = ArtusLiteJointStreamer(communication_method='UART',
                                                  communication_channel_identifier='/dev/ttyUSB0',
                                                  hand_type='right',
                                                  reset_on_start=0,
                                                  streaming_frequency=20,
                                                  start_robot=True,
                                                  calibrate=False,
                                                  robot_connected=True)
    joint_angles_1 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    joint_angles_2 = [0, 20, 30, 30, 10, 50, 70, 10, 50, 70, 10, 50, 70, 10, 50, 70]

    while True:
        artus_joint_streamer.stream_joint_angles(joint_angles=joint_angles_1)
        time.sleep(3)
        # receive force feedback
        force_data = artus_joint_streamer.receive_force_feedback()
        # print("Feedback Data: ", force_data)
        artus_joint_streamer.stream_joint_angles(joint_angles=joint_angles_2)
        time.sleep(3)
        # receive force feedback
        force_data = artus_joint_streamer.receive_force_feedback()
        # print("Feedback Data: ", force_data)
        time.sleep(3)


def test_feedback_streaming():
    artus_joint_streamer = ArtusLiteJointStreamer(communication_method='UART',
                                                  communication_channel_identifier='/dev/ttyUSB0',
                                                  robot_type='artus_lite_plus',
                                                  hand_type='right',
                                                  reset_on_start=0,
                                                  streaming_frequency=20,
                                                  start_robot=True,
                                                  calibrate=False,
                                                  robot_connected=True)
    while True:
        # receive force feedback
        joint_angles_1 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        artus_joint_streamer.stream_joint_angles(joint_angles=joint_angles_1)
        # time.sleep(1)
        force_data = artus_joint_streamer.receive_force_feedback()
        # time.sleep(1)
        if force_data is not None:
            time.sleep(0.001)
            # print("Feedback Data: ", force_data)
            pass

      

        joint_angles_1 = [0,0,5,5,0,5,5,0,5,5,0,5,5,0,5,5]
        artus_joint_streamer.stream_joint_angles(joint_angles=joint_angles_1)
        force_data = artus_joint_streamer.receive_force_feedback()
        if force_data is not None:
            time.sleep(0.001)
            pass
            # print("Feedback Data: ", force_data)
        # # time.sleep(3)



if __name__ == "__main__":
    # test_artus_joint_streamer()
    test_feedback_streaming()