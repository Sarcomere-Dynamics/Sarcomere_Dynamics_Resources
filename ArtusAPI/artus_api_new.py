"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Top-level user-facing API for controlling ARTUS family robotic hands over Modbus."""

import time
import logging
import signal
import math
from enum import Enum
from tracemalloc import start
from .common.ModbusMap import ModbusMap,TrajectoryReturn
from .common.SlaveIDMap import expected_slave_id
from .commands import NewCommands
from .communication.new_communication import NewCommunication,ActuatorState,CommandType
from .robot import Robot
from .firmware_update import FirmwareUpdaterNew

class ArtusAPI_V2:
    """Newer, single user-facing entry point for controlling an ARTUS hand.

    Redesigned to accommodate a more robust communication process as well as
    the newer series of hands, whereas the legacy ArtusAPI is mainly for the
    ARTUS Lite. Composes a robot handler (joint model/limits), a command
    handler (Modbus register serialization), and a communication handler
    (physical bus I/O).
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
                baudrate = 115200): #115200 for RS485, 250000 for UART
        """Initializes the robot, command, and communication handlers and connects.

        Args:
            communication_method: Transport to use, e.g. 'RS485_RTU' or 'Modbus_TCP'.
            communication_channel_identifier: Serial port (e.g. 'COM9') or other
                channel identifier for the chosen communication method.
            robot_type: Robot variant, e.g. 'artus_talos', 'artus_lite',
                'artus_lite_plus', 'artus_scorpion', 'artus_dex'.
            hand_type: Hand side, e.g. 'left' or 'right'.
            communication_frequency: Maximum command send frequency in Hz.
            logger: Optional logger instance shared across handlers; a module
                logger is created if not provided.
            baudrate: Serial baudrate (115200 for RS485, 250000 for UART).
        """

        self.robot_type = robot_type
        self.hand_type = hand_type

        self.control_types = {
            'position': 3,
            'velocity': 2,
            'torque': 1,
            # 'current': 0
        }

        self.control_type = self.control_types['position']

        self._communication_handler = NewCommunication(communication_method=communication_method,
                                                    logger=logger, port=communication_channel_identifier,
                                                    baudrate=baudrate, slave_address=expected_slave_id(robot_type, hand_type))
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

        # set up sigint handler
        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._sigint_handler)

        self.connect()

    def _sigint_handler(self, signum, frame):
        """Handles SIGINT by putting the hand to sleep before disconnecting.

        Args:
            signum: Signal number delivered by the OS.
            frame: Current stack frame at the time the signal was received.
        """
        self.logger.info("Ctrl+C detected. Calling sleep and disconnecting.")
        self.sleep()
        self.disconnect()
        self.original_sigint_handler(signum, frame)

    def set_control_type(self,control_type:int):
        """Sets the active control type of the hand.

        Args:
            control_type: Control type value from ``self.control_types``
                (1 for torque control, 2 for velocity control, 3 for position
                control).

        Returns:
            True if the control type was valid and set, False otherwise.
        """
        if control_type not in self.control_types.values():
            self.logger.error(f"Control type {control_type} is not valid")
            return False
        self.control_type = control_type
        return True

    def _check_awake(self):
        """Checks whether the hand is awake and ready to accept commands.

        Returns:
            True (currently a stub check; the underlying awake gating is
            commented out).
        """
        # if not self.awake:
        #     self.logger.warning(f'Hand not ready, send `wake_up` command')
        #     return False
        return True

    def connect(self):
        """Opens the underlying communication channel to the hand."""
        self._communication_handler.open_connection()
        time.sleep(1)
        # self.wake_up()

    def disconnect(self):
        """Closes the communication channel and restores the original SIGINT handler."""
        self._communication_handler.close_connection()
        signal.signal(signal.SIGINT, self.original_sigint_handler)

    def wake_up(self,control_type:int=3):
        """Wakes up the hand and sets its control type.

        Sends the start command, waits for the hand to report a ready state,
        and retries once if the hand reports it is asleep.

        Args:
            control_type: Control type to wake up with -- 3 for position
                control, 2 for velocity control, 1 for torque control
                (maximum 3 bits).
        """
        wake_command = self._command_handler.get_robot_start_command(control_type=control_type)

        self.control_type = control_type
        self._communication_handler.send_data(wake_command)
        self.last_time = time.perf_counter()

        # wait for hand state ready
        ready_result = self._communication_handler.wait_for_ready(vis=False,timeout=30)
        if not ready_result:
            self.logger.error("Hand timed out waiting for ready")
        elif ready_result == ActuatorState.ACTUATOR_SLEEP.value:
            # try to wake hand again
            self.wake_up()
        else:
            self.logger.info("Hand ready")
            self.state = ActuatorState.ACTUATOR_IDLE
            self.awake = True

    def sleep(self):
        """Sends the sleep command, putting the hand into a low-power/idle state."""
        sleep_command = self._command_handler.get_sleep_command()
        self._communication_handler.send_data(sleep_command)
        self.last_time = time.perf_counter()

    def clear_errors(self):
        """Explicitly clear latched actuator errors.

        The firmware consumes this command only when the hand is in
        ACTUATOR_ERROR (primary recovery path) or ACTUATOR_IDLE (no-op
        refresh). It is silently ignored in every other state so mid-operation
        error bookkeeping is not wiped.

        There is no dedicated ack register - confirm the clear by polling
        ``get_error_report()`` and the robot status register (expect
        ``ACTUATOR_IDLE`` and all joint error_report values zeroed).
        """
        clear_errors_command = self._command_handler.get_clear_errors_command()
        self._communication_handler.send_data(clear_errors_command)
        self.last_time = time.perf_counter()

    def get_config(self, wifi_name:str, wifi_pass:str):
        """Writes new WiFi credentials to the hand and reads back its IP.

        Writes new WiFi credentials to the hand's onboard config over Modbus and
        reads back the IP address it was assigned. Applicable to hands with a
        WiFi-capable communication module; on wired transports (RS485_RTU,
        Modbus_TCP) this still exercises the onboard config write/ack flow but
        the reported IP reflects the WiFi radio regardless of the transport
        used to send this command.

        Sequence per parameter (SSID, then password):
          1. send update_config_command -> hand enters ACTUATOR_CONFIG
          2. send the length-prefixed register payload for the value
          3. wait for ACTUATOR_CONFIG_FINISH ack
        Then read the assigned IP from the feedback position registers.

        Args:
            wifi_name: WiFi SSID to write to the hand.
            wifi_pass: WiFi password to write to the hand.
        """
        ssid_regs = self.string_to_registers(wifi_name)
        pass_regs = self.string_to_registers(wifi_pass)

        config_types = [1, 2] # 1 -> wifi name, 2 -> wifi pass
        labels = {1: "wifi name", 2: "wifi pass"}
        regs = {1: ssid_regs, 2: pass_regs}
        values = {1: wifi_name, 2: wifi_pass}

        for config_type in config_types:
            config_command = self._command_handler.update_config_command(config_type)
            self._communication_handler.send_data(config_command)

            ready_result = self._communication_handler.wait_for_ready(vis=False,acceptable_state=ActuatorState.ACTUATOR_CONFIG.value,timeout=30)
            if not ready_result:
                self.logger.error("Hand timed out waiting for ready")
                continue

            length_command = self._command_handler.update_config_len_command(regs[config_type],values[config_type])
            self._communication_handler.send_data(length_command, CommandType.CONFIG_COMMAND.value)

            ready_result = self._communication_handler.wait_for_ready(vis=False,acceptable_state=ActuatorState.ACTUATOR_CONFIG_FINISH.value,timeout=10)
            if not ready_result:
                self.logger.error("Hand timed out waiting for ready")
            else:
                self.logger.info(f"Finished writing {labels[config_type]}")
            time.sleep(0.2)

        feedback_data = self._communication_handler.receive_data(amount_dat=4,start=ModbusMap().modbus_reg_map['feedback_position_start_reg'])

        bytes_out = []
        for reg in feedback_data[:2]: # only first 2 registers contain the IP
            bytes_out.append((reg >> 8) & 0xFF)
            bytes_out.append(reg & 0xFF)

        ip_address = ".".join(str(b) for b in bytes_out)

        if ip_address == '0.0.0.0':
            self.logger.info("WiFi failed to connect. Please retry.")
        else:
            self.logger.info(f"WiFi parameters set as:\nWiFi name: {wifi_name}\nWiFi pass: {wifi_pass}\nIP address: {ip_address}\nRestart the API with the corresponding IP address.")

    @staticmethod
    def string_to_registers(s:str) -> list:
        """Converts a string into a list of 16-bit Modbus register values.

        Each register holds two ASCII bytes; the byte string is null-padded
        to an even length before packing.

        Args:
            s: String to convert (encoded as UTF-8).

        Returns:
            List of 16-bit integers, each packing two bytes of the string.
        """
        data = s.encode("utf-8")

        # pad to even length
        if len(data) % 2 != 0:
            data += b"\x00"

        registers = []
        for i in range(0, len(data), 2):
            reg = (data[i] << 8) | data[i + 1]
            registers.append(reg)

        return registers

    def get_robot_status(self):
        """Reads and decodes the hand's current actuator and trajectory state.

        Returns:
            Tuple of (actuator_state_name, trajectory_return_name) as
            strings, or None if the raw status value could not be decoded.
        """
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
        """Runs the calibration routine on the hand.

        Sends the calibration command, optionally scoped to a single joint,
        and blocks until the hand reports it is ready again.

        Args:
            joint: Joint index to calibrate. If 0 (default), calibrates all
                joints/strokes.
        """
        if not self._check_awake():
            return
        calibrate_cmd = self._command_handler.get_calibration_command()
        if joint > 0:
            self.logger.info(f"Calibrating joint {joint}")
            calibrate_cmd.append(joint)
        
        self._communication_handler.send_data(calibrate_cmd)
        time.sleep(3)
        self.last_time = time.perf_counter()
        self.state = ActuatorState.ACTUATOR_CALIBRATING_STROKE.value

        # wait for hand state ready
        if not self._communication_handler.wait_for_ready(vis=True,timeout=10):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")
            self.state = ActuatorState.ACTUATOR_IDLE.value

    def set_joint_angles_by_list(self, joint_angles:list, control_type:int=3):
        """Sends joint commands to the hand from an ordered list of angles.

        Named ``set_joint_angles_by_list`` for consistency with the v1 API.
        Internally converts the list into the indexed dict form expected by
        ``set_joint_angles``.

        Args:
            joint_angles: List of joint angles to set. Values must all be of
                the same type based on ``control_type``, and the list must be
                in order of joint index.
            control_type: Control type to use for the joint angles -- 3 for
                position control, 2 for velocity control, 1 for torque
                control.

        Returns:
            True if the command was sent successfully, False otherwise. None
            if the hand is not awake.
        """
        if not self._check_awake():
            return

        # create dict of joint angles
        joint_angles_dict = {f'{i}':{'target_angle':joint_angles[i]} for i in range(len(joint_angles))}
        return self.set_joint_angles(joint_angles_dict, injected_control_type=control_type)

    def set_joint_angles(self, joint_angles:dict, injected_control_type:int=None):
        """Sends joint commands to the hand.

        Named ``set_joint_angles`` for consistency with the v1 API.

        Args:
            joint_angles: Dictionary of joint angles to set. Can have any
                combination of target_angle, target_velocity, or
                target_force -- converted to the correct command based on the
                control type.
            injected_control_type: If provided, overrides the derived
                available-control bitmask with this control type instead of
                using what ``joint_angles`` implies.

        Returns:
            True if the command was sent successfully, False if the joint
            dictionary contained no valid data. None if the hand is not
            awake.
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
        """Checks whether enough time has passed since the last command.

        Necessary so that the messages stay in sync with the configured
        communication frequency.

        Args:
            last_time: Timestamp (from ``time.perf_counter()``) of the last
                command sent.

        Returns:
            True if the time since ``last_time`` is greater than or equal to
            the communication period, False if a command was sent too
            recently.
        """
        current_time = time.perf_counter()
        if current_time - self.last_time < self._communication_period:
            self.logger.debug("Command not sent. Communication frequency is too high.")
            return False
        return True

    def wait_for_com_freq(self):
        """Blocks until the communication period has elapsed since the last command.

        Returns:
            True once it is safe to send the next command.
        """
        while not self._check_communication_frequency(self.last_time):
            time.sleep(0.001)
        return True

    def set_home_position(self):
        """Moves the hand to its home position at the default velocity."""
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
        """Reads the hand's supply voltage feedback.

        Returns:
            Decoded voltage as a float, or None if the hand is not awake.
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
        """Reads feedback data for a given feedback register range.

        Named ``get_joint_angles`` for consistency with the v1 API; actually
        should be ``get_feedback``. Covers all feedback types -- position,
        torque, velocity, temperature -- based on the ``start_reg``
        parameter.

        Args:
            start_reg: Starting Modbus register address, as defined in
                ``ModbusMap().modbus_reg_map``.

        Returns:
            For ``slave_id_reg`` or ``feedback_voltage_start_reg``, the
            single decoded value. Otherwise, a dict mapping joint name to its
            decoded feedback value. None if the hand is not awake.

        Raises:
            ValueError: If ``start_reg`` does not match a known key in
                ``ModbusMap().modbus_reg_map``.
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
        """Maps a decoded feedback list to a dict keyed by joint name.

        Helper function to fill a dictionary from feedback data for getters.

        Args:
            feedback_data: List of decoded feedback data, indexed in the
                same order as ``self._robot_handler.robot.joint_names``.

        Returns:
            Dictionary mapping joint name to its feedback value.
        """
        # return decoded feedback data in a dict
        feedback_data_dict = {}
        for index, value in enumerate(self._robot_handler.robot.joint_names):
            feedback_data_dict[value] = feedback_data[index]
        return feedback_data_dict

    def helper_fill_dict_from_fingertip_forces(self, feedback_data: list) -> dict:
        """Maps decoded fingertip feedback to a dict keyed by finger name.

        Fingertip feedback is 5 fingers x 3 axes = 15 floats. Order matches
        Modbus/firmware and ``robot.force_sensors`` iteration order.

        Args:
            feedback_data: Flat list of 15 decoded force values (x, y, z per
                finger, in finger order).

        Returns:
            Dict mapping finger name to ``{'x': float, 'y': float, 'z':
            float}``, or an empty dict if the robot has no force sensors.
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
        """Reads joint torque/force feedback from the hand.

        Returns:
            Dict mapping joint name to feedback force value, or None if the
            hand is not awake.
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
        """Reads the fingertip forces from the hand.

        This matches the 15 decoded samples from the bus;
        ``robot.force_sensors`` is updated in parallel for object access.

        Returns:
            Dict keyed by finger name (e.g. thumb, index, ...), each value is
            ``{'x': float, 'y': float, 'z': float}``. None if the hand is not
            awake.
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
        """Reads joint velocity feedback from the hand.

        Returns:
            Dict mapping joint name to feedback velocity value, or None if
            the hand is not awake.
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
        """Reads per-joint temperature feedback from the hand.

        Returns:
            Dict mapping joint name to feedback temperature value, or None
            if the hand is not awake.
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
        """Reads the hand's average temperature feedback.

        Returns:
            Decoded average temperature as a float, or None if the hand is
            not awake.
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
        """Reads all feedback types supported by the connected robot.

        Iterates ``self._robot_handler.robot.available_feedback_types`` and
        fetches each one, routing fingertip force sensor data through
        ``get_fingertip_forces``.

        Returns:
            True once all available feedback types have been read, or None
            if the hand is not awake.
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
        """Reads the per-joint actuator error bitfield report from the hand.

        Returns:
            Dict mapping joint name to its decoded error report value, or
            None if the hand is not awake.
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
        """Stub retained for v1 API compatibility.

        Args:
            dat_type: Unused; kept for signature compatibility with v1.

        Returns:
            None. Always logs an error since this is not implemented in
            ArtusAPI_V2.
        """
        self.logger.error(f"get_streamed_joint_angles is not implemented in ArtusAPIv2")
        return None

    def reset(self,joints=None):
        """Sends a reset command for the given number of joints.

        Args:
            joints: Number of joints to reset. If None, prompts on stdin for
                a value between 0 and the robot's total joint count.
        """
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
        """Flashes new firmware to one or all actuator drivers on the hand.

        Prompts on stdin for any missing arguments (binary file path and/or
        which drivers to flash), sends the firmware command, then streams the
        firmware file to the hand and polls status until flashing completes.

        Args:
            file_location: Absolute path to the ``.bin`` firmware file. If
                None or not ending in ``.bin``, prompted for on stdin.
            drivers_to_flash: Which driver(s) to flash -- 0-5 for a specific
                actuator mapped to a joint number, or 6 for all actuators. If
                None, prompted for on stdin.
        """

        if file_location is None or (isinstance(file_location, str) and not file_location.endswith('.bin')):
            file_location = input('Please enter absolute filepath of binary file: ')

        self._firmware_updater = FirmwareUpdaterNew(communication_handler=self._communication_handler,
                                                    command_handler=self._command_handler,
                                                    file_location=file_location,
                                                    logger=self.logger)
        
        fw_size = self._firmware_updater.get_bin_file_info()

        # get driver to flash
        if drivers_to_flash == None:
            while drivers_to_flash is None or drivers_to_flash not in range(0, self._robot_handler.robot.number_of_controllers + 1):
                drivers_to_flash = int(input(
                    f'''
                    Please Enter Drivers to Flash:
                    0-n: Specific Actuator mapped to joint number
                    n+1: All Actuators
                    '''
                    ))
        
        # send commmand
        firmware_cmd = self._command_handler.get_firmware_command(drivers_to_flash)
        self._communication_handler.send_data(firmware_cmd) # sent firmware upload command to command register
        self.last_time = time.perf_counter()

        # send firmware data
        # self._firmware_updater.update_firmware_piecewise(fw_size)

        time.sleep(0.5)

        self.logger.info(f"next line is sending the firmware data")
        # send firmware data 
        self._firmware_updater.update_firmware(fw_size)

        # wait for hand state ready
        while self.get_robot_status()[0] == ActuatorState.ACTUATOR_FLASHING.name:
            self.logger.info(f"Waiting for firmware update to complete")
            time.sleep(2)