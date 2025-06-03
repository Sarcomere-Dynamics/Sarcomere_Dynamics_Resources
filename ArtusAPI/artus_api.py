"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""
import sys
import logging
from pathlib import Path
# Current file's directory
current_file_path = Path(__file__).resolve()
# Add the desired path to the system path
desired_path = current_file_path.parent.parent
sys.path.append(str(desired_path))
print(desired_path)



from .communication import Communication,STARTUP_ACK,NORMAL_ACK
from .commands import Commands
from .robot import Robot
from .firmware_update import FirmwareUpdater
import time

class ArtusAPI:

    def __init__(self,
                #  communication
                communication_method='UART',
                communication_channel_identifier='COM9',
                #  robot
                robot_type='artus_lite',
                hand_type ='left',
                stream = False,
                communication_frequency = 50, # hz
                logger = None,
                reset_on_start = 0,
                baudrate = 921600,
                awake = False
                ):
        """
        ArtusAPI class controls the communication and control of between a system and an Artus Hand by Sarcomere Dynamics Inc. This file contains the high-level calls that
        are used to control the hand. The low-level calls are separated by robot, command and communication classes.
        :communication_method: communication method that is supported on the Artus Hand, see Robot folder for supported methods. Default is UART over USBC
            - UART (USBC or RS485), CAN
        :communication_channel_identifier: channel identifier for the communication method. Usually a COM Port
        :robot_type: name of the series of robot hand. See Robot folder for list of robots
        :hand_type: left or right
        :stream: Whether feedback data should be streamed (True) or require polling (False)
        :communication_frequency: maximum frequency to stream data to the device and feedback data from the device
        :logger: python logger settings to inherit
        :reset_on_start: If hand is powered off in a non-opened state, or software is stopped in a non-opened state, this value should be set to `1` to reduce risk of jamming. May require a calibration.
        :baudrate: Required for difference between serial over USBC (921600) and serial over RS485 (115200) when connected to a UR arm
        :awake: False by default - if the hand is already in a ready state (LED is green) when starting or restarting a control script, set awake to `True` to bypass resending the `wake_up` function. Sending the `wake_up` function when the hand IS NOT in an open state will cause it to lose calibration
        """

        self._communication_handler = Communication(communication_method=communication_method,
                                                  communication_channel_identifier=communication_channel_identifier,baudrate=baudrate,robot_type=robot_type)
        self._command_handler = Commands(reset_on_start=reset_on_start)
        self._robot_handler = Robot(robot_type = robot_type,
                                   hand_type = hand_type)
        
        self._last_command_sent_time = time.perf_counter()
        self.last_streamed_feedback_time = time.perf_counter()
        self._communication_frequency = communication_frequency
        self._communication_period = 1 / self._communication_frequency
        self._communication_period_ms = self._communication_period * 1000
        self.stream = stream
        self.awake = awake

        # only used during streaming
        self.last_command_recv_time = time.perf_counter()

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
    
    # communication setup
    def connect(self):
        """
        Open a connection to the Artus Hand and send a wake command to initiate communication
        """
        self._communication_handler.open_connection()

        time.sleep(1)
        # send wake command with it
        if not self.awake:
            self.wake_up()
        return
    
    def disconnect(self):
        """
        Close a connection to the Artus Hand
        """
        return self._communication_handler.close_connection()
    
    # robot states
    def wake_up(self):
        """
        Wake-up the Artus Hand by sending an initialization command to the hand
        """
        print(f"communication period = {self._communication_period_ms} ms")
        robot_wake_up_command = self._command_handler.get_robot_start_command(self.stream,int(self._communication_period_ms)) # to ms for masterboard
        self._communication_handler.send_data(robot_wake_up_command)

        # wait for data back
        if self._communication_handler.wait_for_ack(value=STARTUP_ACK):
            self.logger.info(f'Finished calibration')
        else:
            self.logger.warning(f'Error in calibration')
        self.awake = True

    def sleep(self):
        """
        Put the Artus Hand to sleep by sending a sleep command to the hand which
        initiates a shutdown sequence. This command will tell the hand to save it's current
        positions to non-volatile memory and shut down the motors. The LED will turn yellow and
        now be able to be powered off.
        """
        robot_sleep_command = self._command_handler.get_sleep_command()
        return self._communication_handler.send_data(robot_sleep_command)
    
    def calibrate(self,joint=0,calibration_type=0):
        """
        Calibrate the Artus Hand
        
        Parameters:
        joint (int): Joint to calibrate. 0 for all joints, 1-16 for specific joints mapping to joint map
        calibration_type (int): Type of calibration. 
            0 for a soft reset (i.e. fingers will go to open endstop)
            1 for a hard reset, finding both open and close endstops
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        robot_calibrate_command = self._command_handler.get_calibration_command()
        robot_calibrate_command[1] = joint
        robot_calibrate_command[2] = calibration_type
        self._communication_handler.send_data(robot_calibrate_command)

        # wait for data back
        if self._communication_handler.wait_for_ack(visual=True):
            self.logger.info(f'Finished calibration')
        else:
            self.logger.warning(f'Error in calibration')
    

    # robot control
    def set_joint_angles(self, joint_angles:dict,name=False):
        """
        Set joint angle targets and speed values to the Artus Hand
        
        Parameters:
        :joint_angles: dictionary of input angles and input speeds. See the grasps in the hand_data folder for accepted structure
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        self._robot_handler.set_joint_angles(joint_angles=joint_angles,name=name)
        robot_set_joint_angles_command = self._command_handler.get_target_position_command(self._robot_handler.robot.hand_joints)
        # check communication frequency
        if not self._check_communication_frequency(self._last_command_sent_time):
            return False
        return self._communication_handler.send_data(robot_set_joint_angles_command)
    
    def set_zero_manual_calibration(self):
        """
        Set the zero position of the joints used in manual calibration
        This is important to have the fingers look centered in an open/neutral position as we are working
        on the calibration process

        The hand will need to be power cycled after this function is called to take effect
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        robot_set_zero_command = self._command_handler.get_set_zero_command()
        self._communication_handler.send_data(robot_set_zero_command)

        time.sleep(1)

    
    def set_home_position(self):
        """
        sends the joints to home positions (0) which opens all the joints of the Artus Hand
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        
        self._robot_handler.set_home_position()
        robot_set_home_position_command = self._command_handler.get_target_position_command(hand_joints=self._robot_handler.robot.hand_joints)
        # check communication frequency
        if not self._check_communication_frequency(self._last_command_sent_time):
            return False
        return self._communication_handler.send_data(robot_set_home_position_command)

    def _check_communication_frequency(self,last_command_time):
        """
        checks if the time between the last command and the current command is less than the communication period
        Necessary so that the messages stay in sync

        Parameters:
        :last_command_time: time of the last command

        Returns:
        :True if the time between the last command and the current command is greater than the communication period
        :False if the time between the last command and the current command is less than the communication period
        """
        current_time = time.perf_counter()
        if current_time - last_command_time < self._communication_period:
            self.logger.warning("Command not sent. Communication frequency is too high.")
            return False
        last_command_time = current_time
        return True

    # robot feedback
    def _receive_feedback(self):
        """
        Send a request for feedback data and receive feedback data

        Returns:
        :feedback_command: feedback data list from the hand
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        
        feedback_command = self._command_handler.get_states_command()
        self._communication_handler.send_data(feedback_command)
        # test
        time.sleep(0.001)
        return self._communication_handler.receive_data()
    
    def get_joint_angles(self):
        """
        Populate feedback fields in self._robot_handler.hand_joints dict

        Returns:
        :tuple: (ack, angles, velocities, temperatures)
            ack: acknowledgement from the hand
            angles: list of joint angles
            velocities: list of joint velocities
            temperatures: list of joint temperatures
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        
        feedback_command = self._receive_feedback()
        if not self._check_communication_frequency(self._last_command_sent_time):
            return None
        joint_angles = self._robot_handler.get_joint_angles(feedback_command)
        if joint_angles is None:
            return None
        
        angles = joint_angles[1][0:16]

        if self._robot_handler.robot_type == 'artus_lite':
            # separate joint angles into 3 lists    
            velocities = joint_angles[1][16:32]
            temperatures = joint_angles[1][32:48]
            # print(joint_angles)
            return joint_angles[0],angles,velocities,temperatures
        
        elif self._robot_handler.robot_type == 'artus_lite_plus':
            # separate into lists and concat decimals
            # angles = joint_angles[1][0:16]
            forces = [round(force, 4) for force in joint_angles[1][16:]]
            return joint_angles[0],angles,forces
    
    # robot feedback stream
    def get_streamed_joint_angles(self):
        """
        Populate feedback fields in self._robot_handler.hand_joints dict without sending a request for feedback data
        This is used for real-time streaming of data for the Artus Hand
        Returns:
        :tuple: (ack, feedback list)
            ack: acknowledgement from the hand
            feedback list: list of joint angles, velocities, and temperatures
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        
        if not self._check_communication_frequency(self.last_streamed_feedback_time):
            return None
        else:
            feedback_command = self._communication_handler.receive_data()
            if not feedback_command:
                print(f'feedback is none')
                return None
            joint_angles = self._robot_handler.get_joint_angles(feedback_command)
        return joint_angles

    def update_firmware(self,upload_flag='y',file_location=None,drivers_to_flash=0):
        """
        send a firmware update to the actuators

        Parameters:
        :upload_flag: whether to upload a new firmware file or not. Default is 'y'
        :file_location: location of the firmware file. Default is None
        :drivers_to_flash: which drivers to flash. Default is 0 (all motor drivers)
            0 - all motor drivers
            1-8 - specific motor driver
            9 - peripheral controller
        """
        file_path = None
        fw_size  = 0
        # input to upload a new file
        if upload_flag == None:
            upload_flag = input(f'Uploading a new BIN file? (y/n)  :  ')
        upload = True

            
        # Create new firmware updater instance
        self._firmware_updater = FirmwareUpdater(self._communication_handler,
                                        self._command_handler)
        
        if upload_flag == 'n' or upload_flag == 'N':
            self._firmware_updater.file_location = 'not empty'
            upload = False
        else:
            if file_location is None: 
                file_location = input('Please enter binfile absolute path:  ')
            self._firmware_updater.file_location = file_location

            fw_size = self._firmware_updater.get_bin_file_info()
        
        # set which drivers to flash should be 1-8
        if drivers_to_flash == None:
            drivers_to_flash = int(input(f'Which drivers would you like to flash? \n0: All Actuators \n1-8 Specific Actuator \n9: Peripheral Controller \nEnter: '))

        if drivers_to_flash == 0:
            
            for i in range(1,9):
                print(f'Flashing driver {i}')
                time.sleep(1)
                self.update_firmware_single_driver(i,fw_size,upload)
                if upload:
                    self._firmware_updater.update_firmware(fw_size)
                    upload = False

                if not self._communication_handler.wait_for_ack(25,True):
                    print(f'Error flashing driver {i}')
                    return
        else:
            self.update_firmware_single_driver(drivers_to_flash,fw_size,upload)
            if upload:
                self._firmware_updater.update_firmware(fw_size)
       
            print(f'Flashing driver {drivers_to_flash}')
            self._communication_handler.wait_for_ack(25,True)
        
        print(f'Power Cycle the device to take effect')

    def update_firmware_single_driver(self,actuator_number,fw_size,upload):
        """
        update firmware for a single driver

        Parameters:
        :actuator_number: which actuator to update
        :fw_size: size of the firmware file
        :upload: whether to upload a new firmware file or not
        """
        self._communication_handler.send_data(self._command_handler.get_firmware_command(fw_size,upload,actuator_number))

    def request_joint_and_motor(self):
        """
        user facing request for joint and motor used in reset and hard close functions
        :return: joint and motor number
        """
        j,m = None,None
        while True:
            j = int(input(f'Enter Joint to reset: '))
            if 0 <= j <= 15:
                break
            else:
                print(f'Invalid joint number, please try again')
        while True:
            m = int(input(f'Enter Motor to reset: '))
            if 0 <= m <= 2:
                break
            else:
                print(f'Invalid motor number, please try again')
        return j,m
    

    def reset(self,j=None,m=None):
        """
        Pulse the motor open, used if finger is "jammed" in close state

        Parameters:
        :j: joint number to reset
        :m: motor number to reset
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        if j is None or m is None:
            j,m = self.request_joint_and_motor()
        
        reset_command = self._command_handler.get_locked_reset_low_command(j,m)
        self._communication_handler.send_data(reset_command)
    
    def hard_close(self,j=None,m=None):
        """
        Pulse the motor open - used if finger is "jammed" in open state

        Parameters:
        :j: joint number to reset
        :m: motor number to reset
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        if j is None or m is None:
            j,m = self.request_joint_and_motor()
        
        hard_close = self._command_handler.get_hard_close_command(j,m)
        self._communication_handler.send_data(hard_close)

    def update_param(self):
        """
        Parameter update, used to change the communication method which must be within the available options.
        Hand will require a power cycle to take effect
        :return: None
        """
        com = None
        while com not in ['UART','CAN','RS485','WIFI']:
            com = input('Enter Communication Protocol you would like to change to (default: UART, CAN, RS485, WIFI): ')
        if com == 'CAN':
            feed = None
            while feed not in ['P','C','ALL']:
                feed = input('Enter feedback information (P: Positions only, C: Positions and Force, ALL: Position, force and temperature): ')
        else:
            feed = None
        command = self._command_handler.update_param_command(com,feed)
        self._communication_handler.send_data(command)

        # wait for data back
        if self._communication_handler.wait_for_ack():
            self.logger.info(f'Finished Updating Param')
        else:
            self.logger.warning(f'Error in updating Param')

    def save_grasp_onhand(self,index=1):
        """
        function to save a grasp on the Artus Hand in non-volatile memory to be called.
        Uses the last set joint angles and velocities to save the grasp that are in the robot.hand_joints dict

        Parameters:
        Default index is 1, value can be 1-6
        """
        command = [0]*32
        for joint,data in self._robot_handler.robot.hand_joints.items():
            command[data.index] = data.target_angle
            command[data.index+16] = data.velocity
        
        self._communication_handler.send_data(self._command_handler.get_save_grasp_command(index,command))
        feedback = None
        while not feedback:
            ack,feedback = self._communication_handler.receive_data()

            if feedback is not None:
                print(feedback[:33])

    def get_saved_grasps_onhand(self):
        """
        Function to print saved grasps on the Artus non-volatile memory. 
        Prints 6 grasps
        """
        self._communication_handler.send_data(self._command_handler.get_return_grasps_command())

        for i in range(6):
            feedback = None
            while not feedback:
                ack,feedback = self._communication_handler.receive_data()

                if feedback is not None:
                    print(feedback[:33])

    def execute_grasp(self,index=1):
        """
        Sends a command to the Artus hand that executes a grasp position from the non-volatile memory grasp array
        """
        self._communication_handler.send_data(self._command_handler.get_execute_grasp_command(index))
        feedback = None
        while not feedback:
            ack,feedback = self._communication_handler.receive_data()

            if feedback is not None:
                print(feedback[:33])
    
    def wipe_sd(self):
        """
        wipe sd card and reset with factory default settings
        Requires a power cycle to take effect
        """
        self._communication_handler.send_data(self._command_handler.get_wipe_sd_command())
        feedback = None
        while not feedback:
            ack,feedback = self._communication_handler.receive_data()


def test_artus_api():
    artus_api = ArtusAPI()
    artus_api.connect()
    artus_api.wake_up()
    artus_api.calibrate()
    artus_api.set_home_position()
    time.sleep(2)
    artus_api.disconnect()

# script entry points
def main():
    try:
        # import specific to the cli entry point
        import argparse
        
        parser = argparse.ArgumentParser(
            description="Artus API CLI Tool"
        )
        # add required arguments
        parser.add_argument('-p','--port',required=True,help="required com port (COMx) or (/dev/ttyUSBx)")
        parser.add_argument('-r','--robot',default='artus_lite',help="Robot type",choices=['artus_lite','artus_lite_plus'])
        parser.add_argument('-s','--side',default='right',choices=['left','right'],help='specify hand side, left or right')
        # parser.add_argument('-b','--baudrate',default=921600,help='specify baudrate',choices=[921600,115200])
        args = parser.parse_args()

        myrobot = ArtusAPI(robot_type=args.robot, hand_type=args.side, communication_channel_identifier=args.port,baudrate=921600)
        myrobot.connect()
        time.sleep(1)

        while(1):
            input_command = input('Enter command: ')
            if input_command == 'c1':
                myrobot.calibrate(calibration_type=1)
            elif input_command == 'c':
                myrobot.calibrate()
            elif input_command == 'h':
                myrobot.set_home_position()
            elif input_command == 'm':
                grasp_dict = {'thumb_spread': {'target_angle': 30}, 'thumb_d2': {'target_angle': 30}, 'thumb_flex': {'target_angle': 30}, 
                              'index_d2': {'target_angle': 30}, 'index_flex': {'target_angle': 30},
                              'middle_d2': {'target_angle': 30}, 'middle_flex': {'target_angle': 30}, 
                              'ring_d2': {'target_angle': 30}, 'ring_flex': {'target_angle': 30},
                              'pinky_d2': {'target_angle': 30}, 'pinky_flex': {'target_angle': 30}}
                myrobot.set_joint_angles(grasp_dict)
            elif input_command == 'q':
                myrobot.sleep()
                time.sleep(1)
                myrobot.disconnect()
                quit()
            elif input_command == 'r':
                j = int(input('Enter joint number: '))
                m = int(input('Enter motor number: '))
                myrobot.reset(j,m)
            else:
                print(f'Invalid command: {input_command}')
            time.sleep(1)

    except Exception as e:
        print(f"An error occurred: {str(e)}")


def main_flash():
    try:
        # import specific to the cli entry point
        import argparse
        import requests
        import os
        import json
        import base64
        import esptool

        bin_paths = {
        "actuator_64": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/actuator_64.txt",
        "peripheral_64": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/peripheral_64.txt",
        "peripheral_plus_64": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/peripheral_plus_64.txt",

        "master_64_right": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/master_right_64.txt",
        "master_plus_64_right": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/master_plus_64.txt",

        "master_64_left": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/master_left_64.txt",
        "master_plus_64_left": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/master_plus_left_64.txt",


        "master_partitions_64": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/master_partitions_64.txt",
        "master_plus_partitions_64": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/master_plus_partitions_64.txt",
        
        "master_bootapp0_64": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/master_plus_bootapp_64.txt",
        "master_bootloader_64": "https://gist.githubusercontent.com/SDRyanLee/ad8bbe17164c74e6417d1e2d4d0843d2/raw/master_bootloader_64.txt"
        }
        
        parser = argparse.ArgumentParser(
            description="Artus API CLI Flash Tool"
        )

        # add required arguments
        parser.add_argument('-p','--port',required=True,help="required com port (COMx) or (/dev/ttyUSBx)")
        parser.add_argument('-r','--robot',default='artus_lite',help="Robot type",choices=['artus_lite','artus_lite_plus'])
        parser.add_argument('-s','--side',default='right',choices=['left','right'],help='specify hand side, left or right')
        # parser.add_argument('-b','--baudrate',default=921600,help='specify baudrate',choices=[921600,115200])
        args = parser.parse_args()

        type_flash = None
        driver_to_flash = None
        bootapp_path = None
        partitions_path = None
        bootloader_path = None
        file_location = None

        # get type of flash
        while type_flash not in ['actuator','peripheral','master']:
            type_flash = input('Enter subsystem to flash (actuator, peripheral, master): ')

        if type_flash == 'actuator':
            file_location = bin_paths['actuator_64']
            driver_to_flash = 0
            print('Flashing actuator')
        elif type_flash == 'peripheral':
            if args.robot == 'artus_lite':
                file_location = bin_paths['peripheral_64']
            elif args.robot == 'artus_lite_plus':
                file_location = bin_paths['peripheral_plus_64']
            driver_to_flash = 9
            print('Flashing peripheral')

        elif type_flash == 'master':
            print(f'flashing master with parameters: {args.robot} {args.side}')
            if args.robot == 'artus_lite':
                if args.side == 'right':
                    file_location = bin_paths['master_64_right']
                elif args.side == 'left':
                    file_location = bin_paths['master_64_left']
                partitions_path = bin_paths['master_partitions_64']

            elif args.robot == 'artus_lite_plus':
                if args.side == 'right':
                    file_location = bin_paths['master_plus_64_right']
                elif args.side == 'left':
                    file_location = bin_paths['master_plus_64_left']
                partitions_path = bin_paths['master_plus_partitions_64']
            
            bootapp_path = bin_paths['master_bootapp0_64']
            bootloader_path = bin_paths['master_bootloader_64']
            print('Flashing master')
        # write files
        # Download and decode base64 firmware file
        print(f"Downloading firmware from firmware file")
        response = requests.get(file_location)
        if response.status_code != 200:
            print(f"Error: Failed to download firmware from {file_location}. Status code: {response.status_code}")
        decoded_firmware = base64.b64decode(response.text)
        
        # Write decoded firmware to flash.bin
        with open('flash.bin', 'wb') as f:
            f.write(decoded_firmware)

        # For master firmware, also download and decode bootloader files
        if type_flash == 'master':
            print(f"Downloading bootapp from bootapp file")
            # Download and decode bootapp
            response = requests.get(bootapp_path) 
            if response.status_code != 200:
                print(f"Error: Failed to download bootloader from {bootapp_path}. Status code: {response.status_code}")
            decoded_bootapp = base64.b64decode(response.text)
            with open('bootapp0.bin', 'wb') as f:
                f.write(decoded_bootapp)

            # Download and decode partitions
            print(f"Downloading partitions from partitions file")
            response = requests.get(partitions_path)
            if response.status_code != 200:
                print(f"Error: Failed to download partitions from {partitions_path}. Status code: {response.status_code}")
            decoded_partitions = base64.b64decode(response.text)
            with open('partitions.bin', 'wb') as f:
                f.write(decoded_partitions)
                
            # Download and decode bootloader
            print(f"Downloading bootloader from bootloader file")
            response = requests.get(bootloader_path)
            if response.status_code != 200:
                print(f"Error: Failed to download bootloader from {bootloader_path}. Status code: {response.status_code}")
            decoded_bootloader = base64.b64decode(response.text)
            with open('bootloader.bin', 'wb') as f:
                f.write(decoded_bootloader)
            

        # flash through api
        if type_flash != 'master':
            myrobot = ArtusAPI(robot_type=args.robot, hand_type=args.side, communication_channel_identifier=args.port,baudrate=921600)
            myrobot.connect()
            print('Connected to robot')
            time.sleep(1)

            file_location = 'flash.bin'
            myrobot.update_firmware(upload_flag='y',file_location=file_location,drivers_to_flash=driver_to_flash)
            time.sleep(1)
            
            myrobot.disconnect()
            print('Disconnected from robot')

        else:
           
            # Build esptool command arguments
            cmd_args = [
                '--chip', 'esp32s3',
                '--port', args.port,
                '--baud', '921600',
                '--before', 'default_reset',
                '--after', 'hard_reset',
                'write_flash',
                '-z',
                '--flash_mode', 'keep',
                '--flash_freq', 'keep',
                '--flash_size', 'keep',
                '0x0', 'bootloader.bin',
                '0x8000', 'partitions.bin', 
                '0xe000', 'bootapp0.bin',
                '0x10000', 'flash.bin'
            ]

            # Run esptool flash command with verbose output
            # cmd_args.append('--verbose')
            esptool.main(cmd_args)

            # Clean up temporary bootloader files
            os.remove('bootloader.bin')
            os.remove('partitions.bin')
            os.remove('bootapp0.bin')

        # delete bin file
        time.sleep(1)
        os.remove('flash.bin')
        print('Flash complete')

        print('Done')

    except Exception as e:
        import traceback
        print("An error occurred:")
        traceback.print_exc()
        # Clean up any remaining temporary files
        temp_files = ['flash.bin', 'bootloader.bin', 'partitions.bin', 'bootapp0.bin']
        for file in temp_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

if __name__ == "__main__":
    test_artus_api()
