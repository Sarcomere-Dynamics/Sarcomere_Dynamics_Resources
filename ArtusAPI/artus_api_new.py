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
from .common.ModbusMap import ModbusMap
from .commands import NewCommands
from .communication.new_communication import NewCommunication,ActuatorState,CommandType
from .robot import Robot

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
        self._communication_handler = NewCommunication(communication_method=communication_method,
                                                    logger=logger, port=communication_channel_identifier,
                                                    baudrate=baudrate)
        self._robot_handler = Robot(robot_type=robot_type,hand_type=hand_type)
        self._command_handler = NewCommands(num_joints=len(self._robot_handler.robot.hand_joints),logger=logger)

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.state = ActuatorState.ACTUATOR_INITIALIZING

        self._communication_period = 1 / communication_frequency
        self.last_time = time.perf_counter()

        self.awake = False

    def _check_awake(self):
        if not self.awake:
            self.logger.warning(f'Hand not ready, send `wake_up` command')
            return False
        return True

    def connect(self):
        self._communication_handler.open_connection()
        time.sleep(1)
        self.wake_up()
    
    def wake_up(self):
        wake_command = self._command_handler.get_robot_start_command()
        self._communication_handler.send_data(wake_command)

        # wait for hand state ready
        if not self._communication_handler.wait_for_ready(vis=True):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")
            self.state = ActuatorState.ACTUATOR_IDLE
            self.awake = True

    def calibrate(self,joint=0):
        if not self._check_awake():
            return
        calibrate_cmd = self._command_handler.get_calibration_command()
        if joint > 0:
            self.logger.info(f"Calibrating joint {joint}")
            calibrate_cmd.append(joint)
        
        self._communication_handler.send_data(calibrate_cmd)
        self.state = ActuatorState.CALIBRATING_STROKE

        # wait for hand state ready
        if not self._communication_handler.wait_for_ready(vis=True):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")
            self.state = ActuatorState.ACTUATOR_IDLE

    def set_joint_angles(self, joint_angles:dict):
        if not self._check_awake():
            return
        self._robot_handler.set_joint_angles(joint_angles)
        set_joint_angles_cmd = self._command_handler.get_target_position_command(self._robot_handler.robot.hand_joints)
        self._communication_handler.send_data(set_joint_angles_cmd)

        # wait for hand state ready
        if not self._communication_handler.wait_for_ready(vis=True):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")

        if not self._check_communication_frequency(0):
            return False
        
        return self._communication_handler.send_data(set_joint_angles_cmd,CommandType.TARGET_COMMAND.value)

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
        if current_time - last_time < self._communication_period:
            self.logger.debug("Command not sent. Communication frequency is too high.")
            return False
        self.last_time = current_time
        return True
    
    def set_home_position(self):
        if not self._check_awake():
            return
        # create hand joint dict with zero value angles
        self._robot_handler.set_home_position()
        robot_set_home_position_cmd = self._command_handler.get_target_position_command(self._robot_handler.robot.hand_joints)
        if not self._check_communication_frequency(0):
            return False
        return self._communication_handler.send_data(robot_set_home_position_cmd,CommandType.TARGET_COMMAND.value)

    def get_joint_angles(self,dat_type=0):
        if not self._check_awake():
            return
        # only get status of hand
        if dat_type == 0:
            start_reg = ModbusMap().modbus_reg_map['feedback_register']
            amount_data = math.ceil(self.num_joints/2) + 1
        elif dat_type == 1:
            start_reg = ModbusMap().modbus_reg_map['feedback_register']
            amount_data = math.ceil(self.num_joints/2) + 1 + self.num_joints*2
        elif dat_type == 2:
            start_reg = ModbusMap().modbus_reg_map['feedback_torque_start_reg']
            amount_data = self.num_joints*2
        elif dat_type == 3:
            start_reg = ModbusMap().modbus_reg_map['feedback_temperature_start_reg']
            amount_data = math.ceil(self.num_joints/2)
        else:
            raise ValueError("Invalid data type")

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        status_data,decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data)

        # populate hand joint dict based on robot
        self._robot_handler.get_joint_angles(decoded_feedback_data,dat_type)
    
    # for compatibility
    def get_streamed_joint_angles(self,dat_type=0):
        return self.get_joint_angles(dat_type)
    
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

        # send firmware data
        self._firmware_updater.update_firmware(fw_size)

        # wait for hand state ready
        if not self._communication_handler.wait_for_ready(vis=True):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")
            