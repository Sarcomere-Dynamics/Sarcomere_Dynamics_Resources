
import re
import numpy as np
import threading
from collections import deque


import time
import ast

import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("Root: ",PROJECT_ROOT)

sys.path.append(str(PROJECT_ROOT))
from Sarcomere_Dynamics_Resources.examples.Control.Tracking.manus_gloves_data.moving_average import MultiMovingAverage

class ManusGlovesHandTrackingData:

    def __init__(self,
                 port='65432',
                 calibration=False):
        
        self.port = port


        self.order_of_joints = ['index', 'middle', 'ring', 'pinky', 'thumb']
        self.running = False
        self.data_queue = {'index': deque(maxlen=20), 'middle': deque(maxlen=20), 'ring': deque(maxlen=20), 'pinky': deque(maxlen=20), 'thumb': deque(maxlen=20)}
        self.user_hand_min_max_left = {'index': [-15,15,0,90,0,90], 'middle': [-15,15,0,90,0,90], 'ring': [-15,15,0,90,0,90], 'pinky': [-15,15,0,90,0,90], 'thumb': [-25,25,0,90,0,90,0,90]}
        self.user_hand_min_max_right = {'index': [-15,15,0,90,0,90], 'middle': [-15,15,0,90,0,90], 'ring': [-15,15,0,90,0,90], 'pinky': [-15,15,0,90,0,90], 'thumb': [-25,25,0,90,0,90,0,90]}
        self.artus_min_max = {'index': [-15,15,0,90,0,90], 'middle': [-15,15,0,90,0,90], 'ring': [-15,15,0,90,0,90], 'pinky': [-15,15,0,90,0,90], 'thumb': [-25,25,0,90,0,90,0,90]}

        self.moving_average_lefthand = MultiMovingAverage(window_size=30, num_windows=20)
        self.moving_average_righthand = MultiMovingAverage(window_size=30, num_windows=20)


        self.joint_angles_left = None # [thumb_1, thumb_2, thumb_3, thumb4, index_1, index_2, index_3, middle_1, middle_2, middle_3, ring, pinky]
        self.joint_angles_right = None

        self._initialize_tcp_server(port=port)


        self.joint_angles_dict_R = {'index':[0,0,0],
                                  'middle':[0,0,0],
                                  'ring':[0,0,0],
                                  'pinky':[0,0,0],
                                  'thumb':[0,0,0,0],
                                  }
        
        self.joint_angles_dict_L = {'index':[0,0,0],
                                  'middle':[0,0,0],
                                  'ring':[0,0,0],
                                  'pinky':[0,0,0],
                                  'thumb':[0,0,0,0],
                                  }
        

        self.temp = {finger: [0, 0, 0, 0] for finger in self.order_of_joints}

        self.data_L = None
        self.data_R = None        

        self.calibration = calibration
        self.calibrate(self.calibration)


    # def get_tcp_port_handle(self):
    #     pass

    def _initialize_tcp_server(self, port="65432"):
        sys.path.append(str(PROJECT_ROOT))
        from Sarcomere_Dynamics_Resources.examples.Control.Tracking.zmq_class.tcp_server import TCPServer

        self.tcp_server = TCPServer(port=int(port))
        self.tcp_server.create()



    ## ------------------------------------------------------------------ ##
    ## ---------------------- Data for Application ---------------------- ##
    ## ------------------------------------------------------------------ ##
    def receive_joint_angles(self):
        """
        Receive joint angles from the hand tracking method
        """
        joint_angles = self.tcp_server.receive() # receive encoded data
        # print("1. Original Data: ", joint_angles)
        if joint_angles is None or joint_angles == "[]" or joint_angles == "":
            return self.joint_angles_dict_L, self.joint_angles_dict_R
        # print("1. Original Data: ", joint_angles)
        self._joint_angles_manus_to_joint_streamer(joint_angles)
        return joint_angles
    
    def get_left_hand_joint_angles(self):
        return self.joint_angles_left
    
    def get_right_hand_joint_angles(self):
        return self.joint_angles_right

    def manus_data_to_dict(self, joint_angles):
        data_L = None
        data_R = None
        pattern_L = r'L\[(.*?)\]'
        pattern_R = r'R\[(.*?)\]'

 
        temp_L = None
        temp_R = None
        match_L = re.search(pattern_L, joint_angles, re.DOTALL)
        if match_L:
            temp_L = match_L.group(1).strip()
        match_R = re.search(pattern_R, joint_angles, re.DOTALL)
        if match_R:
            temp_R = match_R.group(1).strip()

        if temp_L != None:
            self.data_L = temp_L
        if temp_R != None:
            self.data_R = temp_R

   
        # if data_L is None or data_R is None:
        #     return

        data_L = self.data_L.replace("[","").replace("]","").split()

        try:
            data_L = [int(float(angle)) for angle in data_L]
        except ValueError as e:
            print(f"Error converting data: {e}")
            data_L = []

        data_L.extend(data_L)

        data_R = self.data_R.replace("[","").replace("]","").split()

        try:
            data_R = [int(float(angle)) for angle in data_R]
        except ValueError as e:
            print(f"Error converting data: {e}")
            data_R = []

        data_R.extend(data_R)

        # print("Data L: ", data_L)
        # print("Data R: ", data_R)

        self.joint_angles_dict_L['thumb'] = data_L[0:4]
        self.joint_angles_dict_L['index'] = data_L[4:8]
        self.joint_angles_dict_L['middle'] = data_L[8:12]
        self.joint_angles_dict_L['ring'] = data_L[12:16]
        self.joint_angles_dict_L['pinky'] = data_L[16:20]

        # self.joint_angles_dict_L['thumb'][0] = (self.joint_angles_dict_L['thumb'][0] - 10)
        self.joint_angles_dict_L['thumb'][1] = (70 - self.joint_angles_dict_L['thumb'][1])

        self.joint_angles_dict_R['thumb'] = data_R[0:4]
        self.joint_angles_dict_R['index'] = data_R[4:8]
        self.joint_angles_dict_R['middle'] = data_R[8:12]
        self.joint_angles_dict_R['ring'] = data_R[12:16]
        self.joint_angles_dict_R['pinky'] = data_R[16:20]
        
        # self.joint_angles_dict_R['thumb'][0] = (self.joint_angles_dict_R['thumb'][0] - 20)
        self.joint_angles_dict_R['thumb'][1] = (70-self.joint_angles_dict_R['thumb'][1])
    
    def _joint_angles_manus_to_joint_streamer(self, joint_angles):
        """
        Decodes input data from manus core executable to desired format for application
        """

        # decode received data and split to left and right

        self.manus_data_to_dict(joint_angles)
        # print("2. Joint angle Dicts: ", self.joint_angles_dict_L, self.joint_angles_dict_R)

        joint_angles_L, joint_angles_R = self.map_user_hand_to_artus_hand("LR")

        # print("3. mapped joint angles: ", joint_angles_L, joint_angles_R)

        # Organizing Data
        # [thumb_1,   thumb_2,   thumb_3,  thumb_4, 
        #  index_1,   index_2,   index_3, 
        #  middle_1,  middle_2,  middle_3, 
        #  ring_1,    ring_2,    ring_3,
        #  pinky_1,   pinky_2,   pinky_3]

        # self.joint_angles_left = [-joint_angles_L[4],joint_angles_L[9],joint_angles_L[14], joint_angles_L[19], # thumb
        #                       -joint_angles_L[0], joint_angles_L[5], joint_angles_L[10], # index
        #                       -joint_angles_L[1], joint_angles_L[6], joint_angles_L[11], # middle
        #                       -joint_angles_L[3], joint_angles_L[8], joint_angles_L[13], # ring
        #                       -joint_angles_L[2], joint_angles_L[7], joint_angles_L[12]] # pinky

        self.joint_angles_left = [-joint_angles_L[4],joint_angles_L[9],joint_angles_L[14], joint_angles_L[19], # thumb
                              -joint_angles_L[0], joint_angles_L[5], joint_angles_L[10], # index
                              0, 0, 0, # middle
                              0, 0, 0, # ring
                              0, 0, 0] # pinky
        
        self.joint_angles_right = [-joint_angles_R[4],joint_angles_R[9],joint_angles_R[14], joint_angles_R[19], # thumb
                              -joint_angles_R[0], joint_angles_R[5], joint_angles_R[10], # index
                              -joint_angles_R[1], joint_angles_R[6], joint_angles_R[11], # middle
                              -joint_angles_R[3], joint_angles_R[8], joint_angles_R[13], # ring
                              -joint_angles_R[2], joint_angles_R[7], joint_angles_R[12]] # pinky
        
        # self.joint_angles_right = [-joint_angles_R[4],joint_angles_R[9],joint_angles_R[14], joint_angles_R[19], # thumb
        #                       -joint_angles_R[0], joint_angles_R[5], joint_angles_R[10], # index
        #                       -joint_angles_R[1], joint_angles_R[6], joint_angles_R[11], # middle
                            #   0, 0, 0, # ring
                            #   0, 0, 0] # pinky
        
        # print("4. Joint angles sent to hand: ", self.joint_angles_left, self.joint_angles_right)
        
        return self.joint_angles_left, self.joint_angles_right

    ## ------------------------------------------------------------------ ##
    ## --------------------- Map User Hand to Artus Hand ---------------- ##
    ## ------------------------------------------------------------------ ##
    def map_user_hand_to_artus_hand(self, hand="L"):
        """
        Maps data from user hand to artus hand using the calibration data
        """
        # Hand can take these values: L, R, LR
    
        joint_rotations_list_L = []
        joint_rotations_list_R = []

        if hand == "L":
            self._interpolate_data_L(self.joint_angles_dict_L)
            self._append_list_L(self.joint_angles_dict_L, joint_rotations_list_L)

            return joint_rotations_list_L
        
        elif hand == "R":
            self._interpolate_data_R(self.joint_angles_dict_R)
            self._append_list_R(self.joint_angles_dict_R, joint_rotations_list_R)

            return joint_rotations_list_R
        elif hand == "LR":
            self._interpolate_data_L(self.joint_angles_dict_L)
            self._interpolate_data_R(self.joint_angles_dict_R)
            self._append_list_L(self.joint_angles_dict_L, joint_rotations_list_L)
            self._append_list_R(self.joint_angles_dict_R, joint_rotations_list_R)

            return joint_rotations_list_L, joint_rotations_list_R
    
    def _append_list_L(self, joint_rotations_dict, joint_rotations_list):
        joint_rotations_list.append(joint_rotations_dict['index'][0])
        joint_rotations_list.append(joint_rotations_dict['middle'][0])
        joint_rotations_list.append(joint_rotations_dict['pinky'][0])
        joint_rotations_list.append(joint_rotations_dict['ring'][0])
        joint_rotations_list.append(-joint_rotations_dict['thumb'][0])

        joint_rotations_list.append(joint_rotations_dict['index'][1])
        joint_rotations_list.append(joint_rotations_dict['middle'][1])
        joint_rotations_list.append(joint_rotations_dict['pinky'][1])
        joint_rotations_list.append(joint_rotations_dict['ring'][1])
        joint_rotations_list.append(joint_rotations_dict['thumb'][1])
        
        joint_rotations_list.append(joint_rotations_dict['index'][2])
        joint_rotations_list.append(joint_rotations_dict['middle'][2])
        joint_rotations_list.append(joint_rotations_dict['pinky'][2])
        joint_rotations_list.append(joint_rotations_dict['ring'][2])
        joint_rotations_list.append(joint_rotations_dict['thumb'][2])
        
        joint_rotations_list.append(joint_rotations_dict['index'][2])
        joint_rotations_list.append(joint_rotations_dict['middle'][2])
        joint_rotations_list.append(joint_rotations_dict['pinky'][2])
        joint_rotations_list.append(joint_rotations_dict['ring'][2])
        joint_rotations_list.append(joint_rotations_dict['thumb'][3])

        

        # add joint positions to moving average handler
        self.moving_average_lefthand.add_values(joint_rotations_list.copy())
        # get the average of the joint positions
        joint_rotations_list = self.moving_average_lefthand.get_averages()

    def _append_list_R(self, joint_rotations_dict, joint_rotations_list):
        joint_rotations_list.append(joint_rotations_dict['index'][0])
        joint_rotations_list.append(joint_rotations_dict['middle'][0])
        joint_rotations_list.append(joint_rotations_dict['pinky'][0])
        joint_rotations_list.append(joint_rotations_dict['ring'][0])
        joint_rotations_list.append(-joint_rotations_dict['thumb'][0])

        joint_rotations_list.append(joint_rotations_dict['index'][1])
        joint_rotations_list.append(joint_rotations_dict['middle'][1])
        joint_rotations_list.append(joint_rotations_dict['pinky'][1])
        joint_rotations_list.append(joint_rotations_dict['ring'][1])
        joint_rotations_list.append(joint_rotations_dict['thumb'][1])
        
        joint_rotations_list.append(joint_rotations_dict['index'][2])
        joint_rotations_list.append(joint_rotations_dict['middle'][2])
        joint_rotations_list.append(joint_rotations_dict['pinky'][2])
        joint_rotations_list.append(joint_rotations_dict['ring'][2])
        joint_rotations_list.append(joint_rotations_dict['thumb'][2])
        
        joint_rotations_list.append(joint_rotations_dict['index'][2])
        joint_rotations_list.append(joint_rotations_dict['middle'][2])
        joint_rotations_list.append(joint_rotations_dict['pinky'][2])
        joint_rotations_list.append(joint_rotations_dict['ring'][2])
        joint_rotations_list.append(joint_rotations_dict['thumb'][3])
        
        # add joint positions to moving average handler
        self.moving_average_righthand.add_values(joint_rotations_list.copy())
        # get the average of the joint positions
        joint_rotations_list = self.moving_average_righthand.get_averages()
    
    def _scale_value(self, value, min_val, max_val, arm_min_val, arm_max_val):
        # Ensure the value is within the min_max range
        value = max(min_val, min(value, max_val))

        # Map the value to the artus
        if max_val - min_val == 0:
            return arm_min_val  # Avoid division by zero if min_val == max_val

        scaled_value = ((value - min_val) / (max_val - min_val)) * (arm_max_val - arm_min_val) + arm_min_val
        return scaled_value
    
    def _interpolate_data_L(self, joint_angles_dict):
        for finger in self.order_of_joints:
            num_joints = 0
            if finger == "thumb":
                num_joints = 4
            else:
                num_joints = 3

            for joint_index in range(num_joints):
                value = joint_angles_dict[finger][joint_index]
                min_index = joint_index * 2
                max_index = min_index + 1

                min_val = self.user_hand_min_max_left[finger][min_index]
                max_val = self.user_hand_min_max_left[finger][max_index]
                arm_min_val = self.artus_min_max[finger][min_index]
                arm_max_val = self.artus_min_max[finger][max_index]

                scaled_value = self._scale_value(value, min_val, max_val, arm_min_val, arm_max_val)
                joint_angles_dict[finger][joint_index] = scaled_value

        return joint_angles_dict
    
    def _interpolate_data_R(self, joint_angles_dict):
        for finger in self.order_of_joints:
            num_joints = 0
            if finger == "thumb":
                num_joints = 4
            else:
                num_joints = 3

            for joint_index in range(num_joints):
                value = joint_angles_dict[finger][joint_index]
                min_index = joint_index * 2
                max_index = min_index + 1

                min_val = self.user_hand_min_max_right[finger][min_index]
                max_val = self.user_hand_min_max_right[finger][max_index]
                arm_min_val = self.artus_min_max[finger][min_index]
                arm_max_val = self.artus_min_max[finger][max_index]

                scaled_value = self._scale_value(value, min_val, max_val, arm_min_val, arm_max_val)
                joint_angles_dict[finger][joint_index] = scaled_value

        return joint_angles_dict
    
    ## ------------------------------------------------------------------ ##
    ## ---------------------- User Hand Calibration --------------------- ##
    ## ------------------------------------------------------------------ ##

    def calibrate(self, calibration):

        file_path_L = str(PROJECT_ROOT) + "\\Sarcomere_Dynamics_Resources\\examples\\Control\\Tracking\\manus_gloves_data\\calibration_data_L.txt"
        file_path_R = str(PROJECT_ROOT) + "\\Sarcomere_Dynamics_Resources\\examples\\Control\\Tracking\\manus_gloves_data\\calibration_data_R.txt"

        if calibration:
            self.user_hand_min_max_left = self.calibrate_L()
            self.user_hand_min_max_right = self.calibrate_R()

            with open(file_path_L, 'w') as f:
                f.write(str(self.user_hand_min_max_left))

            with open(file_path_R, 'w') as f:
                f.write(str(self.user_hand_min_max_right))
        else:
            # load existing calibration
            with open(file_path_L, 'r') as f:
                self.user_hand_min_max_left = ast.literal_eval(f.read())
            with open(file_path_R, 'r') as f:
                self.user_hand_min_max_right = ast.literal_eval(f.read())
    
    def receive_joint_angles_for_calibration(self):
        """
        Receive joint angles from the hand tracking method
        """
        joint_angles = self.tcp_server.receive() # receive encoded data
        if joint_angles == None:
            return None
        self.manus_data_to_dict(joint_angles)
        return joint_angles

    def calibrate_L(self):

        ############# Calibrating Finger Spread (Abduction) ###########################
        for finger in self.order_of_joints:

            ###################### MIN ############################

            print(f"Calibrating LEFT {finger} SPREAD MIN")
            self.get_data("L")
            self.user_hand_min_max_left[finger][0] = self.temp[finger][0]

            ###################### MAX ############################

            print(f"Calibrating LEFT {finger} SPREAD MAX")
            self.get_data("L")
            self.user_hand_min_max_left[finger][1] = self.temp[finger][0]


        ############# Calibrating Finger Flex ###########################
        print(f"Put LEFT fingers together flat on table, thumb outwards (Making L shape)")
        self.get_data("L")

        self.user_hand_min_max_left["index"][2] = self.temp["index"][1]
        self.user_hand_min_max_left["middle"][2] = self.temp["middle"][1]
        self.user_hand_min_max_left["ring"][2] = self.temp["ring"][1]
        self.user_hand_min_max_left["pinky"][2] = self.temp["pinky"][1]
        self.user_hand_min_max_left["thumb"][2] = self.temp["thumb"][1]

        self.user_hand_min_max_left["index"][4] = self.temp["index"][2]
        self.user_hand_min_max_left["middle"][4] = self.temp["middle"][2]
        self.user_hand_min_max_left["ring"][4] = self.temp["ring"][2]
        self.user_hand_min_max_left["pinky"][4] = self.temp["pinky"][2]
        self.user_hand_min_max_left["thumb"][4] = self.temp["thumb"][2]

        self.user_hand_min_max_left["thumb"][6] = self.temp["thumb"][3]

        print(f"Bend fingers 90 degrees")
        self.get_data("L")

        self.user_hand_min_max_left["index"][3] = self.temp["index"][1]
        self.user_hand_min_max_left["middle"][3] = self.temp["middle"][1]
        self.user_hand_min_max_left["ring"][3] = self.temp["ring"][1]
        self.user_hand_min_max_left["pinky"][3] = self.temp["pinky"][1]

        print(f"Fully bend four fingers")
        self.get_data("L")

        self.user_hand_min_max_left["index"][5] = self.temp["index"][2]
        self.user_hand_min_max_left["middle"][5] = self.temp["middle"][2]
        self.user_hand_min_max_left["ring"][5] = self.temp["ring"][2]
        self.user_hand_min_max_left["pinky"][5] = self.temp["pinky"][2]

        ############# Calibrating Thumb Flex ###########################
        print(f"Move thumb to the bottom of pinky")
        self.get_data("L")

        self.user_hand_min_max_left["thumb"][3] = self.temp["thumb"][1]

        print(f"Curl Thumb")
        self.get_data("L")

        self.user_hand_min_max_left["thumb"][5] = self.temp["thumb"][2]
        self.user_hand_min_max_left["thumb"][7] = self.temp["thumb"][3]

        return self.user_hand_min_max_left
     

    def calibrate_R(self):

        ############# Calibrating Finger Spread (Abduction) ###########################
        for finger in self.order_of_joints:

            ###################### MIN ############################

            print(f"Calibrating RIGHT {finger} SPREAD MIN")
            self.get_data("R")
            self.user_hand_min_max_right[finger][0] = self.temp[finger][0]

            ###################### MAX ############################

            print(f"Calibrating RIGHT {finger} SPREAD MAX")
            self.get_data("R")
            self.user_hand_min_max_right[finger][1] = self.temp[finger][0]


        ############# Calibrating Finger Flex ###########################
        print(f"Put RIGHT fingers together flat on table, thumb outwards (Making L shape)")
        self.get_data("R")

        self.user_hand_min_max_right["index"][2] = self.temp["index"][1]
        self.user_hand_min_max_right["middle"][2] = self.temp["middle"][1]
        self.user_hand_min_max_right["ring"][2] = self.temp["ring"][1]
        self.user_hand_min_max_right["pinky"][2] = self.temp["pinky"][1]
        self.user_hand_min_max_right["thumb"][2] = self.temp["thumb"][1]

        self.user_hand_min_max_right["index"][4] = self.temp["index"][2]
        self.user_hand_min_max_right["middle"][4] = self.temp["middle"][2]
        self.user_hand_min_max_right["ring"][4] = self.temp["ring"][2]
        self.user_hand_min_max_right["pinky"][4] = self.temp["pinky"][2]
        self.user_hand_min_max_right["thumb"][4] = self.temp["thumb"][2]

        self.user_hand_min_max_right["thumb"][6] = self.temp["thumb"][3]

        print(f"Bend fingers 90 degrees")
        self.get_data("R")

        self.user_hand_min_max_right["index"][3] = self.temp["index"][1]
        self.user_hand_min_max_right["middle"][3] = self.temp["middle"][1]
        self.user_hand_min_max_right["ring"][3] = self.temp["ring"][1]
        self.user_hand_min_max_right["pinky"][3] = self.temp["pinky"][1]

        print(f"Fully bend four fingers")
        self.get_data("R")

        self.user_hand_min_max_right["index"][5] = self.temp["index"][2]
        self.user_hand_min_max_right["middle"][5] = self.temp["middle"][2]
        self.user_hand_min_max_right["ring"][5] = self.temp["ring"][2]
        self.user_hand_min_max_right["pinky"][5] = self.temp["pinky"][2]

        ############# Calibrating Thumb Flex ###########################
        print(f"Move thumb to the bottom of pinky")
        self.get_data("R")

        self.user_hand_min_max_right["thumb"][3] = self.temp["thumb"][1]

        print(f"Curl Thumb")
        self.get_data("R")

        self.user_hand_min_max_right["thumb"][5] = self.temp["thumb"][2]
        self.user_hand_min_max_right["thumb"][7] = self.temp["thumb"][3]

        return self.user_hand_min_max_right
    
    def gather_data_L(self):
        while self.running:
            self.receive_joint_angles_for_calibration()
            for finger in self.order_of_joints:
                self.temp[finger] = self.joint_angles_dict_L[finger]
            time.sleep(0.1)

    def gather_data_R(self):
        while self.running:
            self.receive_joint_angles_for_calibration()
            for finger in self.order_of_joints:
                self.temp[finger] = self.joint_angles_dict_R[finger]
            time.sleep(0.1)

    def get_data(self, hand):
        self.running = True
        if hand == "L":
            thread = threading.Thread(target=self.gather_data_L)
        elif hand == "R":
            thread = threading.Thread(target=self.gather_data_R)            
        thread.start()

        print()
        input("Press Enter to record value")
        print()

        self.running = False
        thread.join()  # Wait for the thread to finish


def test_hand_tracking_data():
    hand_tracking_data = ManusGlovesHandTrackingData(port="65432")
    while True:
        # Receive joint angles from Manus core exe
        joint_angles = hand_tracking_data.receive_joint_angles()

        if joint_angles is not None:
            # left and right hand joitn angles for the application 
            joint_angles_left = hand_tracking_data.get_left_hand_joint_angles()
            joint_angles_right = hand_tracking_data.get_right_hand_joint_angles()
            print("Left Hand Data: ", joint_angles_left)
            print("Right Hand Data: ", joint_angles_right)


if __name__ == "__main__":
    test_hand_tracking_data()