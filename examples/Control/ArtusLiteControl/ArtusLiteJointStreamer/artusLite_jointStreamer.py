
import time
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
sys.path.append(PROJECT_ROOT)
print("Project Root", PROJECT_ROOT)

# from artus_3d_api.Artus3DAPI import Artus3DAPI
# sys.path.append(PROJECT_ROOT)
from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI

class ArtusLiteJointStreamer:

    def __init__(self,                 
                communication_method= 'UART',
                communication_channel_identifier='COM7',
                hand_type = 'left',
                reset_on_start = 0,
                
                streaming_frequency = 40, # data/seconds
                start_robot=True,
                calibrate= False,
                robot_connected=True,
                ):
        
        self.artusLite_api = ArtusAPI(communication_method=communication_method,
                                    communication_channel_identifier=communication_channel_identifier,
                                    hand_type=hand_type,
                                    reset_on_start=reset_on_start)
        
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
        time.sleep(2)
        if self.robot_start:
            self.artusLite_api.wake_up()
            time.sleep(2)
        if self.calibrate:
            self.artusLite_api.calibrate()
        time.sleep(2)

    def _go_to_zero_position(self):
        self.artusLite_api.set_home_position()
        

    def stream_joint_angles(self, joint_angles = []):
         # make sure all ints
        hand_joints = {0:'0',1:'0',2:'0',3:'0',4:'0',5:'0',6:'0',7:'0',8:'0',9:'0',10:'0',11:'0',12:'0',13:'0',14:'0',15:'0'}
        joint_angles = [int(i) for i in joint_angles]
        
        for i in range(16):
            joint = {'index':i, 'target_angle': joint_angles[i], 'velocity' : 80}
            hand_joints[i] = joint
            
        # set joint angles
        if self._check_streaming_rate():
            # print(f"Sending {self.communication_channel_identifier}...{hand_joints}")
            print(f'******************************** hand joints : ************************************************/n {hand_joints}')
            self.artusLite_api.set_joint_angles(joint_angles=hand_joints)
            return joint_angles
        else:
            print(f'missed {self.communication_channel_identifier}')
            return None
        
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
    

def test_artus_joint_streamer():
    artus_joint_streamer = ArtusLiteJointStreamer()
    joint_angles_1 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    joint_angles_2 = [0, 20, 30, 30, 10, 50, 70, 10, 50, 70, 10, 50, 70, 10, 50, 70]

    while True:
        artus_joint_streamer.stream_joint_angles(joint_angles=joint_angles_1)
        time.sleep(3)
        artus_joint_streamer.stream_joint_angles(joint_angles=joint_angles_2)
        time.sleep(3)


if __name__ == "__main__":
    test_artus_joint_streamer()