"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.

=========================================================
This example script uses a server-client ethernet architecture that Sarcomere Dynamics has used in-house for
control through an OMRON TM-7. This script uses a received variable to execute a given movement. 
=========================================================
"""
import socket
import time
import threading
import json
import os
import sys
from pathlib import Path
# Current file's directory
current_file_path = Path(__file__).resolve()
# Add the desired path to the system path
desired_path = current_file_path.parent.parent
sys.path.append(str(desired_path))
 
from ArtusAPI.artus_api import ArtusAPI

class EthernetServer:
    def __init__(self,
                SERVER_IP = None,
                SERVER_PORT = 5050,
                buffer_size = 1024):
        
        if SERVER_IP is None:
            self.SERVER_IP = socket.gethostbyname(socket.gethostname())  # 169.254.87.127 (when connected to Omron's Arm control box)
        else:
            self.SERVER_IP = SERVER_IP
        # print('IP: ', self.SERVER_IP)
        # SERVER_IP = '0.0.0.0'  # Listen on all available interfaces

        self.SERVER_PORT = SERVER_PORT
        self.buffer_size = buffer_size
        self.connected = False

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.SERVER_IP, self.SERVER_PORT))
        # self.server_socket.listen(5)
        self.server_socket.listen()

        print('Waiting for a connection...')
        threading.Thread(target=self._wait_for_connection).start()

    def start_as_client(self):
        print('IP: ', self.SERVER_IP)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print('Waiting for a connection...')
        threading.Thread(target=self._wait_for_server).start()

    def _wait_for_server(self):
        self.client_socket.connect((self.SERVER_IP, self.SERVER_PORT))
        print(f'Connected to {self.SERVER_IP} on port {self.SERVER_PORT}')

        # self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) # testing
        self.connected = True

    def _wait_for_connection(self):
        self.client_socket, self.addr = self.server_socket.accept()
        print(f'Connected to {self.addr} on port {self.SERVER_PORT}')

    def send_string(self, message_string):
        self.client_socket.send(message_string.encode('utf-8'))

    def sendall_string(self, message_string):
        self.client_socket.sendall(message_string.encode('utf-8'))

    def receive_float(self, number_of_bytes_to_receive = 1024):
        data = self.receive(number_of_bytes_to_receive=number_of_bytes_to_receive)
        # decode the recieved data bytes which is a float
        # convert hex string to float
        data = float.fromhex(data.decode('utf-8'))
        return data

    def receive(self, number_of_bytes_to_receive = 1024):
        # non-blocking receive
        self.client_socket.setblocking(0)
        data = self.client_socket.recv(2).decode('utf-8')
        return data
    
    def close(self):
        self.client_socket.close()
        self.server_socket.close()


# main script
if __name__ == "__main__":

    com_port = input('Enter COM port (e.g. COM7 or /dev/ttyUSB0): ')

    eth_server = EthernetServer()
    artus_lite = ArtusAPI(communication_method='UART',communication_channel_identifier=com_port,
                        hand_type='right')
    # connect to hand
    artus_lite.connect()

    started = input('Is this the first time running the script after power cycle? (y/n): ')

    if started == 'y':
    # wake up
        artus_lite.wake_up()

    eth_server.start()

    while True:
        try:
            var = eth_server.receive()
            if var == '1':
                with open(os.path.join(desired_path,'data','hand_poses','grasp_example.json'),'r') as file:
                    grasp_dict = json.load(file)
                    artus_lite.set_joint_angles(grasp_dict)
            elif var == '2':
                with open(os.path.join(desired_path,'data','hand_poses','grasp_open.json'),'r') as file:
                    grasp_dict = json.load(file)
                    artus_lite.set_joint_angles(grasp_dict) 
            elif var == '3':
                artus_lite._robot_handler.robot.hand_joints['thumb_flex'].target_angle = 45
                artus_lite._robot_handler.robot.hand_joints['thumb_d2'].target_angle = 20
                artus_lite._robot_handler.robot.hand_joints['thumb_d1'].target_angle = 20

                artus_lite._communication_handler.send_data(artus_lite._command_handler.get_target_position_command(artus_lite._robot_handler.robot.hand_joints))

        except Exception as e:
            print('[Error Received] ' + e)