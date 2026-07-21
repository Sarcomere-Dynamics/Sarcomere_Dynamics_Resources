"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Receives raw Manus glove joint data over TCP and maps it to ARTUS hand
joint angles, including optional interactive calibration.
"""


import re
import numpy as np
import threading
from collections import deque


import time
import ast

import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print("Root: ",PROJECT_ROOT)

sys.path.append(str(PROJECT_ROOT))
from examples.Tracking.manus_gloves_data.moving_average import MultiMovingAverage

class ManusGlovesHandTrackingData:
    """Receives Manus glove joint data and maps it to ARTUS hand joint angles.

    Owns a TCP server that receives raw joint data from the Manus core
    executable for both hands, applies user-hand-to-ARTUS-hand range
    interpolation and moving-average smoothing, and exposes the resulting
    per-hand joint angle lists for use by the application.
    """

    def __init__(self,
                 port='65432',
                 calibration=False):
        """Initializes tracking state, the TCP server, and calibration data.

        Args:
            port: TCP port to listen on for incoming Manus glove data.
            calibration: If True, runs the interactive calibration sequence
                for both hands and saves the results to disk. If False,
                loads previously saved calibration data from disk.
        """
        self.port = port


        self.order_of_joints = ['index', 'middle', 'ring', 'pinky', 'thumb']
        self.running = False
        self.data_queue = {'index': deque(maxlen=20), 'middle': deque(maxlen=20), 'ring': deque(maxlen=20), 'pinky': deque(maxlen=20), 'thumb': deque(maxlen=20)}
        self.user_hand_min_max_left = {'index': [-15,15,0,90,0,90], 'middle': [-15,15,0,90,0,90], 'ring': [-15,15,0,90,0,90], 'pinky': [-15,15,0,90,0,90], 'thumb': [-25,25,0,90,0,90,0,90]}
        self.user_hand_min_max_right = {'index': [-15,15,0,90,0,90], 'middle': [-15,15,0,90,0,90], 'ring': [-15,15,0,90,0,90], 'pinky': [-15,15,0,90,0,90], 'thumb': [-25,25,0,90,0,90,0,90]}
        self.artus_min_max = {'index': [-15,15,0,90,0,90], 'middle': [-15,15,0,90,0,90], 'ring': [-15,15,0,90,0,90], 'pinky': [-15,15,0,90,0,90], 'thumb': [-25,25,0,90,0,90,0,90]}

        self.moving_average_lefthand =  MultiMovingAverage(window_size=60, num_windows=20)
        self.moving_average_righthand = MultiMovingAverage(window_size=60, num_windows=20)


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
        """Creates and starts the TCP server used to receive Manus glove data.

        Args:
            port: TCP port to bind the server to.
        """
        sys.path.append(str(PROJECT_ROOT))
        from examples.Tracking.zmq_class.tcp_server import TCPServer

        self.tcp_server = TCPServer(port=int(port))
        self.tcp_server.create()



    ## ------------------------------------------------------------------ ##
    ## ---------------------- Data for Application ---------------------- ##
    ## ------------------------------------------------------------------ ##
    def receive_joint_angles(self):
        """Receives raw joint data and updates the decoded left/right joint angles.

        If new data is received, decodes it and refreshes
        self.joint_angles_left and self.joint_angles_right as a side effect.

        Returns:
            The raw joint angle string/data received from the TCP server,
            or the current left/right joint angle dicts if no new data was
            available.
        """
        joint_angles = self.tcp_server.receive() # receive encoded data
        # print("1. Original Data: ", joint_angles)
        if joint_angles is None or joint_angles == "[]" or joint_angles == "":
            return self.joint_angles_dict_L, self.joint_angles_dict_R
        # print("1. Original Data: ", joint_angles)
        self._joint_angles_manus_to_joint_streamer(joint_angles)
        return joint_angles
    
    def get_left_hand_joint_angles(self):
        """Gets the most recently computed left-hand joint angles.

        Returns:
            The left-hand joint angle list, or None if none has been
            computed yet.
        """
        return self.joint_angles_left

    def get_right_hand_joint_angles(self):
        """Gets the most recently computed right-hand joint angles.

        Returns:
            The right-hand joint angle list, or None if none has been
            computed yet.
        """
        return self.joint_angles_right

    def manus_data_to_dict(self, joint_angles):
        """Parses the raw Manus data string into per-finger joint angle dicts.

        Extracts the "L[...]" and "R[...]" segments from the raw data,
        converts each into a flat list of integer angles, and splits the
        result into self.joint_angles_dict_L and self.joint_angles_dict_R
        keyed by finger name. Also applies a fixed correction to the thumb's
        second joint value for both hands.

        Args:
            joint_angles: Raw data string received from the TCP server,
                expected to contain "L[...]" and "R[...]" segments of
                space-separated angle values.
        """
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
        """Decodes raw Manus data into the joint angle format used by the application.

        Parses the raw data, maps user-hand values to the ARTUS hand's
        range, and assembles the flattened per-hand joint angle lists
        (thumb, index, middle, ring, pinky) expected by the rest of the
        application. Updates self.joint_angles_left and
        self.joint_angles_right as a side effect.

        Args:
            joint_angles: Raw data string received from the TCP server.

        Returns:
            A tuple (joint_angles_left, joint_angles_right) of the
            flattened joint angle lists for the left and right hands.
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

        self.joint_angles_left = [-joint_angles_L[4],joint_angles_L[9],joint_angles_L[14], joint_angles_L[19], # thumb
                              -joint_angles_L[0], joint_angles_L[5], joint_angles_L[10], # index
                              -joint_angles_L[1], joint_angles_L[6], joint_angles_L[11], # middle
                              -joint_angles_L[3], joint_angles_L[8], joint_angles_L[13], # ring
                              -joint_angles_L[2], joint_angles_L[7], joint_angles_L[12]] # pinky

        # self.joint_angles_left = [-joint_angles_L[4],joint_angles_L[9],joint_angles_L[14], joint_angles_L[19], # thumb
        #                       -joint_angles_L[0], joint_angles_L[5], joint_angles_L[10], # index
        #                       0, 0, 0, # middle
        #                       0, 0, 0, # ring
        #                       0, 0, 0] # pinky
        
        self.joint_angles_right = [-joint_angles_R[4],joint_angles_R[9],joint_angles_R[14], joint_angles_R[19], # thumb
                              -joint_angles_R[0], joint_angles_R[5], joint_angles_R[10], # index
                              -joint_angles_R[1], joint_angles_R[6], joint_angles_R[11], # middle
                              -joint_angles_R[3], joint_angles_R[8], joint_angles_R[13], # ring
                              -joint_angles_R[2], joint_angles_R[7], joint_angles_R[12]] # pinky
        
        # """ 
        # FOR TESTING
        # """
        # self.joint_angles_right = [-joint_angles_R[4],joint_angles_R[9],joint_angles_R[14], joint_angles_R[19], # thumb
        #                       0, 0, 0, # index
        #                       0, 0, 0, # middle
        #                       0, 0, 0, # ring
        #                       0, 0, 0] # pinky
        
        # print("4. Joint angles sent to hand: ", self.joint_angles_left, self.joint_angles_right)
        
        return self.joint_angles_left, self.joint_angles_right

    ## ------------------------------------------------------------------ ##
    ## --------------------- Map User Hand to Artus Hand ---------------- ##
    ## ------------------------------------------------------------------ ##
    def map_user_hand_to_artus_hand(self, hand="L"):
        """Maps user-hand joint values to ARTUS hand values using calibration data.

        Interpolates the relevant hand's joint angle dict from the user's
        calibrated range into the ARTUS hand's range, then flattens it into
        a moving-average-smoothed list ordered for the ARTUS hand.

        Args:
            hand: Which hand(s) to map. One of "L", "R", or "LR".

        Returns:
            If hand is "L" or "R", the flattened joint rotations list for
            that hand. If hand is "LR", a tuple
            (joint_rotations_list_L, joint_rotations_list_R).
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
        """Flattens the left-hand joint dict into joint_rotations_list and smooths it.

        Appends the interpolated left-hand joint values (in ARTUS joint
        order) to joint_rotations_list in place, and feeds a copy of that
        list into the left-hand moving-average filter. Note: the resulting
        averaged values are computed but assigned only to a local variable,
        so joint_rotations_list retains the unsmoothed values.

        Args:
            joint_rotations_dict: Interpolated left-hand joint angle dict
                keyed by finger name.
            joint_rotations_list: List to append the flattened joint values
                to, in place.
        """
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
        """Flattens the right-hand joint dict into joint_rotations_list and smooths it.

        Appends the interpolated right-hand joint values (in ARTUS joint
        order) to joint_rotations_list in place, and feeds a copy of that
        list into the right-hand moving-average filter. Note: the resulting
        averaged values are computed but assigned only to a local variable,
        so joint_rotations_list retains the unsmoothed values.

        Args:
            joint_rotations_dict: Interpolated right-hand joint angle dict
                keyed by finger name.
            joint_rotations_list: List to append the flattened joint values
                to, in place.
        """
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
        """Linearly rescales a value from a source range to a target range.

        Clamps value to [min_val, max_val] before rescaling.

        Args:
            value: The raw value to rescale.
            min_val: Lower bound of the source range.
            max_val: Upper bound of the source range.
            arm_min_val: Lower bound of the target (ARTUS) range.
            arm_max_val: Upper bound of the target (ARTUS) range.

        Returns:
            The rescaled value in the target range. Returns arm_min_val if
            min_val equals max_val, to avoid division by zero.
        """
        # Ensure the value is within the min_max range
        value = max(min_val, min(value, max_val))

        # Map the value to the artus
        if max_val - min_val == 0:
            return arm_min_val  # Avoid division by zero if min_val == max_val

        scaled_value = ((value - min_val) / (max_val - min_val)) * (arm_max_val - arm_min_val) + arm_min_val
        return scaled_value
    
    def _interpolate_data_L(self, joint_angles_dict):
        """Rescales left-hand joint values from the user's calibrated range to ARTUS range.

        Mutates joint_angles_dict in place, scaling each finger's joint
        values using self.user_hand_min_max_left as the source range and
        self.artus_min_max as the target range.

        Args:
            joint_angles_dict: Left-hand joint angle dict keyed by finger
                name, mutated in place.

        Returns:
            The same joint_angles_dict, with values rescaled in place.
        """
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
        """Rescales right-hand joint values from the user's calibrated range to ARTUS range.

        Mutates joint_angles_dict in place, scaling each finger's joint
        values using self.user_hand_min_max_right as the source range and
        self.artus_min_max as the target range.

        Args:
            joint_angles_dict: Right-hand joint angle dict keyed by finger
                name, mutated in place.

        Returns:
            The same joint_angles_dict, with values rescaled in place.
        """
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
        """Runs or loads calibration data for both hands.

        If calibration is True, runs the interactive calibration sequences
        for the left and right hands and writes the resulting min/max
        dicts to calibration_data_L.txt and calibration_data_R.txt. If
        False, loads the previously saved calibration dicts from those
        files instead.

        Args:
            calibration: Whether to run interactive calibration (True) or
                load existing calibration data from disk (False).
        """

        file_path_L = str(PROJECT_ROOT) + "/examples/Tracking/manus_gloves_data/calibration_data_L.txt"
        file_path_R = str(PROJECT_ROOT) + "/examples/Tracking/manus_gloves_data/calibration_data_R.txt"

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
        """Receives raw joint data and decodes it into the per-hand joint dicts.

        Used during calibration to keep self.joint_angles_dict_L and
        self.joint_angles_dict_R up to date without running the full
        ARTUS-mapping pipeline.

        Returns:
            The raw joint angle data received from the TCP server, or None
            if no data was available.
        """
        joint_angles = self.tcp_server.receive() # receive encoded data
        if joint_angles == None:
            return None
        self.manus_data_to_dict(joint_angles)
        return joint_angles

    def calibrate_L(self):
        """Runs the interactive left-hand calibration sequence.

        Prompts the user through a series of hand poses (finger spread
        min/max, flat/bent/curled positions, thumb positions), recording a
        live-averaged sample after each prompt via self.get_data("L"), and
        uses those samples to populate self.user_hand_min_max_left.

        Returns:
            The updated self.user_hand_min_max_left dict.
        """

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
        """Runs the interactive right-hand calibration sequence.

        Prompts the user through a series of hand poses (finger spread
        min/max, flat/bent/curled positions, thumb positions), recording a
        live-averaged sample after each prompt via self.get_data("R"), and
        uses those samples to populate self.user_hand_min_max_right.

        Returns:
            The updated self.user_hand_min_max_right dict.
        """

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
        """Continuously samples left-hand joint angles into self.temp while running.

        Intended to run in a background thread started by get_data(); loops
        until self.running is set to False, polling roughly every 0.1s.
        """
        while self.running:
            self.receive_joint_angles_for_calibration()
            for finger in self.order_of_joints:
                self.temp[finger] = self.joint_angles_dict_L[finger]
            time.sleep(0.1)

    def gather_data_R(self):
        """Continuously samples right-hand joint angles into self.temp while running.

        Intended to run in a background thread started by get_data(); loops
        until self.running is set to False, polling roughly every 0.1s.
        """
        while self.running:
            self.receive_joint_angles_for_calibration()
            for finger in self.order_of_joints:
                self.temp[finger] = self.joint_angles_dict_R[finger]
            time.sleep(0.1)

    def get_data(self, hand):
        """Collects a live-averaged joint sample for one hand during calibration.

        Starts a background thread that continuously updates self.temp with
        the latest joint angles for the given hand, waits for the user to
        press Enter, then stops the thread. Used as a single calibration
        step to capture the pose the user is holding.

        Args:
            hand: Which hand to sample. One of "L" or "R".
        """
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
    """Manually exercises ManusGlovesHandTrackingData by polling and printing joint angles."""
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
