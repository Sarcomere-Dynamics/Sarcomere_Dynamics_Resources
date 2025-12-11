
from enum import Enum

# in-house link https://sarcomere-my.sharepoint.com/:x:/g/personal/ryan_lee_sarcomeredynamics_com/EZc0Efig0G1FmhJh-1EKzkMBEruf7tcIM2OreEytxHWceA?e=opvYYD
class ModbusMap: # Artus Generic Modbus Map
    def __init__(self):
        self.modbus_reg_map = {
            # size is 16b
            'command_register': 0, # input command register
            # size is byte
            'target_position_start_reg': 1, # input target position registers
            # size is float
            'target_torque_start_reg': 50, # input target torque registers
            # size is 16b
            'target_velocity_start_reg': 150, # input target velocity registers
            # size is 16b
            'feedback_register' : 200, # input feedback registers
            # size is byte
            'feedback_position_start_reg': 201, # input feedback position registers
            # size is float
            'feedback_torque_start_reg': 250, # input feedback torque registers
            # size is 16b
            'feedback_velocity_start_reg': 350, # input feedback velocity registers
            # size is byte
            'feedback_temperature_start_reg': 400, # input feedback temperature registers
            # size is byte
            'feedback_actuator_error_reg' : 500,    # feedback error reports
            # size is byte
            'feedback_atuator_motor_mode_reg' : 600, # feedback motor mode
            # size is float
            'feedback_force_sensor_start_reg': 650 # input feedback fingertip force sensors 
        }

        self.data_type_multiplier_map = {
            # size is 16b
            'command_register': 1, # input command register
            # size is byte
            'target_position_start_reg': 0.5, # input target position registers
            # size is float
            'target_torque_start_reg': 2, # input target torque registers
            # size is 16b
            'feedback_velocity_start_reg': 1, # input feedback velocity registers
            # size is 16b
            'feedback_register' : 1, # input feedback registers
            # size is byte
            'feedback_position_start_reg': 0.5, # input feedback position registers
            # size is float
            'feedback_torque_start_reg': 2, # input feedback torque registers
            # size is 16b
            'feedback_velocity_start_reg': 1, # input feedback velocity registers
            # size is byte
            'feedback_temperature_start_reg': 0.5, # input feedback temperature registers
            # size is byte
            'feedback_actuator_error_reg' : 0.5,    # feedback error reports
            # size is byte
            'feedback_atuator_motor_mode_reg' : 0.5, # feedback motor mode
            # size is float
            'feedback_force_sensor_start_reg': 2 # input feedback fingertip force sensors
        }

class ActuatorState(Enum):
    ACTUATOR_INITIALIZING = 0
    ACTUATOR_IDLE = 1
    ACTUATOR_CALIBRATING_LL = 2  # calibrating the rotor position for foc
    ACTUATOR_CALIBRATED_LL = 3
    ACTUATOR_CALIBRATING_HL = 4  # calibrating the endstop position finding for homing
    ACTUATOR_CALIBRATING_STROKE = 5  # calibrating the stroke of the finger
    ACTUATOR_CALIBRATION_FAILED = 6
    ACTUATOR_READY = 7  # ready to receive commmands, setup control modes, etc.
    ACTUATOR_BUSY = 8  # wait for ack from actuator
    ACTUATOR_ERROR = 9
    ACTUATOR_FLASHING_ACK = 11

class CommandType(Enum):
    SETUP_COMMANDS = 6
    TARGET_COMMAND = 16
    FIRMWARE_COMMAND = 33 # actual data being sent