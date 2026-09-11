"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Top-level user-facing API for controlling ARTUS family robotic hands over Modbus."""

import signal
import time

from .commands import NewCommands
from .common.ModbusMap import ModbusMap, TrajectoryReturn
from .common.SlaveIDMap import expected_slave_id
from .communication.new_communication import (
    ActuatorState,
    CommandType,
    NewCommunication,
)
from .firmware_update import FirmwareUpdaterNew
from .robot import Robot


class ArtusAPI:
    """Newer, single user-facing entry point for controlling an ARTUS hand.

    Redesigned to accommodate a more robust communication process as well as
    the newer series of hands, whereas the legacy ArtusAPI is mainly for the
    ARTUS Lite. Composes a robot handler (joint model/limits), a command
    handler (Modbus register serialization), and a communication handler
    (physical bus I/O).
    """

    def __init__(
        self,
        config_file=None,
        config=None,
        logger=None,
        # optional overrides of the loaded configuration
        communication_method=None,
        communication_channel_identifier=None,
        robot_type=None,
        hand_type=None,
        communication_frequency=None,
        baudrate=None,
    ):
        """Initializes from the robot configuration, then builds handlers and connects.

        The configuration file is loaded first (an explicit *config_file* or
        *config*, otherwise the packaged default). Robot-specific objects
        (``_robot_handler``, communication, commands) are built only after
        those settings are resolved. Keyword arguments override the file.

        Args:
            config_file: Path to the user's ``robot_config.yaml``. Ignored
                when *config* is given. When both are omitted, see
                :func:`ArtusAPI.configuration.resolve_config_file`.
            config: An already-loaded :class:`~ArtusAPI.configuration.ArtusConfig`.
            logger: Optional logger instance shared across handlers. When
                omitted, the logger created by the configuration is used.
            communication_method: Transport override, e.g. 'RS485_RTU' or
                'Modbus_TCP'. Passing this does not skip port discovery
                unless *communication_channel_identifier* is also set.
            communication_channel_identifier: Serial port override (e.g.
                'COM9'). When given, automatic port/robot discovery is
                skipped.
            robot_type: Robot variant override, e.g. 'artus_talos',
                'artus_lite', 'artus_lite_plus', 'artus_scorpion',
                'artus_dex'.
            hand_type: Hand side override, e.g. 'left' or 'right'.
            communication_frequency: Maximum command send frequency in Hz.
            baudrate: Serial baudrate override (115200 for RS485, 250000
                for UART).
        """
        from .configuration import ArtusConfig

        self.config = (
            config
            if config is not None
            else ArtusConfig(
                config_file=config_file,
                logger=logger,
            )
        )
        self.logger = logger or self.config.logger

        settings = self._resolve_settings(
            communication_method=communication_method,
            communication_channel_identifier=communication_channel_identifier,
            robot_type=robot_type,
            hand_type=hand_type,
            communication_frequency=communication_frequency,
            baudrate=baudrate,
        )

        self.robot_type = settings["robot_type"]
        self.hand_type = settings["hand_type"]

        self.control_types = {
            "position": 3,
            "velocity": 2,
            "torque": 1,
            # 'current': 0
        }

        self.control_type = self.control_types["position"]

        self._communication_handler = NewCommunication(
            communication_method=settings["communication_method"],
            logger=self.logger,
            port=settings["communication_channel_identifier"],
            baudrate=settings["baudrate"],
            slave_address=expected_slave_id(self.robot_type, self.hand_type),
        )
        self._robot_handler = Robot(
            robot_type=self.robot_type,
            hand_type=self.hand_type,
            logger=self.logger,
        )
        self._command_handler = NewCommands(
            num_joints=len(self._robot_handler.robot.hand_joints),
            logger=self.logger,
        )

        self.state = ActuatorState.ACTUATOR_INITIALIZING.value

        self._communication_period = 1 / settings["communication_frequency"]
        self.last_time = time.perf_counter()

        self.awake = False

        # one-shot so the deprecation notice does not spam a control loop
        self._warned_get_joint_angles = False

        # set up sigint handler
        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._sigint_handler)

        self.connect()

    def _resolve_settings(
        self,
        communication_method,
        communication_channel_identifier,
        robot_type,
        hand_type,
        communication_frequency,
        baudrate,
    ):
        """Resolves constructor overrides against the loaded configuration.

        Reads the connected-hand block from ``self.config`` first. When no
        explicit port is given, runs automatic port/robot discovery so
        ``robot_type`` / ``hand_type`` / the channel identifier are known
        before handlers are constructed.

        Args:
            communication_method: Optional transport override.
            communication_channel_identifier: Optional port override. When
                set, pre-flight discovery is skipped.
            robot_type: Optional robot variant override.
            hand_type: Optional hand-side override.
            communication_frequency: Optional send-frequency override.
            baudrate: Optional serial baudrate override.

        Returns:
            Dict of resolved ``robot_type``, ``hand_type``,
            ``communication_method``, ``communication_channel_identifier``,
            ``baudrate``, and ``communication_frequency``.

        Raises:
            ValueError: If no connected robot is in the config and
                ``robot_type`` / ``hand_type`` were not provided.
        """
        try:
            robot_cfg = self.config.get_connected_robot()
        except ValueError:
            robot_cfg = None

        skip_preflight = (
            communication_channel_identifier is not None
            or communication_method == "Modbus_TCP"
            or (
                robot_cfg is not None
                and getattr(robot_cfg, "communication_method", "RS485_RTU")
                == "Modbus_TCP"
            )
        )
        if robot_cfg is not None and not skip_preflight:
            robot_cfg = self.config._preflight(robot_cfg, self.logger)

        def pick(override, attr, default):
            if override is not None:
                return override
            if robot_cfg is not None and hasattr(robot_cfg, attr):
                return getattr(robot_cfg, attr)
            return default

        resolved_robot_type = pick(robot_type, "robot_type", None)
        resolved_hand_type = pick(hand_type, "hand_type", None)
        if resolved_robot_type is None or resolved_hand_type is None:
            raise ValueError(
                "No connected robot in the configuration file and "
                "robot_type/hand_type were not provided."
            )

        return {
            "robot_type": resolved_robot_type,
            "hand_type": resolved_hand_type,
            "communication_method": pick(
                communication_method, "communication_method", "RS485_RTU"
            ),
            "communication_channel_identifier": pick(
                communication_channel_identifier,
                "communication_channel_identifier",
                "COM9",
            ),
            "baudrate": pick(baudrate, "baudrate", 115200),
            "communication_frequency": (
                communication_frequency
                if communication_frequency is not None
                else getattr(robot_cfg, "streaming_frequency", 50)
                if robot_cfg is not None
                else 50
            ),
        }

    def get_robot_calibrate(self, hand_type: str = None) -> bool:
        """Reads the calibrate flag from the loaded configuration.

        Args:
            hand_type: ``'left'`` or ``'right'``. Defaults to this
                instance's ``hand_type``.

        Returns:
            True if the calibrate flag is set for that hand.
        """
        return self.config.get_robot_calibrate(hand_type or self.hand_type)

    def get_robot_wake_up(self, hand_type: str = None) -> bool:
        """Reads the start_robot (wake up) flag from the loaded configuration.

        Args:
            hand_type: ``'left'`` or ``'right'``. Defaults to this
                instance's ``hand_type``.

        Returns:
            True if the start_robot flag is set for that hand.

        Raises:
            ValueError: If hand_type is given but is not 'left' or 'right'.
        """
        return self.config.get_robot_wake_up(hand_type or self.hand_type)

    @staticmethod
    def copy_default_config(dest):
        """Writes the packaged robot_config.yaml template to *dest*.

        Args:
            dest: File path, or a directory (writes ``robot_config.yaml``
                inside it).

        Returns:
            The Path of the written file.
        """
        from .configuration import copy_default_config as _copy_default_config

        return _copy_default_config(dest)

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

    def set_control_type(self, control_type: int):
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

    def wake_up(self, control_type: int = 3):
        """Wakes up the hand and sets its control type.

        Sends the start command, waits for the hand to report a ready state,
        and retries once if the hand reports it is asleep.

        Args:
            control_type: Control type to wake up with -- 3 for position
                control, 2 for velocity control, 1 for torque control
                (maximum 3 bits).
        """
        wake_command = self._command_handler.get_robot_start_command(
            control_type=control_type
        )

        self.control_type = control_type
        self._communication_handler.send_data(wake_command)
        self.last_time = time.perf_counter()

        # wait for hand state ready
        ready_result = self._communication_handler.wait_for_ready(vis=False, timeout=30)
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

    def get_config(self, wifi_name: str, wifi_pass: str):
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

        config_types = [1, 2]  # 1 -> wifi name, 2 -> wifi pass
        labels = {1: "wifi name", 2: "wifi pass"}
        regs = {1: ssid_regs, 2: pass_regs}
        values = {1: wifi_name, 2: wifi_pass}

        for config_type in config_types:
            config_command = self._command_handler.update_config_command(config_type)
            self._communication_handler.send_data(config_command)

            ready_result = self._communication_handler.wait_for_ready(
                vis=False,
                acceptable_state=ActuatorState.ACTUATOR_CONFIG.value,
                timeout=30,
            )
            if not ready_result:
                self.logger.error("Hand timed out waiting for ready")
                continue

            length_command = self._command_handler.update_config_len_command(
                regs[config_type], values[config_type]
            )
            self._communication_handler.send_data(
                length_command, CommandType.CONFIG_COMMAND.value
            )

            ready_result = self._communication_handler.wait_for_ready(
                vis=False,
                acceptable_state=ActuatorState.ACTUATOR_CONFIG_FINISH.value,
                timeout=10,
            )
            if not ready_result:
                self.logger.error("Hand timed out waiting for ready")
            else:
                self.logger.info(f"Finished writing {labels[config_type]}")
            time.sleep(0.2)

        feedback_data = self._communication_handler.receive_data(
            amount_dat=4,
            start=ModbusMap().modbus_reg_map["feedback_position_start_reg"],
        )

        bytes_out = []
        for reg in feedback_data[:2]:  # only first 2 registers contain the IP
            bytes_out.append((reg >> 8) & 0xFF)
            bytes_out.append(reg & 0xFF)

        ip_address = ".".join(str(b) for b in bytes_out)

        if ip_address == "0.0.0.0":
            self.logger.info("WiFi failed to connect. Please retry.")
        else:
            self.logger.info(
                f"WiFi parameters set as:\nWiFi name: {wifi_name}\nWiFi pass: {wifi_pass}\nIP address: {ip_address}\nRestart the API with the corresponding IP address."
            )

    @staticmethod
    def string_to_registers(s: str) -> list:
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
            actuator_state = ActuatorState(robot_state & 0b00001111).name
            trajectory_return = TrajectoryReturn((robot_state & 0b11110000) >> 4).name
            self.logger.info(
                f"Actuator state: {actuator_state}, Trajectory return: {trajectory_return}"
            )
            return actuator_state, trajectory_return
        except ValueError:
            self.logger.error(f"Invalid actuator state: {robot_state}")
            return None

    def calibrate(self, joint=0):
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
        if not self._communication_handler.wait_for_ready(vis=True, timeout=10):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")
            self.state = ActuatorState.ACTUATOR_IDLE.value

    def set_joint_angles_by_list(self, joint_angles: list, control_type: int = 3):
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
        joint_angles_dict = {
            f"{i}": {"target_angle": joint_angles[i]} for i in range(len(joint_angles))
        }
        return self.set_joint_angles(
            joint_angles_dict, injected_control_type=control_type
        )

    def set_joint_angles(self, joint_angles: dict, injected_control_type: int = None):
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

        available_control = self._robot_handler.set_joint_angles(
            joint_angles, name=True
        )
        self.logger.info(f"Available control: {available_control}")

        if available_control == 0:
            self.logger.warning("No valid data in joint dictionary to send")
            return False

        if injected_control_type is not None:
            available_control = 1 << injected_control_type

        if (available_control & 0b100) != 0 and self.control_type == self.control_types[
            "position"
        ]:
            set_joint_angles_cmd = self._command_handler.get_target_position_command(
                self._robot_handler.robot.hand_joints
            )
            self.wait_for_com_freq()
            self._communication_handler.send_data(
                set_joint_angles_cmd, CommandType.TARGET_COMMAND.value
            )
            self.last_time = time.perf_counter()
        if (available_control & 0b10) != 0 and self.control_type >= self.control_types[
            "velocity"
        ]:
            set_joint_angles_cmd = self._command_handler.get_target_velocity_command(
                self._robot_handler.robot.hand_joints
            )
            self.wait_for_com_freq()
            self._communication_handler.send_data(
                set_joint_angles_cmd, CommandType.TARGET_COMMAND.value
            )
            self.last_time = time.perf_counter()
        if (available_control & 0b1) != 0 and self.control_type >= self.control_types[
            "torque"
        ]:
            set_joint_angles_cmd = self._command_handler.get_target_force_command(
                self._robot_handler.robot.hand_joints
            )
            self.wait_for_com_freq()
            self._communication_handler.send_data(
                set_joint_angles_cmd, CommandType.TARGET_COMMAND.value
            )
            self.last_time = time.perf_counter()
        return True

    def _feedback_register_count(self, feedback_reg_key: str) -> int:
        """Computes how many holding registers to read for a feedback field.

        Delegates layout (scalar vs per-joint vs fingertip) to
        ``ModbusMap.feedback_register_count``; this wrapper supplies the
        connected robot's joint and force-sensor counts.

        Args:
            feedback_reg_key: Key in ``ModbusMap.data_type_multiplier_map`` /
                ``modbus_reg_map`` (e.g. ``feedback_position_start_reg``).

        Returns:
            Number of consecutive 16-bit registers to request.
        """
        sensors = self._robot_handler.robot.force_sensors or {}
        return ModbusMap().feedback_register_count(
            feedback_reg_key,
            self._robot_handler.robot.number_of_joints,
            len(sensors),
        )

    def _resolve_feedback_key(self, start_reg) -> str:
        """Resolves a feedback field name or register address to a ModbusMap key.

        Args:
            start_reg: Either a ModbusMap key name (e.g.
                ``'feedback_force_start_reg'``) or its Modbus register address.

        Returns:
            The matching key in ``ModbusMap().modbus_reg_map``.

        Raises:
            ValueError: If the name or address is not in the register map.
        """
        reg_map = ModbusMap().modbus_reg_map
        if isinstance(start_reg, str):
            if start_reg in reg_map:
                return start_reg
        else:
            for key, value in reg_map.items():
                if value == start_reg:
                    return key
        raise ValueError(
            f"Start Register {start_reg} is not recognized -- see ModbusMap.pdf in robot/$robot$/data"
        )

    def _read_feedback(self, feedback_reg_key: str) -> list:
        """Reads and decodes one feedback field off the bus.

        Args:
            feedback_reg_key: ModbusMap key for the feedback start register.

        Returns:
            List of decoded values, in bus order.
        """
        feedback_data = self._communication_handler.receive_data(
            amount_dat=self._feedback_register_count(feedback_reg_key),
            start=ModbusMap().modbus_reg_map[feedback_reg_key],
        )
        decoded_feedback_data = self._command_handler.get_decoded_feedback_data(
            feedback_data, modbus_key=feedback_reg_key
        )
        self._record_feedback(feedback_reg_key, decoded_feedback_data)
        return decoded_feedback_data

    def _record_feedback(self, feedback_reg_key: str, decoded_feedback_data: list):
        """Stores decoded feedback on the robot model and logs it.

        Per-joint and fingertip fields go through the robot handler, which
        populates ``hand_joints``/``force_sensors`` for object-style access.
        Scalar fields are logged directly -- the robot handler indexes its
        argument per joint and cannot consume them.

        Args:
            feedback_reg_key: ModbusMap key for the feedback start register.
            decoded_feedback_data: Decoded values from ``_read_feedback``.
        """
        if feedback_reg_key in ModbusMap.SCALAR_FEEDBACK_KEYS:
            label = ModbusMap.SCALAR_FEEDBACK_KEYS[feedback_reg_key]
            self.logger.info(f"{label}: {decoded_feedback_data[0]}")
            return
        self.logger.info(
            f"{feedback_reg_key}:{self._robot_handler.get_feedback_data(decoded_feedback_data, feedback_type=feedback_reg_key)}"
        )

    def _shape_feedback(self, feedback_reg_key: str, decoded_feedback_data: list):
        """Shapes decoded feedback into the return type for its field.

        Args:
            feedback_reg_key: ModbusMap key for the feedback start register.
            decoded_feedback_data: Decoded values from ``_read_feedback``.

        Returns:
            The single value for scalar fields, a dict keyed by finger for
            fingertip forces, or a dict keyed by joint name otherwise.
        """
        if feedback_reg_key in ModbusMap.SCALAR_FEEDBACK_KEYS:
            return decoded_feedback_data[0]
        if feedback_reg_key == ModbusMap.FINGERTIP_FEEDBACK_KEY:
            return self.helper_fill_dict_from_fingertip_forces(decoded_feedback_data)
        return self.helper_fill_dict_from_feedback_data(decoded_feedback_data)

    def _set_get_joint_field(
        self, joint_angles: dict, target_packer, feedback_reg_key: str
    ):
        """Shared FC 0x17 path: write one target field and read matching feedback.

        Args:
            joint_angles: Joint dict consumed by ``Robot.set_joint_angles``.
            target_packer: ``NewCommands`` method that packs
                ``[start_reg, *values]`` for the target field.
            feedback_reg_key: ModbusMap key for the feedback start register.

        Returns:
            Dict mapping joint name to decoded feedback, False if no valid
            joint data, or None if the hand is not awake.
        """
        if not self._check_awake():
            return

        available_control = self._robot_handler.set_joint_angles(
            joint_angles, name=True
        )
        if available_control == 0:
            self.logger.warning("No valid data in joint dictionary to send")
            return False

        write_cmd = target_packer(self._robot_handler.robot.hand_joints)
        write_start = write_cmd[0]
        write_values = write_cmd[1:]
        read_start = ModbusMap().modbus_reg_map[feedback_reg_key]
        read_count = self._feedback_register_count(feedback_reg_key)

        self.wait_for_com_freq()
        feedback_data = self._communication_handler.send_receive_data(
            read_start, read_count, write_start, write_values
        )
        self.last_time = time.perf_counter()

        decoded = self._command_handler.get_decoded_feedback_data(
            feedback_data, modbus_key=feedback_reg_key
        )
        self._record_feedback(feedback_reg_key, decoded)
        return self._shape_feedback(feedback_reg_key, decoded)

    def set_get_joint_angles(self, joint_angles: dict):
        """Writes target positions and reads feedback positions in one FC 0x17.

        Args:
            joint_angles: Dictionary of joint targets (must include angles).

        Returns:
            Dict mapping joint name to feedback position, False if no valid
            data, or None if the hand is not awake.
        """
        return self._set_get_joint_field(
            joint_angles,
            self._command_handler.get_target_position_command,
            "feedback_position_start_reg",
        )

    def set_get_joint_speeds(self, joint_angles: dict):
        """Writes target velocities and reads feedback velocities in one FC 0x17.

        Args:
            joint_angles: Dictionary of joint targets (must include velocities).

        Returns:
            Dict mapping joint name to feedback velocity, False if no valid
            data, or None if the hand is not awake.
        """
        return self._set_get_joint_field(
            joint_angles,
            self._command_handler.get_target_velocity_command,
            "feedback_velocity_start_reg",
        )

    def set_get_joint_forces(self, joint_angles: dict):
        """Writes target forces and reads feedback forces in one FC 0x17.

        Args:
            joint_angles: Dictionary of joint targets (must include forces).

        Returns:
            Dict mapping joint name to feedback force, False if no valid
            data, or None if the hand is not awake.
        """
        return self._set_get_joint_field(
            joint_angles,
            self._command_handler.get_target_force_command,
            "feedback_force_start_reg",
        )

    def _check_communication_frequency(self, last_time: float):
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
        robot_set_home_position_cmd = self._command_handler.get_target_position_command(
            self._robot_handler.robot.hand_joints
        )
        if not self._check_communication_frequency(self.last_time):
            return False
        self._communication_handler.send_data(
            robot_set_home_position_cmd, CommandType.TARGET_COMMAND.value
        )
        self.last_time = time.perf_counter()

    def get_voltage(self):
        """Reads the hand's supply voltage feedback.

        Returns:
            Decoded voltage as a float, or None if the hand is not awake.
        """
        return self.get_feedback_data("feedback_voltage_start_reg")

    def get_feedback_data(
        self, start_reg=ModbusMap().modbus_reg_map["feedback_position_start_reg"]
    ):
        """Reads feedback data for a given feedback register range.

        Single entry point for every feedback field -- position, force,
        velocity, temperature, fingertip forces, voltage, error report. The
        public ``get_*`` methods are thin wrappers around this.

        Args:
            start_reg: Either a ModbusMap key name (e.g.
                ``'feedback_force_start_reg'``) or its starting Modbus
                register address, as defined in
                ``ModbusMap().modbus_reg_map``. Defaults to feedback
                position.

        Returns:
            For whole-hand scalar fields (``slave_id_reg``,
            ``feedback_voltage_start_reg``,
            ``feedback_avg_temperature_start_reg``), the single decoded
            value. For ``feedback_force_sensor_start_reg``, a dict keyed by
            finger name. Otherwise, a dict mapping joint name to its decoded
            feedback value. None if the hand is not awake.

        Raises:
            ValueError: If ``start_reg`` does not match a known key or
                address in ``ModbusMap().modbus_reg_map``.
        """
        if not self._check_awake():
            return

        feedback_reg_key = self._resolve_feedback_key(start_reg)
        decoded_feedback_data = self._read_feedback(feedback_reg_key)
        return self._shape_feedback(feedback_reg_key, decoded_feedback_data)

    def get_joint_angles(
        self, start_reg=ModbusMap().modbus_reg_map["feedback_position_start_reg"]
    ):
        """Deprecated alias for :meth:`get_feedback_data`.

        Kept so code written against the previous release keeps working. The
        name was misleading -- this reads any feedback field, not just
        angles. Prefer ``get_feedback_data``.

        Args:
            start_reg: Same as :meth:`get_feedback_data`.

        Returns:
            Same as :meth:`get_feedback_data`.
        """
        if (
            not self._warned_get_joint_angles
            and start_reg != ModbusMap().modbus_reg_map["feedback_position_start_reg"]
        ):
            self.logger.warning(
                "get_joint_angles() is deprecated and will be removed in a future release -- use get_feedback_data() instead"
            )
            self._warned_get_joint_angles = True
        return self.get_feedback_data(start_reg)

    def helper_fill_dict_from_feedback_data(self, feedback_data: list):
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

        Fingertip feedback is one x/y/z sample per force sensor. Axis
        count and names come from ``ModbusMap``. Order matches
        Modbus/firmware and ``robot.force_sensors`` iteration order.

        Args:
            feedback_data: Flat list of decoded force values (one triple
                per finger, in finger order).

        Returns:
            Dict mapping finger name to ``{'x': float, 'y': float, 'z':
            float}``, or an empty dict if the robot has no force sensors.
        """
        fs = self._robot_handler.robot.force_sensors
        if not fs:
            return {}
        axes = ModbusMap.FINGERTIP_AXIS_NAMES
        n_axes = ModbusMap.FINGERTIP_AXES
        out = {}
        i = 0
        for finger in fs:
            if i + n_axes - 1 < len(feedback_data):
                out[finger] = {
                    name: feedback_data[i + j] for j, name in enumerate(axes)
                }
            i += n_axes
        return out

    def get_joint_forces(self):
        """Reads joint torque/force feedback from the hand.

        Returns:
            Dict mapping joint name to feedback force value, or None if the
            hand is not awake.
        """
        return self.get_feedback_data("feedback_force_start_reg")

    def get_fingertip_forces(self):
        """Reads the fingertip forces from the hand.

        This matches the decoded x/y/z samples from the bus;
        ``robot.force_sensors`` is updated in parallel for object access.

        Returns:
            Dict keyed by finger name (e.g. thumb, index, ...), each value is
            ``{'x': float, 'y': float, 'z': float}``. None if the hand is not
            awake.
        """
        return self.get_feedback_data(ModbusMap.FINGERTIP_FEEDBACK_KEY)

    def get_joint_speeds(self):
        """Reads joint velocity feedback from the hand.

        Returns:
            Dict mapping joint name to feedback velocity value, or None if
            the hand is not awake.
        """
        return self.get_feedback_data("feedback_velocity_start_reg")

    ### NOT IMPLEMENTED YET ###
    def get_joint_temperatures(self):
        """Reads per-joint temperature feedback from the hand.

        Returns:
            Dict mapping joint name to feedback temperature value, or None
            if the hand is not awake.
        """
        return self.get_feedback_data("feedback_temperature_start_reg")

    def get_avg_temperature(self):
        """Reads the hand's average temperature feedback.

        Returns:
            Decoded average temperature as a float, or None if the hand is
            not awake.
        """
        return self.get_feedback_data("feedback_avg_temperature_start_reg")

    def get_hand_feedback_data(self) -> bool:
        """Reads all feedback types supported by the connected robot.

        Iterates ``self._robot_handler.robot.available_feedback_types`` and
        fetches each one through ``get_feedback_data``, which handles the
        per-field read size and return shape.

        Returns:
            True once all available feedback types have been read, or None
            if the hand is not awake.
        """
        if not self._check_awake():
            return

        for feedback_type in self._robot_handler.robot.available_feedback_types:
            self.get_feedback_data(feedback_type)
        return True

    def get_error_report(self):
        """Reads the per-joint actuator error bitfield report from the hand.

        Returns:
            Dict mapping joint name to its decoded error report value, or
            None if the hand is not awake.
        """
        return self.get_feedback_data("feedback_actuator_error_reg")

    # for compatibility
    def get_streamed_joint_angles(self, dat_type=0):
        """Stub retained for v1 API compatibility.

        Args:
            dat_type: Unused; kept for signature compatibility with v1.

        Returns:
            None. Always logs an error since this is not implemented in
            ArtusAPI.
        """
        self.logger.error("get_streamed_joint_angles is not implemented in ArtusAPIv2")

    def reset(self, joints=None):
        """Sends a reset command for the given number of joints.

        Args:
            joints: Joint # to reset. If None, prompts on stdin for
                a value between 0 and the robot's total joint count.
        """
        if (
            joints is None
            or joints < 0
            or joints > self._robot_handler.robot.number_of_joints - 1
        ):
            self.logger.error(f"Invalid joint number: {joints}")
            return
        reset_command = self._command_handler.get_reset_command(joints)
        self.wait_for_com_freq()
        self._communication_handler.send_data(reset_command)
        self.last_time = time.perf_counter()

        # wait for hand state ready
        if not self._communication_handler.wait_for_ready(vis=False):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")

    def soft_reset(self, joints=None):
        """Sends a reset command for the given number of joints.

        Args:
            joints: Number of joints to reset. If None, prompts on stdin for
                a value between 0 and the robot's total joint count.
        """
        if (
            joints is None
            or joints < 0
            or joints > self._robot_handler.robot.number_of_joints - 1
        ):
            self.logger.error(f"Invalid joint number: {joints}")
            return
        soft_reset_command = self._command_handler.get_soft_reset_command(joints)
        self.wait_for_com_freq()
        self._communication_handler.send_data(soft_reset_command)
        self.last_time = time.perf_counter()

        # wait for hand state ready
        if not self._communication_handler.wait_for_ready(vis=False):
            self.logger.error("Hand timed out waiting for ready")
        else:
            self.logger.info("Hand ready")

    def update_firmware(self, file_location=None, drivers_to_flash=0):
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

        if file_location is None or not file_location.endswith(".bin"):
            self.logger.error(f"Invalid file location: {file_location}")
            return

        self._firmware_updater = FirmwareUpdaterNew(
            communication_handler=self._communication_handler,
            command_handler=self._command_handler,
            file_location=file_location,
            logger=self.logger,
        )

        fw_size = self._firmware_updater.get_bin_file_info()

        # get driver to flash
        if (
            drivers_to_flash == None
            or drivers_to_flash < 0
            or drivers_to_flash > self._robot_handler.robot.number_of_controllers
        ):
            self.logger.error(f"Invalid driver number: {drivers_to_flash}")
            return

        # send commmand
        firmware_cmd = self._command_handler.get_firmware_command(drivers_to_flash)
        self._communication_handler.send_data(
            firmware_cmd
        )  # sent firmware upload command to command register
        self.last_time = time.perf_counter()

        # send firmware data
        # self._firmware_updater.update_firmware_piecewise(fw_size)

        time.sleep(0.5)

        self.logger.info("next line is sending the firmware data")
        # send firmware data
        self._firmware_updater.update_firmware(fw_size)

        # wait for hand state ready
        while self.get_robot_status()[0] == ActuatorState.ACTUATOR_FLASHING.name:
            self.logger.info("Waiting for firmware update to complete")
            time.sleep(2)
