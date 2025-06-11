"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.


=========================================================
This example script creates a triangle wave signal at a set singal and sample frequency to stream to the hand
while also receiving streamed feedback data from the hand. 
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
try:
    from ArtusAPI.artus_api import ArtusAPI  # Attempt to import the pip-installed version
    print("Using pip-installed version of ArtusAPI")
except ModuleNotFoundError:
    from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI  # Fallback to the local version
    print("Using local version of ArtusAPI")

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

def main(triangle_wave, freq, max):
    import logging

    # Save logging configuration to a file with date included in the log filename
    log_filename = f"app_{time.strftime('%Y%m%d')}.log"
    logging.basicConfig(filename=log_filename, level=logging.WARNING, format='%(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # Path to the hand poses
    hand_poses_path = os.path.join(PROJECT_ROOT, 'Sarcomere_Dynamics_Resources', 'data', 'hand_poses')
    # make dict
    with open(os.path.join(hand_poses_path, 'grasp_open.json'), 'r') as file:
        grasp_dict = json.load(file)

    # Initialize ArtusAPI with specified parameters
    artus = ArtusAPI(
        communication_method='UART',
        communication_channel_identifier="/dev/ttyUSB0",  ### @TODO EDIT ME ###
        robot_type='artus_lite_plus',
        hand_type='left',
        reset_on_start=0,
        communication_frequency=freq,
        stream=True
    )

    # Start robot
    artus.connect()

    time.sleep(1)

    wave_index = 0
    sleeper_flag = False
    sleeper_last = time.perf_counter()
    time_stamp = time.perf_counter()
    while True:
        # Update all joint angles in the dictionary
        for joint in grasp_dict:
            if grasp_dict[joint]["index"] not in [0, 3, 4, 7, 10, 13]:
                grasp_dict[joint]["target_angle"] = int(triangle_wave[wave_index])
            elif grasp_dict[joint]["index"] == 0 and int(triangle_wave[wave_index]) <= 45:
                grasp_dict[joint]["target_angle"] = int(triangle_wave[wave_index]) - 20
            grasp_dict[joint]["velocity"] = 50

        try:
            x = artus.get_streamed_joint_angles()
            if sleeper_flag:
                if time.perf_counter() - sleeper_last > 1:
                    sleeper_flag = False
            # Send updated positions to the robot
            elif x is not None and artus.set_joint_angles(grasp_dict,True):
                if triangle_wave[wave_index] == max:
                    sleeper_flag = True
                    sleeper_last = time.perf_counter()
                elif triangle_wave[wave_index] == 0:
                    sleeper_flag = True
                    sleeper_last = time.perf_counter()
                # Increment wave index and loop back to start if needed
                wave_index = (wave_index + 1) % len(triangle_wave)


            if x:
                if artus._robot_handler.robot.robot_type == 'artus_lite':
                    feedback_forces = [data.feedback_force for data in artus._robot_handler.robot.hand_joints.values()]
                # elif artus._robot_handler.robot.robot_type == 'artus_lite_plus':
                    # feedback_forces = [data.feedback_force for data in artus._robot_handler.robot.force_sensors.values()]
                print(f'Feedback data: {x}')
                logger.warning(f'Current Feedback Forces: {x}')
                time_stamp = time.perf_counter()
        except KeyboardInterrupt:
            artus.set_home_position()
            time.sleep(1)
            artus.sleep()
            artus.disconnect()
            logger.info('Disconnected from robot')
            quit()
        except Exception as e:
            logger.error(e)

    artus.disconnect()

if __name__ == "__main__":
    # gete com port
    while True:
        try:
            freq = 50
            max_val = 37
            triangle_wave = generate_triangle_wave(1.5,freq,max_val)
            main(triangle_wave,freq,max_val)
        except Exception as e:
            print('E::'+e)
