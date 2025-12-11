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
import logging
import math
from tracemalloc import start
from .common.ModbusMap import ModbusMap
from .commands import NewCommands
from .communication.new_communication import NewCommunication,ActuatorState,CommandType
from .robot import Robot
from .firmware_update import FirmwareUpdaterNew

class ArtusAPI_New:
    """
    This is a newer version of the ArtusAPI that has been redesigned to accomodate a more robust communication process
    as well as accomodate our newer series of hands, whereas the legacy ArtusAPI is mainly for the Artus Lite
    """
    def __init__(self,
                # communication method 
                communication_method='RS485_RTU',
                communication_channel_identifier='COM9',
                # robot 
                robot_type='artus_talos',
                hand_type='left',
                communication_frequency = 50, # hz
                logger = None,
                baudrate = 115200):

        self.control_types = {
            'position': 3,
            'velocity': 2,
            'torque': 1,
            # 'current': 0
        }

        self.control_type = self.control_types['position']

        self._communication_handler = NewCommunication(communication_method=communication_method,
                                                    logger=logger, port=communication_channel_identifier,
                                                    baudrate=baudrate)
        self._robot_handler = Robot(robot_type=robot_type,hand_type=hand_type,logger=logger)
        self._command_handler = NewCommands(num_joints=len(self._robot_handler.robot.hand_joints),logger=logger)

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.state = ActuatorState.ACTUATOR_INITIALIZING.value

        self._communication_period = 1 / communication_frequency
        self.last_time = time.perf_counter()

        self.awake = False

    def set_control_type(self,control_type:int):
        """
        Set the control type of the hand
        :param control_type: 0 for position control, 1 for velocity control, 2 for torque control
        """
        if control_type not in self.control_types.values():
            self.logger.error(f"Control type {control_type} is not valid")
            return False
        self.control_type = control_type
        return True

    def _check_awake(self):
        # if not self.awake:
        #     self.logger.warning(f'Hand not ready, send `wake_up` command')
        #     return False
        return True

    def connect(self):
        self._communication_handler.open_connection()
        time.sleep(1)
        # self.wake_up()
    
    def wake_up(self,control_type:int=0):
        """
        Wake up the hand and set the control type
        :param control_type: 0 for position control, 1 for velocity control, 2 for torque control
        """
        wake_command = self._command_handler.get_robot_start_command(control_type=control_type)

        self.control_type = control_type
        self._communication_handler.send_data(wake_command)
        self.last_time = time.perf_counter()

        # wait for hand state ready
        # if not self._communication_handler.wait_for_ready(vis=False):
        #     self.logger.error("Hand timed out waiting for ready")
        # else:
        #     self.logger.info("Hand ready")
        #     self.state = ActuatorState.ACTUATOR_IDLE
        #     self.awake = True

    def sleep(self):
        sleep_command = self._command_handler.get_sleep_command()
        self._communication_handler.send_data(sleep_command)
        self.last_time = time.perf_counter()
    
    def get_actuator_status(self):
        return self._communication_handler._check_robot_state()


    def calibrate(self,joint=0):
        if not self._check_awake():
            return
        calibrate_cmd = self._command_handler.get_calibration_command()
        if joint > 0:
            self.logger.info(f"Calibrating joint {joint}")
            calibrate_cmd.append(joint)
        
        self._communication_handler.send_data(calibrate_cmd)
        self.last_time = time.perf_counter()
        self.state = ActuatorState.ACTUATOR_CALIBRATING_STROKE.value

        # wait for hand state ready
        # if not self._communication_handler.wait_for_ready(vis=True):
        #     self.logger.error("Hand timed out waiting for ready")
        # else:
        #     self.logger.info("Hand ready")
        #     self.state = ActuatorState.ACTUATOR_IDLE

    def set_joint_angles(self, joint_angles:dict):
        """
        sends joint commands to the hand - set_joint_angles for consistency with v1 api
        :param joint_angles: dictionary of joint angles to set - can have any combination of target_angle, target_velocity, or target_torque - will be converted to the correct command based on the control type
        :return: True if the command was sent successfully, False otherwise
        """
        if not self._check_awake():
            return

        available_control = self._robot_handler.set_joint_angles(joint_angles,name=True)

        if available_control == 0:
            self.logger.warning("No valid data in joint dictionary to send")
            return False

        if (available_control & 0b1) != 0:
            set_joint_angles_cmd = self._command_handler.get_target_position_command(self._robot_handler.robot.hand_joints)
            self.wait_for_com_freq()
            self._communication_handler.send_data(set_joint_angles_cmd,CommandType.TARGET_COMMAND.value)
            self.last_time = time.perf_counter()
        # if (available_control & 0b10) != 0:
        #     set_joint_angles_cmd = self._command_handler.get_target_velocity_command(self._robot_handler.robot.hand_joints)
        #     self.wait_for_com_freq()
        #     self._communication_handler.send_data(set_joint_angles_cmd,CommandType.TARGET_COMMAND.value)
        #     self.last_time = time.perf_counter()
        # if (available_control & 0b100) != 0:
        #     set_joint_angles_cmd = self._command_handler.get_target_torque_command(self._robot_handler.robot.hand_joints)
        #     self.wait_for_com_freq()
        #     self._communication_handler.send_data(set_joint_angles_cmd,CommandType.TARGET_COMMAND.value)
        #     self.last_time = time.perf_counter()
        return True

    def _check_communication_frequency(self,last_time:float):
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
        if current_time - self.last_time < self._communication_period:
            self.logger.debug("Command not sent. Communication frequency is too high.")
            return False
        return True

    def wait_for_com_freq(self):
        while not self._check_communication_frequency(self.last_time):
            time.sleep(0.001)
        return True
    
    def set_home_position(self):
        if not self._check_awake():
            return
        # create hand joint dict with zero value angles
        self._robot_handler.set_home_position()
        robot_set_home_position_cmd = self._command_handler.get_target_position_command(self._robot_handler.robot.hand_joints)
        if not self._check_communication_frequency(self.last_time):
            return False
        self._communication_handler.send_data(robot_set_home_position_cmd,CommandType.TARGET_COMMAND.value)
        self.last_time = time.perf_counter()
    
    def get_joint_angles(self,start_reg=ModbusMap().modbus_reg_map['feedback_position_start_reg']):
        """
        named get_joint_angles for consistency with v1 api
        actually should be `get_feedback`
        covers all feedback types - position, torque, velocity, temperature based on start_reg parameter
        
        :param start_reg: according to modbusmap
        """
        if not self._check_awake():
            return
        # check starting reg
        start_reg_confirmed = False
        for key,value in ModbusMap().modbus_reg_map:
            if value == start_reg:
                start_reg_confirmed = key
                break

        if start_reg_confirmed is not None:
            amount_data = ModbusMap().data_type_multiplier_map[start_reg_confirmed] * self._robot_handler.robot.number_of_joints
        else:
            raise ValueError('Start Register is not recognized -- see ModbusMap.pdf in robot/$robot$/data')

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_confirmed)

        # populate hand joint dict based on robot
        self.logger.info(self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_confirmed))

    def get_joint_torques(self):
        """
        Get the joint torques from the hand
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_torque_start_reg']
        start_reg_key = 'feedback_torque_start_reg'

        amount_data = ModbusMap().data_type_multiplier_map[start_reg_key] * self._robot_handler.robot.number_of_joints

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        # populate hand joint dict based on robot
        self.logger.info(self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_key))

    def get_joint_speeds(self):
        """
        Get the joint speeds from the hand
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_velocity_start_reg']
        start_reg_key = 'feedback_velocity_start_reg'

        amount_data = ModbusMap().data_type_multiplier_map[start_reg_key] * self._robot_handler.robot.number_of_joints

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        # populate hand joint dict based on robot
        self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_key)


    ### NOT IMPLEMENTED YET ###
    def get_joint_temperatures(self):
        """
        Get the joint temperatures from the hand
        :todo: work in progress - not implemented yet
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_temperature_start_reg']
        start_reg_key = 'feedback_temperature_start_reg'

        amount_data = ModbusMap().data_type_multiplier_map[start_reg_key] * self._robot_handler.robot.number_of_joints

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        # populate hand joint dict based on robot
        self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_key)

    def get_hand_feedback_data(self):
        """
        Get all feedback data from the hand that is available
        """
        if not self._check_awake():
            return

        for feedback_type in self._robot_handler.robot.available_feedback_types:
            self.get_joint_angles(start_reg=ModbusMap().modbus_reg_map[feedback_type])

    # for compatibility
    def get_streamed_joint_angles(self,dat_type=0):
        self.logger.error(f"get_streamed_joint_angles is not implemented for the {self._robot_handler.robot.robot_type}")
        return None
    
    def get_robot_status(self):
        if not self._check_awake():
            return
        feedback_data = self._communication_handler.receive_data()

    def update_firmware(self,file_location=None,drivers_to_flash=None):
        
        if file_location is None or (isinstance(file_location, str) and not file_location.endswith('.bin')):
            file_location = input('Please enter absolute filepath of binary file: ')

        self._firmware_updater = FirmwareUpdaterNew(communication_handler=self._communication_handler,
                                                    command_handler=self._command_handler,
                                                    file_location=file_location,
                                                    logger=self.logger)
        
        fw_size = self._firmware_updater.get_bin_file_info()

        # get driver to flash
        if drivers_to_flash == None:
            while drivers_to_flash is None or drivers_to_flash not in range(0, 7):
                drivers_to_flash = int(input(
                    f'''
                    Please Enter Drivers to Flash:
                    0-5: Specific Actuator mapped to joint number
                    6: All Actuators
                    '''
                    ))
        
        # send commmand
        firmware_cmd = self._command_handler.get_firmware_command(drivers_to_flash)
        self._communication_handler.send_data(firmware_cmd) # sent firmware upload command to command register
        self.last_time = time.perf_counter()

        # send firmware data
        self._firmware_updater.update_firmware_piecewise(fw_size)

        # wait for hand state ready
        # if not self._communication_handler.wait_for_ready(vis=False):
        #     self.logger.error("Hand timed out waiting for ready")
        # else:
        #     self.logger.info("Hand ready")
            