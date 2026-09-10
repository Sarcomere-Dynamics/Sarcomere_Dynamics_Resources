import math
from enum import Enum

# in-house link https://sarcomere-my.sharepoint.com/:x:/g/personal/ryan_lee_sarcomeredynamics_com/EZc0Efig0G1FmhJh-1EKzkMBEruf7tcIM2OreEytxHWceA?e=opvYYD
class ModbusMap: # Artus Generic Modbus Map
    """Generic Modbus RTU/TCP register map shared by all ARTUS hands.

    Attributes:
        modbus_reg_map: Mapping of logical register name to its starting
            Modbus register address.
        data_type_multiplier_map: Mapping of the same logical register
            names to the number of 16-bit words used to encode one joint's
            sample: 0.5 means two joints are packed per register (8-bit
            pairs), 1 means one joint per 16-bit register, and 2 means two
            registers per joint (IEEE 754 float, except
            ``feedback_actuator_error_reg`` which is a uint32 bitfield).
        SCALAR_FEEDBACK_KEYS: Whole-hand fields (not one sample per joint).
            Maps register key to a log label. Register count is
            ``data_type_multiplier_map[key]`` with no joint multiplier.
        FINGERTIP_FEEDBACK_KEY: Key for x/y/z per fingertip force sensor.
        FINGERTIP_AXIS_NAMES: Axis order of each fingertip sample.
        FINGERTIP_AXES: Number of axes per fingertip sensor.
    """

    SCALAR_FEEDBACK_KEYS = {
        'feedback_voltage_start_reg': 'Voltage',
        'feedback_avg_temperature_start_reg': 'Average temperature',
        'slave_id_reg': 'slave_id_reg',
    }
    FINGERTIP_FEEDBACK_KEY = 'feedback_force_sensor_start_reg'
    FINGERTIP_AXIS_NAMES = ('x', 'y', 'z')
    FINGERTIP_AXES = 3

    def __init__(self):
        """Initializes the register address map and data-type multipliers."""
        self.modbus_reg_map = {
            # size is 16b
            'command_register': 0, # input command register
            # size is byte
            'target_position_start_reg': 1, # input target position registers
            # size is float
            'target_force_start_reg': 50, # input target force registers
            # size is 16b
            'target_velocity_start_reg': 150, # input target velocity registers
            # size is 16b
            'feedback_register' : 200, # input feedback registers
            # size is byte
            'feedback_position_start_reg': 201, # input feedback position registers
            # size is float
            'feedback_force_start_reg': 250, # input feedback force registers
            # size is 16b
            'feedback_velocity_start_reg': 350, # input feedback velocity registers
            # size is byte
            'feedback_temperature_start_reg': 400, # input feedback temperature registers
            # size is uint32 (2 registers per joint) — see data_type_multiplier_map below
            'feedback_actuator_error_reg' : 500,    # feedback error reports
            # size is byte
            'feedback_atuator_motor_mode_reg' : 600, # feedback motor mode
            # size is float
            'feedback_force_sensor_start_reg': 650, # input feedback fingertip force sensors
            # size is float
            'feedback_voltage_start_reg': 1000, # feedback voltage register (1 value)
            # size is int16_t
            'feedback_avg_temperature_start_reg' : 1002,
            # size is uint8_t (low byte of one holding register)
            'slave_id_reg': 1003,
        }

        self.data_type_multiplier_map = {
            # size is 16b
            'command_register': 1, # input command register
            # size is byte
            'target_position_start_reg': 0.5, # input target position registers
            # size is float
            'target_force_start_reg': 2, # input target force registers
            # size is 16b
            'target_velocity_start_reg': 1, # input feedback velocity registers
            # size is 16b
            'feedback_register' : 1, # input feedback registers
            # size is byte
            'feedback_position_start_reg': 0.5, # input feedback position registers
            # size is float
            'feedback_force_start_reg': 2, # input feedback force registers
            # size is 16b
            'feedback_velocity_start_reg': 1, # input feedback velocity registers
            # size is byte
            'feedback_temperature_start_reg': 0.5, # input feedback temperature registers
            # error_report is a uint32 bitfield per joint (2 registers each).
            # Decoded as uint32 (not IEEE float) — see NewCommands.get_decoded_feedback_data.
            'feedback_actuator_error_reg' : 2,    # feedback error reports (uint32 per joint)
            # size is byte
            'feedback_atuator_motor_mode_reg' : 0.5, # feedback motor mode
            # size is float
            'feedback_force_sensor_start_reg': 2, # input feedback fingertip force sensors
            # size is float
            'feedback_voltage_start_reg': 2, # feedback voltage register (1 value)
            # size is int16_t
            'feedback_avg_temperature_start_reg' : 1,
            # decoded as single uint8 from low byte (see NewCommands.get_decoded_feedback_data)
            'slave_id_reg': 1,
        }

    def feedback_register_count(self, feedback_reg_key, number_of_joints, number_of_sensors=0):
        """How many 16-bit holding registers to read for a feedback field.

        Args:
            feedback_reg_key: Key in ``modbus_reg_map`` /
                ``data_type_multiplier_map``.
            number_of_joints: Joint count of the connected robot. Ignored
                for scalar fields.
            number_of_sensors: Force-sensor count of the connected robot.
                Used only for ``FINGERTIP_FEEDBACK_KEY``.

        Returns:
            Number of consecutive 16-bit registers to request.
        """
        multiplier = self.data_type_multiplier_map[feedback_reg_key]
        if feedback_reg_key in self.SCALAR_FEEDBACK_KEYS:
            return math.ceil(multiplier)
        if feedback_reg_key == self.FINGERTIP_FEEDBACK_KEY:
            return math.ceil(multiplier * number_of_sensors * self.FINGERTIP_AXES)
        return math.ceil(multiplier * number_of_joints)

