"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.

=========================================================
DEPRACATED DEPRACATED DEPRACATED DEPRACATED DEPRACATED DEPRACATED
=========================================================
"""
import time
import json
import os
current_directory = os.getcwd()
import sys
import multiprocessing
sys.path.append(os.path.dirname((os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# print(os.path.dirname(current_directory))
from Sarcomere_Dynamics_Resources.artus_lite_api.ArtusAPI import ArtusAPI,UART,WIFI
import pandas as pd
import numpy as np
from datetime import datetime

def zmq_menu():
    return input('''
Artus simulation for zmq:
1. start conection to hand
2. start robot
3. calibrate
4. start simulating hand
5. close connection
                 ''')

def json_to_command(filename:str,artusapi:ArtusAPI):
    with open(os.path.join(r'C:/Users/General User/Desktop/github_files/Sarcomere_Dynamics_Resources/grasp_patterns',filename),'r') as file:
        grasp_dict = json.load(file)
        for name,values in grasp_dict.items():
            artusapi.set_robot_params_by_joint_name(name,values['input_angle'],values['input_speed'])
        artusapi.send_target_command()


def simulate_artus_teleop(artus3d_L:ArtusAPI, record):
    # CALIBRATE BEFORE RUNNING THIS FILE
    # artus3d_L = ArtusAPI(port='COM11',communication_method=UART,hand='left', zmq_=False)
    # artus3d_R = ArtusAPI(port='COM4', communication_method = 'UART', hand = 'right', zmq_ = False)

    artus3d_L.start_connection()
    # artus3d_R.start_connection()
    artus3d_L.start_robot()
    # artus3d_R.start_robot()

    duration = 4
    record = True
    # while record.value == False:
    #     continue

    current_time = time.perf_counter()

    while record == True:
        json_to_command(filename = 'trial.json', artusapi = artus3d_L)
        # json_to_artus_command('trial.json', artus3d_R)

        while time.perf_counter() - current_time < duration:
            joints_L = artus3d_L.get_robot_states()
            joint_positions_L = []
            for _, joint in joints_L.items():
                joint_positions_L.append(joint.feedback_angle)

            # joints_R = artus3d_R.get_robot_states()
            # joint_positions_R = []
            # for _, joint in joints_R.items():
            #     joint_positions_R.append(joint.feedback_angle)
            grasp_pattern_L = artus3d_L.grasp_pattern
            start_index = grasp_pattern_L.find('[') + 1
            end_index = grasp_pattern_L.find(']', start_index)
            cmd_substring_L = grasp_pattern_L[start_index:end_index]
            joint_commads_L = list(map(int, cmd_substring_L.split(',')))

            # start_index = artus3d_R.grasp_pattern.find('[') + 1
            # end_index = artus3d_R.grasp_pattern.find(']', start_index)
            # cmd_substring_R = artus3d_R.grasp_pattern[start_index:end_index]
            # joint_commads_R = list(map(int, cmd_substring_R.split(',')))

            # artus3d_L.zmq.send_feedback_zmq(joint_positions_L, joint_positions_L) #, joint_positions_R)
            # artus3d_L.zmq.send_command_zmq(joint_commads_L, joint_commads_L) #, joint_commads_R)

        current_time = time.perf_counter()

        json_to_command('grasp_open.json', artus3d_L)
        # json_to_artus_command('grasp_open.json', artus3d_R)

        while time.perf_counter() - current_time < duration:
            joints_L = artus3d_L.get_robot_states()
            joint_positions_L = []
            for _, joint in joints_L.items():
                joint_positions_L.append(joint.feedback_angle)

            # joints_R = artus3d_R.get_robot_states()
            # joint_positions_R = []
            # for _, joint in joints_R.items():
            #     joint_positions_R.append(joint.feedback_angle)

            start_index = artus3d_L.grasp_pattern.find('[') + 1
            end_index = artus3d_L.grasp_pattern.find(']', start_index)
            cmd_substring_L = artus3d_L.grasp_pattern[start_index:end_index]
            joint_commads_L = list(map(int, cmd_substring_L.split(',')))

            # start_index = artus3d_R.grasp_pattern.find('[') + 1
            # end_index = artus3d_R.grasp_pattern.find(']', start_index)
            # cmd_substring_R = artus3d_R.grasp_pattern[start_index:end_index]
            # joint_commads_R = list(map(int, cmd_substring_R.split(',')))

            # artus3d_L.zmq.send_feedback_zmq(joint_positions_L, joint_positions_L) #, joint_positions_R)
            # artus3d_L.zmq.send_command_zmq(joint_commads_L,joint_commads_L) # joint_commads_R)

        current_time = time.perf_counter()

def simulation(artus3d:ArtusAPI, save_directory, reading_frequency = 2, duration = 4):
    artus3d.start_connection()
    artus3d.start_robot()
    sent_command = []
    recieved_feedback = []

    current_time = time.perf_counter()
    last_read_time = current_time

    while True:
        ## change from one to another every 8 seconds.
        ## in each 8 seconds, continuously read and write messages every 1/frequency seconds to a list
        try:
            json_to_command('trial.json', artus3d)
            while time.perf_counter() - current_time < duration:

                if time.perf_counter() - last_read_time > 1 / reading_frequency:

                    joints = artus3d.get_robot_states()
                    joint_positions_only = []
                    for _, joint in joints.items():
                        joint_positions_only.append(joint.feedback_angle)
                    print(f'Edited for zmq: {joint_positions_only}')
                    recieved_feedback.append(joint_positions_only) # replace with zmq publish

                    print(f'grasp_pattern: {artus3d.grasp_pattern}')
                    start_index = artus3d.grasp_pattern.find('[') + 1
                    end_index = artus3d.grasp_pattern.find(']', start_index)
                    cmd_substring = artus3d.grasp_pattern[start_index:end_index]
                    values_list = list(map(int, cmd_substring.split(',')))
                    sent_command.append(values_list) # replace with zmq publish

                    last_read_time = time.perf_counter()
                
            current_time = time.perf_counter()

            json_to_command('grasp_open.json', artus3d)
            while time.perf_counter() - current_time < duration:

                if time.perf_counter() - last_read_time > 1 / reading_frequency:
                    joints = artus3d.get_robot_states()
                    joint_positions_only = []
                    for _, joint in joints.items():
                        joint_positions_only.append(joint.feedback_angle)
                    print(f'Edited for zmq: {joint_positions_only}')
                    recieved_feedback.append(joint_positions_only)

                    print(f'command sent: {artus3d.grasp_pattern}')
                    start_index = artus3d.grasp_pattern.find('[') + 1
                    end_index = artus3d.grasp_pattern.find(']', start_index)
                    cmd_substring = artus3d.grasp_pattern[start_index:end_index]
                    values_list = list(map(int, cmd_substring.split(',')))
                    sent_command.append(values_list)

                    last_read_time = time.perf_counter()

            current_time = time.perf_counter()

        except KeyboardInterrupt:
            print('keyboard interrupt detected')
            json_to_command('grasp_open.json', artus3d)

            artus_cmd_df = pd.DataFrame(sent_command, columns = artus3d.joint_names)#, columns=np.append([f"motor_{i+1}" for i in range(16)]))
            cmd_file_path = os.path.join(save_directory, 'artus_commands.csv')
            artus_cmd_df.to_csv(cmd_file_path, index=False)  

            artus_feed_df = pd.DataFrame(recieved_feedback, columns=artus3d.joint_names)#, columns=np.append([f"motor_{i+1}" for i in range(16)]))
            feed_file_path = os.path.join(save_directory, 'artus_feedback.csv')
            artus_feed_df.to_csv(feed_file_path, index=False)  
            
            artus3d.close_connection()
            exit()
        
# def debug_simulation(artus3d:ArtusAPI, duration = 4, reading_frequency = 5):
#     current_time = time.perf_counter()
#     last_read_time = current_time
#     while True:
#         ## change from one to another every 8 seconds.
#         ## in each 8 seconds, continuously read and write messages every 1/frequency seconds to a list
#         try:
#             json_to_command('trial.json', artus3d)
#             while time.perf_counter() - current_time < duration:

#                 if time.perf_counter() - last_read_time > 1 / reading_frequency:
#                     joints = artus3d.get_robot_states()
#                     joint_positions_only = []
#                     for name, joint in joints.items():
#                         joint_positions_only.append(joint.feedback_angle)
#                     print(f'Feedback for zmq: {joint_positions_only}')

#                     last_read_time = time.perf_counter()
                
#             current_time = time.perf_counter()

#             json_to_command('grasp_open.json', artus3d)
#             print(f'command sent: {artus3d.grasp_pattern}')
#             while time.perf_counter() - current_time < duration:

#                 if time.perf_counter() - last_read_time > 1 / reading_frequency:
#                     joints = artus3d.get_robot_states()
#                     joint_positions_only = []
#                     for name, joint in joints.items():
#                         joint_positions_only.append(joint.feedback_angle)
#                     print(f'Feedback for zmq: {joint_positions_only}')

#                     last_read_time = time.perf_counter()

#             current_time = time.perf_counter()

#         except KeyboardInterrupt:
#             print('keyboard interrupt detected')
#             json_to_command('grasp_open.json', artus3d)
#             artus3d.close_connection()
#             exit()
    


def simulation_for_zmq(reading_frequency = 5, save_directory = r"C:/Users/General User/Desktop/teleoperation_data_pipeline"): #r"C:/Users/sansk/OneDrive/Desktop/artus_data"):
    date = datetime.now()
    date = str(date.strftime("%Y_%d_%b_%H_%M_%S"))
    os.makedirs(save_directory, exist_ok=True)
    current_session_directory = os.path.join(save_directory, date)
    os.mkdir(current_session_directory)

    artus3d = ArtusAPI(port='COM11',communication_method=UART,hand='left', zmq_=True)
    while True:
        user_input = zmq_menu()
        match user_input:
            case "1":
                artus3d.start_connection()
            case "2":
                artus3d.start_robot()
            case "3":
                artus3d.calibrate()
            case "4":
                simulation(artus3d, save_directory=current_session_directory, reading_frequency=reading_frequency)
            case "5":
                record = True
                # record.value = True
                simulate_artus_teleop(artus3d_L=artus3d, record = record)
            # case "t":
            #     debug_simulation(artus3d=artus3d, reading_frequency= reading_frequency)


if __name__ == '__main__':
    # example()
    simulation_for_zmq(reading_frequency= 5)


