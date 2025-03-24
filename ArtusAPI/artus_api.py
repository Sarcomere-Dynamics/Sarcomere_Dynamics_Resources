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



from .communication import Communication
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
                communication_frequency = 200, # hz
                logger = None,
                reset_on_start = 0,
                baudrate = 921600,
                awake = False
                ):
        """
        ArtusAPI class controls the communication and control of between a system and an Artus Hand by Sarcomere Dynamics Inc.
        :communication_method: communication method that is supported on the Artus Hand, see Robot folder for supported methods. Default is UART over USBC
        :communication_channel_identifier: channel identifier for the communication method. Usually a COM Port
        :robot_type: name of the series of robot hand. See Robot folder for list of robots
        :hand_type: left or right
        :stream: Whether feedback data should be streamed (True) or require polling (False)
        :communication_frequency: maximum frequency to stream data to the device and feedback data from the device
        :logger: python logger settings to inherit
        :reset_on_start: If hand is powered off in a non-opened state, or software is stopped in a non-opened state, this value should be set to `1` to reduce risk of jamming. May require a calibration.
        :baudrate: Required for difference between serial over USBC (921600) and serial over RS485 (115200)
        :awake: False by default - if the hand is already in a ready state (LED is green) when starting or restarting a control script, set awake to `True` to bypass resending the `wake_up` function. Sending the `wake_up` function when the hand IS NOT in an open state will cause it to lose calibration
        """

        self._communication_handler = Communication(communication_method=communication_method,
                                                  communication_channel_identifier=communication_channel_identifier,baudrate=baudrate)
        self._command_handler = Commands(reset_on_start=reset_on_start)
        self._robot_handler = Robot(robot_type = robot_type,
                                   hand_type = hand_type)
        
        self._last_command_sent_time = time.perf_counter()
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
        Open a connection to the Artus Hand
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
        Wake-up the Artus Hand
        """
        print(f"communication period = {self._communication_period_ms} ms")
        robot_wake_up_command = self._command_handler.get_robot_start_command(self.stream,int(self._communication_period_ms)) # to ms for masterboard
        self._communication_handler.send_data(robot_wake_up_command)

        # wait for data back
        if self._communication_handler.wait_for_ack():
            self.logger.info(f'Finished calibration')
        else:
            self.logger.warning(f'Error in calibration')
        self.awake = True

        # get current position of the hand and set the last target positions to this value
        # while True:
        #     joint_angles = self.get_joint_angles()
        #     time.sleep(1)
        #     if joint_angles is not None:
        #         break
        
        # for joint,data in self._robot_handler.robot.hand_joints.items():
        #     data.target_angle = data.feedback_angle

    def sleep(self):
        """
        Sleep the Artus Hand
        """
        robot_sleep_command = self._command_handler.get_sleep_command()
        return self._communication_handler.send_data(robot_sleep_command)
    
    def calibrate(self,joint=0,calibration_type=0):
        """
        Calibrate the Artus Hand
        :joint: joint to calibrate, 0 for all joints
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
    def set_joint_angles(self, joint_angles:dict):
        """
        Set joint angle targets and speed values to the Artus Hand
        :joint_angles: dictionary of input angles and input speeds
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        self._robot_handler.set_joint_angles(joint_angles=joint_angles,name=False)
        robot_set_joint_angles_command = self._command_handler.get_target_position_command(self._robot_handler.robot.hand_joints)
        # check communication frequency
        if not self._check_communication_frequency(self._last_command_sent_time):
            return False
        return self._communication_handler.send_data(robot_set_joint_angles_command)
    
    def set_zero_manual_calibration(self):
        """
        Set the zero position of the joints used in internal calibration
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        robot_set_zero_command = self._command_handler.get_set_zero_command()
        self._communication_handler.send_data(robot_set_zero_command)
    
    def set_home_position(self):
        """
        sends the joints to home positions (0) which opens the Artus Hand
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
        check if the communication frequency is too high
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
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        
        feedback_command = self._receive_feedback()
        joint_angles = self._robot_handler.get_joint_angles(feedback_command)
        if joint_angles is None:
            return None
        # separate joint angles into 3 lists
        angles = joint_angles[1][0:16]
        velocities = joint_angles[1][16:32]
        temperatures = joint_angles[1][32:48]
        # print(joint_angles)
        return joint_angles[0],angles,velocities,temperatures
    
    # robot feedback stream
    def get_streamed_joint_angles(self):
        """
        Populate feedback fields in self._robot_handler.hand_joints dict
        """
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return
        
        if not self._check_communication_frequency(self.last_command_recv_time):
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
        send firmware update to the actuators
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
        """
        self._communication_handler.send_data(self._command_handler.get_firmware_command(fw_size,upload,actuator_number))

    def request_joint_and_motor(self):
        """
        request joint and motor from user
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
        Reset a joint back to it's open state, used if finger is "jammed" in close state
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
        drive a joint partially closed - used if finger is "jammed" in open state
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
        Parameter update, used to change the communication method
        """
        com = None
        while com not in ['UART','CAN','RS485']:
            com = input('Enter Communication Protocol you would like to change to (default: UART, CAN, RS485): ')
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
        Defeault index is 1, value can be 1-6
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

if __name__ == "__main__":
    test_artus_api()