class ActuatorState(Enum):
    """Firmware actuator state machine values reported in the status register."""

    ACTUATOR_INITIALIZING = 0    # at Boot
    ACTUATOR_IDLE = 1            # idle state, set control type and mode
    ACTUATOR_CALIBRATING_LL = 2  # calibrating the rotor position for foc
    ACTUATOR_CALIBRATING_STROKE = 3  # calibrating the stroke of the finger
    ACTUATOR_SLEEP = 4
    ACTUATOR_WAIT_ACK = 5
    ACTUATOR_READY = 6           # ready to receive commands, setup control modes, etc.
    ACTUATOR_ACTIVE = 7          # active mode, receiving commands in control mode
    ACTUATOR_BUSY = 8            # busy state, waiting for actuator to be ready
    ACTUATOR_ERROR = 9
    ACTUATOR_ALL_CALIBRATE = 10
    ACTUATOR_FLASHING = 11
    ACTUATOR_FLASHING_ACK = 12
    ACTUATOR_RESET = 13
    ACTUATOR_CONFIG = 14         # onboard config write in progress (e.g. WiFi SSID/password)
    ACTUATOR_CONFIG_FINISH = 15  # onboard config write acknowledged

class TrajectoryReturn(Enum):
    """Trajectory sub-state, packed into the upper nibble of the status register
    alongside ActuatorState in the lower nibble."""
    TRAJECTORY_RUNNING = 0
    TRAJECTORY_STOPPED = 1
    TRAJECTORY_COMPLETE = 2

class CommandType(Enum):
    """Modbus function/command grouping used when sending data to the hand."""

    SETUP_COMMANDS = 6
    TARGET_COMMAND = 16
    READ_WRITE_COMMAND = 23  # FC 0x17 Read/Write Multiple Registers
    FIRMWARE_COMMAND = 33 # actual data being sent
    CONFIG_COMMAND = 68 # onboard config write (e.g. WiFi SSID/password), same opcode as update_config_command