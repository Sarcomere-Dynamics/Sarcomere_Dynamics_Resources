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
import signal
import math
import ArtusAPI.common.SlaveIDMap as slave_ID_map

from enum import Enum
from tracemalloc import start
from .common.ModbusMap import ModbusMap
# from .common.SlaveIDMap import expected_slave_id
from .commands import NewCommands
from .communication.new_communication import NewCommunication,ActuatorState,CommandType
from .robot import Robot
from .firmware_update import FirmwareUpdaterNew

# trajectory returns are the return values for the trajectory enum
class TrajectoryReturn(Enum):
    TRAJECTORY_RUNNING = 0
    TRAJECTORY_STOPPED = 1
    TRAJECTORY_COMPLETE = 2

class ArtusAPI_V2:
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
                hand_type='right',
                communication_frequency = 50, # hz
                logger = None,
                baudrate = 115200):

        self.robot_type = robot_type
        self.hand_type = hand_type

        self.control_types = {
            'position': 3,
            'velocity': 2,
            'torque': 1,
            # 'current': 0
        }

        self.control_type = self.control_types['position']

        # initialize to 1 in order to cycle through it
        default_firmware_slave_id = 1

        self._communication_handler = NewCommunication(communication_method=communication_method,
                                                    logger=logger, port=communication_channel_identifier,
                                                    baudrate=baudrate, slave_address=slave_ID_map.expected_slave_id(robot_type, hand_type))
        # self._communication_handler = NewCommunication(communication_method=communication_method,
        #                                             logger=logger, port=communication_channel_identifier,
        #                                             baudrate=baudrate, slave_address=default_firmware_slave_id)
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
        self.counter = 0

        # set up sigint handler
        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._sigint_handler)

        self.connect()

    def _sigint_handler(self, signum, frame):
        self.logger.info("Ctrl+C detected. Calling sleep and disconnecting.")
        self.sleep()
        self.disconnect()
        self.original_sigint_handler(signum, frame)

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

    def disconnect(self):
        self._communication_handler.close_connection()
        signal.signal(signal.SIGINT, self.original_sigint_handler)

    def wake_up(self,control_type:int=3):
        # """
        # Wake up the hand and set the control type
        #  3 for position control, 2 for velocity control, 1 for torque control -- maximum 3 bits
        # """
        # wake_command = self._command_handler.get_robot_start_command(control_type=control_type)

        # self.control_type = control_type
        # self.logger.info(f"Current configuration {self.robot_type} and {self.hand_type}, attemping wakeup")
        # self.counter = 0
        # while not self.awake and self.counter < len(slave_ID_map.SLAVE_ID_BY_ROBOT_HAND):
        #     self._communication_handler.send_data(wake_command)
        #     self.last_time = time.perf_counter()

        #     # wait for hand state ready
        #     ready_result = self._communication_handler.wait_for_ready(vis=False,timeout=30)

        #     # TODO try another slave ID if the hand times out 
        #     self.logger.info(f"Current configuration {self.robot_type} and {self.hand_type}, attemping wakeup")
        #     if not ready_result:
        #         # self.iterate_slave_id()
        #         self.logger.error("Hand timed out waiting for ready")
        #     elif ready_result == ActuatorState.ACTUATOR_SLEEP.value:
        #         # try to wake hand again
        #         self.wake_up()
        #     else:
        #         self.logger.info("Hand ready")
        #         self.state = ActuatorState.ACTUATOR_IDLE
        #         self.awake = True
        """
        Wake up the hand by scanning all known slave addresses using raw
        serial I/O (bypasses minimalmodbus address validation).
        Once a hand responds, reads slave_id_reg to auto-detect robot type,
        then reconfigures for normal minimalmodbus operation.
        """
        self.control_type = control_type
        self.awake = False

        start_cmd = self._command_handler.commands['start_command']
        value = (control_type << 8) | start_cmd

        # Build scan order: configured address first, then all others
        configured_addr = slave_ID_map.expected_slave_id(self.robot_type, self.hand_type)
        all_ids = list(slave_ID_map.SLAVE_ID_TO_ROBOT_HAND.keys())
        scan_order = [configured_addr] + [sid for sid in all_ids if sid != configured_addr]

        # find which address the hand listens on
        responding_addr = None
        for addr in scan_order:
            rtype, htype = slave_ID_map.robot_hand_from_slave_id(addr)
            self.logger.info(f"Probing slave_id={addr} ({rtype}, {htype})...")

            resp_slave = self._communication_handler.raw_write_register(
                register=0, value=value, slave_override=addr
            )
            if resp_slave is not None:
                self.logger.info(
                    f"Hand responded on addr={addr} (response byte={resp_slave})"
                )
                responding_addr = addr
                break
            # Small delay before trying next address
            time.sleep(0.1)

        if responding_addr is None:
            self.logger.error("No hand responded on any known slave address")
            return

        # poll feedback register (raw) until ready 
        feedback_reg = ModbusMap().modbus_reg_map['feedback_register']
        acceptable = {
            ActuatorState.ACTUATOR_IDLE.value,
            ActuatorState.ACTUATOR_READY.value,
            ActuatorState.ACTUATOR_ACTIVE.value,
            ActuatorState.ACTUATOR_ERROR.value,
        }
        timeout = 30
        start_time = time.perf_counter()
        ready = False

        while time.perf_counter() - start_time < timeout:
            _, vals = self._communication_handler.raw_read_registers(
                start_register=feedback_reg, count=1,
                slave_override=responding_addr
            )
            if vals is not None:
                state = vals[0] & 0x0F
                self.logger.info(f"Robot state: {ActuatorState(state).name}")
                if state in acceptable:
                    ready = True
                    break
                elif state == ActuatorState.ACTUATOR_SLEEP.value:
                    self.logger.info("Hand sleeping, resending wake command")
                    self._communication_handler.raw_write_register(
                        register=0, value=value, slave_override=responding_addr
                    )
            time.sleep(0.3)

        if not ready:
            self.logger.error("Hand timed out waiting for ready")
            return

        # identify robot type 
        # First try slave_id_reg
        self.logger.info("Hand awake. Reading slave_id_reg...")
        slave_id_reg = ModbusMap().modbus_reg_map['slave_id_reg']
        _, id_vals = self._communication_handler.raw_read_registers(
            start_register=slave_id_reg, count=1,
            slave_override=responding_addr
        )

        detected_id = None
        if id_vals is not None:
            detected_id = id_vals[0] & 0xFF
            result = slave_ID_map.robot_hand_from_slave_id(detected_id)
            if result is not None:
                robot_type, hand_type = result
                self.logger.info(f"Identified via slave_id_reg={detected_id} -> {robot_type}, {hand_type}")
                self._reconfigure(robot_type, hand_type, detected_id)
                self.state = ActuatorState.ACTUATOR_IDLE
                self.awake = True
                self.logger.info(f"Hand ready — {self.robot_type} ({self.hand_type})")
                return

        # Fallback: the hand only responds on its correct slave address,
        # so responding_addr IS the slave_id
        self.logger.info(
            f"slave_id_reg returned {detected_id}, falling back to scan address {responding_addr}"
        )
        result = slave_ID_map.robot_hand_from_slave_id(responding_addr)
        if result is not None:
            robot_type, hand_type = result
            self.logger.info(f"Identified via scan address={responding_addr} -> {robot_type}, {hand_type}")
            self._reconfigure(robot_type, hand_type, responding_addr)
        else:
            self.logger.warning(f"Address {responding_addr} not in SlaveIDMap, keeping current config")
            self._reconfigure_addr_only(responding_addr)

        self.state = ActuatorState.ACTUATOR_IDLE
        self.awake = True
        self.logger.info(f"Hand ready — {self.robot_type} ({self.hand_type})")

    def _read_and_identify_robot(self):
        """
        Read the slave_id_reg from the (already awake) hand and resolve it
        to a (robot_type, hand_type, slave_id) tuple.
        
        Returns (robot_type, hand_type, slave_id) on success, or
        (self.robot_type, self.hand_type, None) on failure.
        """
        try:
            slave_id_reg = ModbusMap().modbus_reg_map['slave_id_reg']
            raw = self._communication_handler.receive_data(amount_dat=1, start=slave_id_reg)
            if raw is None:
                self.logger.warning("No response when reading slave_id_reg")
                return (self.robot_type, self.hand_type, None)

            # decode slave_id_reg is uint8 in the low byte
            decoded = self._command_handler.get_decoded_feedback_data(raw, modbus_key='slave_id_reg')
            detected_id = decoded[0] if decoded else None

            if detected_id is None or detected_id == 0:
                self.logger.warning(f"slave_id_reg returned invalid value: {detected_id}")
                return (self.robot_type, self.hand_type, None)

            result = slave_ID_map.robot_hand_from_slave_id(detected_id)
            if result is None:
                self.logger.warning(f"slave_id={detected_id} not found in SlaveIDMap")
                return (self.robot_type, self.hand_type, None)

            robot_type, hand_type = result
            self.logger.info(f"Detected slave_id={detected_id} -> {robot_type}, {hand_type}")
            return (robot_type, hand_type, detected_id)

        except Exception as e:
            self.logger.error(f"Error reading slave_id_reg: {e}")
            return (self.robot_type, self.hand_type, None)

    def _reconfigure(self, robot_type: str, hand_type: str, slave_id: int):
        """
        Reconfigure the API to use the detected robot type / hand type.
        Updates the communication slave address, robot handler, and command handler.
        """
        self.robot_type = robot_type
        self.hand_type = hand_type

        # Update Modbus slave address all the way down to the instrument
        self._communication_handler.update_slave_address(slave_id)

        # Rebuild robot and command handlers for the new joint configuration
        self._robot_handler = Robot(
            robot_type=robot_type, hand_type=hand_type, logger=self.logger
        )
        self._command_handler = NewCommands(
            num_joints=len(self._robot_handler.robot.hand_joints),
            logger=self.logger,
        )
        self.logger.info(
            f"Reconfigured to {robot_type} ({hand_type}), slave_id={slave_id}")
        
    def _reconfigure_addr_only(self, slave_addr: int):
        """Fallback: set the communication address without changing robot/command handlers."""
        self._communication_handler.update_slave_address(slave_addr)
        self.logger.info(f"Set communication address to {slave_addr} (robot type unchanged)")

    def sleep(self):
        sleep_command = self._command_handler.get_sleep_command()
        self._communication_handler.send_data(sleep_command)
        self.last_time = time.perf_counter()
    
    def get_robot_status(self):
        try:
            robot_state = self._communication_handler._check_robot_state()
            
            actuator_state = ActuatorState((robot_state & 0b00001111)).name
            trajectory_return = TrajectoryReturn((robot_state & 0b11110000) >> 4).name
            self.logger.info(f"Actuator state: {actuator_state}, Trajectory return: {trajectory_return}")
            return actuator_state, trajectory_return
        except ValueError:
            self.logger.error(f"Invalid actuator state: {robot_state}")
            return None

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
        if not self._communication_handler.wait_for_ready(vis=True,timeout=10,acceptable_state=ActuatorState.ACTUATOR_READY.value):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")
            self.state = ActuatorState.ACTUATOR_IDLE

    def set_joint_angles_by_list(self, joint_angles:list, control_type:int=3):
        """
        sends joint commands to the hand - set_joint_angles for consistency with v1 api
        :param joint_angles: list of joint angles to set - MUST ALL BE OF SAME TYPE based on injected_control_type
        :param injected_control_type: control type to use for the joint angles - 3 for position control, 2 for velocity control, 1 for torque control
        JOINT LIST MUST BE IN ORDER OF JOINT INDEX
        :return: True if the command was sent successfully, False otherwise
        """
        if not self._check_awake():
            return

        # create dict of joint angles
        joint_angles_dict = {f'{i}':{'target_angle':joint_angles[i]} for i in range(len(joint_angles))}
        return self.set_joint_angles(joint_angles_dict, injected_control_type=control_type)

    def set_joint_angles(self, joint_angles:dict, injected_control_type:int=None):
        """
        sends joint commands to the hand - set_joint_angles for consistency with v1 api
        :param joint_angles: dictionary of joint angles to set - can havInvalie any combination of target_angle, target_velocity, or target_force - will be converted to the correct command based on the control type
        :return: True if the command was sent successfully, False otherwise
        """
        if not self._check_awake():
            return

        available_control = self._robot_handler.set_joint_angles(joint_angles,name=True)
        self.logger.info(f"Available control: {available_control}")

        if available_control == 0:
            self.logger.warning("No valid data in joint dictionary to send")
            return False

        if injected_control_type is not None:
            available_control = (1 << injected_control_type)

        if (available_control & 0b100) != 0 and self.control_type == self.control_types['position']:
            set_joint_angles_cmd = self._command_handler.get_target_position_command(self._robot_handler.robot.hand_joints)
            self.wait_for_com_freq()
            self._communication_handler.send_data(set_joint_angles_cmd,CommandType.TARGET_COMMAND.value)
            self.last_time = time.perf_counter()
        if (available_control & 0b10) != 0 and self.control_type >= self.control_types['velocity']:
            set_joint_angles_cmd = self._command_handler.get_target_velocity_command(self._robot_handler.robot.hand_joints)
            self.wait_for_com_freq()
            self._communication_handler.send_data(set_joint_angles_cmd,CommandType.TARGET_COMMAND.value)
            self.last_time = time.perf_counter()
        if (available_control & 0b1) != 0 and self.control_type >= self.control_types['torque']:
            set_joint_angles_cmd = self._command_handler.get_target_force_command(self._robot_handler.robot.hand_joints)
            self.wait_for_com_freq()
            self._communication_handler.send_data(set_joint_angles_cmd,CommandType.TARGET_COMMAND.value)
            self.last_time = time.perf_counter()
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

    def get_voltage(self):
        """
        get voltage feedback from the hand
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_voltage_start_reg']
        start_reg_key = 'feedback_voltage_start_reg'

        amount_data = 2 # 1 float 

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        self.logger.info(f"Voltage: {decoded_feedback_data[0]}")
        return decoded_feedback_data[0]
    
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
        for key,value in ModbusMap().modbus_reg_map.items():
            if value == start_reg:
                start_reg_confirmed = key
                break

        if start_reg_confirmed is not None:
            amount_data = math.ceil(ModbusMap().data_type_multiplier_map[start_reg_confirmed] * self._robot_handler.robot.number_of_joints)
            if start_reg_confirmed == 'feedback_voltage_start_reg':
                amount_data = 2 # 1 float for voltage
            elif start_reg_confirmed == 'slave_id_reg':
                amount_data = 1
            elif start_reg_confirmed == 'feedback_force_sensor_start_reg':
                amount_data = 5 * 3 * 2 # 5 fingers, 3 axes per finger, 2 registers per float
        else:
            raise ValueError('Start Register is not recognized -- see ModbusMap.pdf in robot/$robot$/data')

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_confirmed)

        if start_reg_confirmed == 'slave_id_reg':
            self.logger.info('slave_id_reg: %s', decoded_feedback_data[0])
            return decoded_feedback_data[0]

        # populate hand joint dict based on robot
        self.logger.info(f'{start_reg_confirmed}:{self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_confirmed)}')
        if start_reg_confirmed == 'feedback_voltage_start_reg':
            return decoded_feedback_data[0]
        return self.helper_fill_dict_from_feedback_data(decoded_feedback_data)

    def helper_fill_dict_from_feedback_data(self,feedback_data:list):
        """
        Helper function to fill a dictionary from feedback data for getters

        Parameters:
        :feedback_data: list of feedback data

        Returns:
        :feedback_data_dict: dictionary of feedback data
        """
        # return decoded feedback data in a dict
        feedback_data_dict = {}
        for index, value in enumerate(self._robot_handler.robot.joint_names):
            feedback_data_dict[value] = feedback_data[index]
        return feedback_data_dict

    def helper_fill_dict_from_fingertip_forces(self, feedback_data: list) -> dict:
        """
        Map decoded fingertip feedback (5 fingers × 3 axes = 15 floats) to finger names.
        Order matches Modbus / firmware and ``robot.force_sensors`` iteration order.
        """
        fs = self._robot_handler.robot.force_sensors
        if not fs:
            return {}
        out = {}
        i = 0
        for finger in fs:
            if i + 2 < len(feedback_data):
                out[finger] = {
                    'x': feedback_data[i],
                    'y': feedback_data[i + 1],
                    'z': feedback_data[i + 2],
                }
            i += 3
        return out

    def get_joint_forces(self):
        """
        Get the joint torques from the hand
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_force_start_reg']
        start_reg_key = 'feedback_force_start_reg'

        amount_data = math.ceil(ModbusMap().data_type_multiplier_map[start_reg_key] * self._robot_handler.robot.number_of_joints)

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        # populate hand joint dict based on robot
        self.logger.info(self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_key))
        return self.helper_fill_dict_from_feedback_data(decoded_feedback_data)

    def get_fingertip_forces(self):
        """
        Get the fingertip forces from the hand.

        Returns a dict keyed by finger name (e.g. thumb, index, …), each value is
        ``{'x': float, 'y': float, 'z': float}``. This matches the 15 decoded samples
        from the bus; ``robot.force_sensors`` is updated in parallel for object access.
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_force_sensor_start_reg']
        start_reg_key = 'feedback_force_sensor_start_reg'

        amount_data = math.ceil(ModbusMap().data_type_multiplier_map[start_reg_key] * len(self._robot_handler.robot.force_sensors) * 3) # 5 fingers, 3 axes per finger

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        self.logger.info(self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_key))
        return self.helper_fill_dict_from_fingertip_forces(decoded_feedback_data)
    
    def get_joint_speeds(self):
        """
        Get the joint speeds from the hand
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_velocity_start_reg']
        start_reg_key = 'feedback_velocity_start_reg'

        amount_data = math.ceil(ModbusMap().data_type_multiplier_map[start_reg_key] * self._robot_handler.robot.number_of_joints)

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        # populate hand joint dict based on robot
        self.logger.info(self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_key))
        return self.helper_fill_dict_from_feedback_data(decoded_feedback_data)

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

        amount_data = math.ceil(ModbusMap().data_type_multiplier_map[start_reg_key] * self._robot_handler.robot.number_of_joints) 

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        # populate hand joint dict based on robot
        self.logger.info(self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_key))
        return self.helper_fill_dict_from_feedback_data(decoded_feedback_data)

    def get_avg_temperature(self):
        """
        Get the average temperature of the hand
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_avg_temperature_start_reg']
        start_reg_key = 'feedback_avg_temperature_start_reg'

        amount_data = 1 # only 1 value

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        self.logger.info(f"Average temperature: {decoded_feedback_data[0]}")

        return decoded_feedback_data[0]
        
    def get_hand_feedback_data(self) -> bool:
        """
        Get all feedback data from the hand that is available
        """
        if not self._check_awake():
            return

        for feedback_type in self._robot_handler.robot.available_feedback_types:
            if feedback_type == 'feedback_force_sensor_start_reg':
                self.get_fingertip_forces()
            else:
                self.get_joint_angles(start_reg=ModbusMap().modbus_reg_map[feedback_type])
        return True

    def get_error_report(self):
        """
        Get the error report from the hand
        """
        if not self._check_awake():
            return

        start_reg = ModbusMap().modbus_reg_map['feedback_actuator_error_reg']
        start_reg_key = 'feedback_actuator_error_reg'

        amount_data = math.ceil(ModbusMap().data_type_multiplier_map[start_reg_key] * self._robot_handler.robot.number_of_joints)

        feedback_data = self._communication_handler.receive_data(amount_dat=amount_data,start=start_reg)
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(feedback_data,modbus_key=start_reg_key)

        # populate hand joint dict based on robot
        self.logger.info(self._robot_handler.get_joint_angles(decoded_feedback_data,feedback_type=start_reg_key))
        return self.helper_fill_dict_from_feedback_data(decoded_feedback_data)
        

    # for compatibility
    def get_streamed_joint_angles(self,dat_type=0):
        self.logger.error(f"get_streamed_joint_angles is not implemented in ArtusAPIv2")
        return None

    def reset(self,joints=None):
        if joints is None:
            joints = int(input(f"Enter number of joints to reset (0-{self._robot_handler.robot.number_of_joints}): "))
        reset_command = self._command_handler.get_reset_command(joints)
        self.wait_for_com_freq()
        self._communication_handler.send_data(reset_command)
        self.last_time = time.perf_counter()
        
        # wait for hand state ready
        if not self._communication_handler.wait_for_ready(vis=False):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")
    
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
        # self._firmware_updater.update_firmware_piecewise(fw_size)

        time.sleep(0.5)

        # send firmware data 
        self._firmware_updater.update_firmware(fw_size)

        # wait for hand state ready
        while self.get_robot_status()[0] == ActuatorState.ACTUATOR_FLASHING.name:
            self.logger.info(f"Waiting for firmware update to complete")
            time.sleep(2)