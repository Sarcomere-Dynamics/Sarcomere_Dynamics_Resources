"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.

=========================================================
This example script simply runs through a wave motion, starting from the pinky to the thumb 
by setting the joint angles directly through the object one by one.
=========================================================
"""
# ------------------------------------------------------------------------------
# ---------------------------- Import Libraries --------------------------------
# ------------------------------------------------------------------------------
import time
import json
# Add the desired path to the system path
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
# import ArtusAPI
from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI

import numpy as np

def generate_triangle_wave(signal_freq, sample_freq,max):
    """
    Generate triangle wave points from 0 to 90 and back to 0
    
    Args:
        signal_freq: Frequency of the triangle wave in Hz
        sample_freq: Sampling frequency in Hz
    
    Returns:
        String representation of points array
    """
    # Calculate number of points needed for one period
    period = 1.0/signal_freq
    num_points = int(period * sample_freq)
    
    # Generate first half (0 to 90)
    up = np.linspace(0, max, num_points//2, dtype=int)
    
    # Generate second half (90 to 0) 
    down = np.linspace(max, 0, num_points//2, dtype=int)
    
    # Combine into full wave
    points = np.concatenate([up, down])

    print(str(up.tolist()).replace("[","{").replace("]",","),end="\n")
    print(str(down.tolist()).replace("[","").replace("]","};"),end="\n")
    # Convert to string format
    return points

def main(triangle_wave,freq,max):
    # Path to the hand poses
    hand_poses_path = os.path.join(PROJECT_ROOT,'Sarcomere_Dynamics_Resources','data','hand_poses')
    # make dict
    with open(os.path.join(hand_poses_path ,'grasp_open.json'),'r') as file:
        grasp_dict = json.load(file)

    # Initialize ArtusAPI with specified parameters
    artus = ArtusAPI(
        communication_method='UART',
        communication_channel_identifier="/dev/ttyUSB0", ### @TODO EDIT ME ###
        robot_type='artus_lite',
        hand_type='right',
        reset_on_start=0,
        communication_frequency=freq,
        stream=True
    )

    # artus1 = ArtusAPI(
    #     communication_method='UART',
    #     communication_channel_identifier="/dev/ttyUSB1",
    #     robot_type='artus_lite',
    #     hand_type='left',
    #     reset_on_start=0,
    #     communication_frequency=freq
    # )
    # start robot
    artus.connect()
    # artus1.connect()

    time.sleep(1)

    wave_index = 0
    sleeper_flag = False
    sleeper_last = time.perf_counter()  
    time_stamp = time.perf_counter()

    for joint in grasp_dict:
        grasp_dict[joint]["velocity"] = 50

    sleep_time = 0.5
    target_angle = 90

    while True:
        # d2s first
        # grasp_dict["thumb_spread"]["target_angle"] = 20
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)
        # grasp_dict["thumb_spread"]["target_angle"] = -20
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)
        
        
        # grasp_dict["thumb_d2"]["target_angle"] = target_angle
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)

        # grasp_dict["thumb_d2"]["target_angle"] = 0
        # grasp_dict["thumb_d1"]["target_angle"] = target_angle
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)

        # grasp_dict["thumb_d1"]["target_angle"] = 0
        grasp_dict["pinky_flex"]["target_angle"] = target_angle       
        grasp_dict["pinky_d2"]["target_angle"] = target_angle
        artus.set_joint_angles(grasp_dict)
        time.sleep(sleep_time)

        grasp_dict["ring_flex"]["target_angle"] = target_angle
        grasp_dict["ring_d2"]["target_angle"] = target_angle
        artus.set_joint_angles(grasp_dict)
        time.sleep(sleep_time)

        grasp_dict["middle_flex"]["target_angle"] = target_angle          
        grasp_dict["middle_d2"]["target_angle"] = target_angle
        artus.set_joint_angles(grasp_dict)
        time.sleep(sleep_time)

        grasp_dict["index_d2"]["target_angle"] = target_angle
        grasp_dict["index_flex"]["target_angle"] = target_angle
        artus.set_joint_angles(grasp_dict)
        time.sleep(sleep_time)

        time.sleep(0.5)

        grasp_dict["thumb_flex"]["target_angle"] = 40       
        grasp_dict["thumb_d2"]["target_angle"] = 30
        grasp_dict["thumb_d1"]["target_angle"] = 30
        grasp_dict["thumb_spread"]["target_angle"] = -20
        artus.set_joint_angles(grasp_dict)

        time.sleep(sleep_time)

        time.sleep(1)

        for joint in grasp_dict:
            grasp_dict[joint]["target_angle"] = 0

        artus.set_joint_angles(grasp_dict)
        


        # grasp_dict["pinky_d2"]["target_angle"] = 0
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)

        # grasp_dict["pinky_flex"]["target_angle"] = target_angle
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)

        # grasp_dict["pinky_flex"]["target_angle"] = 0
        # grasp_dict["ring_flex"]["target_angle"] = target_angle
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)

        # grasp_dict["ring_flex"]["target_angle"] = 0
        # grasp_dict["middle_flex"]["target_angle"] = target_angle
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)

        # grasp_dict["middle_flex"]["target_angle"] = 0
        # grasp_dict["index_flex"]["target_angle"] = target_angle
        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)

        # grasp_dict["index_flex"]["target_angle"] = 0
        # artus.set_joint_angles(grasp_dict)
        
        # time.sleep(sleep_time)

        # half second delay before abdcution
        # time.sleep(0.5)

        # grasp_dict["index_spread"]["target_angle"] = -15
        # grasp_dict["middle_spread"]["target_angle"] = -10
        # grasp_dict["ring_spread"]["target_angle"] = 10
        # grasp_dict["pinky_spread"]["target_angle"] = 15

        # artus.set_joint_angles(grasp_dict)
        # time.sleep(sleep_time)

        # grasp_dict["index_spread"]["target_angle"] = 0
        # grasp_dict["middle_spread"]["target_angle"] = 0
        # grasp_dict["ring_spread"]["target_angle"] = 0
        # grasp_dict["pinky_spread"]["target_angle"] = 0

        # artus.set_joint_angles(grasp_dict)

        time.sleep(5)


        # # Update all joint angles in the dictionary
        # for joint in grasp_dict:
        #     if grasp_dict[joint]["index"] not in [0,1,4,7,10,13] : # :[2,3]
        #         grasp_dict[joint]["velocity"] = 40
        #         grasp_dict[joint]["target_angle"] = int(triangle_wave[wave_index])
        #     elif grasp_dict[joint]["index"] == 0 and int(triangle_wave[wave_index]) <= 40:
        #         grasp_dict[joint]["velocity"] = 40
        #         grasp_dict[joint]["target_angle"] = int(triangle_wave[wave_index])-20
        #     # if grasp_dict[joint]["index"] == 8:
        #     #     grasp_dict[joint]["velocity"] = 20
        #     #     grasp_dict[joint]["target_angle"] = int(triangle_wave[wave_index])
        # try:
        #     if sleeper_flag:
        #         if time.perf_counter() - sleeper_last > 1:
        #             sleeper_flag = False
        #     # Send updated positions to the robot
        #     elif artus.set_joint_angles(grasp_dict):
        #         if triangle_wave[wave_index] == max:
        #             sleeper_flag = True
        #             sleeper_last = time.perf_counter()
        #         elif triangle_wave[wave_index] == 0:
        #             sleeper_flag = True
        #             sleeper_last = time.perf_counter()
        #         # Increment wave index and loop back to start if needed
        #         wave_index = (wave_index + 1) % len(triangle_wave)

        #     x = artus.get_streamed_joint_angles()
        #     if x:
        #         # print(f'Data Returned: {x}')
        #         print(f'time period: {(time.perf_counter() - time_stamp)*1000:.2f} ms')
        #         time_stamp = time.perf_counter()
            # else:
            #     print(f'x.type = {type(x)}')
        # except KeyboardInterrupt:
        #     artus.disconnect()
        #     print(f'Disconnected from robot')
        #     return
        # except Exception as e:
        #     print(e)
        # time.sleep(0.05)  # Match the streaming frequency

    artus.disconnect()


if __name__ == "__main__":
    # gete com port
    while True:
        try:
            freq = 50
            max_val = 45
            triangle_wave = generate_triangle_wave(0.8,freq,max_val)
            main(triangle_wave,freq,max_val)
        except Exception as e:
            print('E::'+e)
