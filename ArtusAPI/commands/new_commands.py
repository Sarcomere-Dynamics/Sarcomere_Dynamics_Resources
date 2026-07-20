"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from typing import Any
import logging
import struct
import math

from .commands import Commands
from ..common.ModbusMap import ModbusMap
"""
New Commands Class based on Modbus RTU for RS485 Communication
"""
class NewCommands(Commands,ModbusMap):
    def __init__(self,num_joints,logger=None):
        Commands.__init__(self)
        ModbusMap.__init__(self)
        self.num_joints = num_joints
        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def get_robot_start_command(self, control_type:int=3) -> list:
        """
        Get the robot start command
        :param control_type: 3 for position control, 2 for velocity control, 1 for torque control -- maximum 3 bits
        """
        return [self.commands['start_command'],control_type]

    def get_target_position_command(self,hand_joints:dict) -> list:
        """
        @param hand_joints: a sorted dictionary of hand joints by index
        @return command_list: a list of commands to send to the hand
                first element is the starting register
                next elements are the data to be sent
        """
        tmp_list = []
        starting_reg = self.modbus_reg_map['target_position_start_reg'] # get starting register

        for name, joint_data in hand_joints.items():
            if joint_data.target_angle is not None:
                # constrain target_angle to be size int8_t
                int8_angle = int(joint_data.target_angle)
                if int8_angle < -128 or int8_angle > 127:
                    self.logger.warning(f"target_angle {int8_angle} out of int8_t range, will be truncated.")
                    # Clamp the value to int8_t range
                    int8_angle = max(-128, min(127, int8_angle))
            else:
                int8_angle = 0
            tmp_list.append(int8_angle)
        
        command_list = []
        command_list.append(starting_reg)

        # if number of joints is 1, just fill with 0
        if len(tmp_list) == 1:
            tmp_list.append(0)
        
        for i in range(0, len(tmp_list), 2):
            command_list.append(tmp_list[i] << 8 | tmp_list[i+1])

        # cast all elements to uint16_t
        command_list = [int(x) & 0xFFFF for x in command_list]
        return command_list

    def get_reset_command(self,joints=0):
        """
        @param joints: number of joints to reset
        @return command_list: a list of commands to send to the hand
                first element is the starting register
                next elements are the data to be sent
        """
        return [self.commands['reset_command'],joints]

    def get_target_velocity_command(self,hand_joints:dict) -> list:
        """
        @param hand_joints: a sorted dictionary of hand joints by index
        @return command_list: a list of commands to send to the hand
                first element is the starting register
                next elements are the data to be sent
        """
        tmp_list = []
        starting_reg = self.modbus_reg_map['target_velocity_start_reg'] # get starting register
        tmp_list.append(starting_reg)
        for name,joint_data in hand_joints.items():
            if joint_data.target_velocity is not None:
                # constrain target_velocity to be size int16_t
                int16_velocity = int(joint_data.target_velocity)
                if int16_velocity < -32768 or int16_velocity > 32767:
                    self.logger.warning(f"target_velocity {int16_velocity} out of int16_t range, will be truncated.")
                    # Clamp the value to int16_t range
                    int16_velocity = max(-32768, min(32767, int16_velocity))
            else:
                int16_velocity = 0
            tmp_list.append(int16_velocity)

        return tmp_list

    def get_target_force_command(self,hand_joints:dict) -> list:
        """
        @param hand_joints: a sorted dictionary of hand joints by index
        @return command_list: a list of commands to send to the hand
                first element is the starting register
                next elements are the data to be sent
        """
        tmp_list = []
        starting_reg = self.modbus_reg_map['target_force_start_reg'] # get starting register
        tmp_list.append(starting_reg)
        for name,joint_data in hand_joints.items():
            if joint_data.target_force is not None:
                # round target force to 2 decimal places
                tmp = round(joint_data.target_force, 2)
                byte_representation = struct.pack('<f', tmp)  # Little-endian float to bytes
                int_low = struct.unpack('<H', byte_representation[:2])[0]  # First 2 bytes as uint16
                int_high = struct.unpack('<H', byte_representation[2:])[0]  # Last 2 bytes as uint16
                tmp_list.append(int_high) # high byte is first (even register index)
                tmp_list.append(int_low) # low byte is second (odd register index)
            else:
                tmp_list.append(0)
                tmp_list.append(0)
        return tmp_list

    def get_decoded_feedback_data(self,feedback_data:list,modbus_key:str='feedback_register') -> list:
        """
        @param start_reg: starting register of the feedback data
        Decode the feedback data from byte specific joint map to general list to be put into the hand joint dictionary
        @param feedback_data: list of uint16 values that need to be decoded into properly formatted values (bytes,floats,etc. ) based on value type
        @return decoded_data: list of decoded data in the correct format based on the value type
        """

        def helper_decode_feedback_16b_8b(data:list) -> list:
            """
            Helper function to decode feedback data and temperature (i.e. split 16bit values into two 8bit values)
            """
            decoded_data = []
            for value in data:
                # Split 16-bit value into two 8-bit bytes
                high_byte = ((value >> 8) & 0xFF)  # Extract upper 8 bits
                low_byte = (value & 0xFF)          # Extract lower 8 bits
                
                # Convert to signed 8-bit values using two's complement
                high_byte = high_byte if high_byte < 128 else high_byte - 256
                low_byte = low_byte if low_byte < 128 else low_byte - 256

                decoded_data.append(high_byte)
                decoded_data.append(low_byte)

            # check length of decoded data and make sure it matches the number of joints, if not then remove last element
            if len(decoded_data) != self.num_joints and len(decoded_data) > 0:
                decoded_data.pop()
            return decoded_data

        def helper_decode_feedback_16b_float(data:list) -> list:
            """
            Helper function to decode feedback data from 16bit values, combine and convert to float
            """
            decoded_data = []
            for i in range(0, len(data), 2):
                if i + 1 < len(data):
                    # Pack two 16-bit values into 4 bytes and unpack as IEEE float
                    # Device sends data in big-endian format (high word first)
                    packed_bytes = struct.pack('<HH', data[i], data[i + 1])
                    float_value = struct.unpack('<f', packed_bytes)[0]
                    decoded_data.append(round(float_value, 2))
            return decoded_data

        def helper_decode_feedback_16b_uint32(data:list) -> list:
            """
            Helper for bit-field fields transported as pairs of uint16 registers.
            Firmware packs the low 16 bits at the even register and the high 16
            bits at the odd register (see host_communication.c::get_word). Decode
            as little-endian uint32 per joint — do NOT reinterpret as IEEE float.
            """
            decoded_data = []
            for i in range(0, len(data), 2):
                if i + 1 < len(data):
                    # low word first, high word second (matches get_word() on firmware)
                    packed_bytes = struct.pack('<HH', data[i], data[i + 1])
                    uint32_value = struct.unpack('<I', packed_bytes)[0]
                    decoded_data.append(uint32_value)
            return decoded_data

        def helper_decode_feedback_signed_16b(data:Any) -> Any:
            """
            Helper function to decode signed 16-bit feedback data
            :param data: list of uint16 values that need to be decoded into properly formatted values (bytes,floats,etc. ) based on value type
            :return decoded_data: list of decoded data in the correct format based on the value type
            """
            # each value is an item in list
            if isinstance(data, list):
                return [((v + 2**15) % 2**16 - 2**15) for v in data]
            else:
                return ((data + 2**15) % 2**16 - 2**15)


            

        # feedback type
        estimated_feedback_type = None
        # get size of feedback data
        if isinstance(feedback_data, int):
            size_of_feedback_data = 1
            feedback_data = [feedback_data]
        else:
            size_of_feedback_data = len(feedback_data)
        self.logger.info(f"Size of feedback data: {size_of_feedback_data} & num joints: {self.num_joints}")

        # only 1 data type is allowed to be sent back at a time

        # do the actual decoding
        # todo update with more feedbacks
        decoded_data = []
        if modbus_key == "slave_id_reg":
            if isinstance(feedback_data, int):
                feedback_data = [feedback_data]
            if not feedback_data:
                return []
            return [int(feedback_data[0]) & 0xFF]

        # error_report is a 32-bit bitfield per joint transported as (low_word, high_word).
        # Route it to the uint32 helper so bit flags like DRV_FAULT=0x20 survive intact —
        # the multiplier=2 path would otherwise reinterpret the bytes as IEEE float.
        if modbus_key == "feedback_actuator_error_reg":
            decoded_data = helper_decode_feedback_16b_uint32(feedback_data)
            return decoded_data

        match ModbusMap().data_type_multiplier_map[modbus_key]:
            case 0.5:
                decoded_data = helper_decode_feedback_16b_8b(feedback_data)
            case 2:
                decoded_data = helper_decode_feedback_16b_float(feedback_data)
            case 1:
                # Ensure feedback_data is interpreted as int16_t (signed 16-bit integers)
                decoded_data = [((v + 2**15) % 2**16 - 2**15) for v in feedback_data]

        return decoded_data



    def get_set_zero_command(self):
        return [self.commands['set_zero_command']]

    def get_calibration_command(self):
        return [self.commands['calibrate_command']]

    def get_sleep_command(self):
        return [self.commands['sleep_command']]

    def get_clear_errors_command(self):
        """Explicit host-triggered error clear. Firmware state_machine_process
        consumes this only in ACTUATOR_ERROR (primary recovery) or
        ACTUATOR_IDLE (no-op refresh); swallowed silently in every other
        state. Response is observed via the existing feedback stream
        (FEEDBACK_STATUS register 200 and FEEDBACK_ERROR_START register 500)."""
        return [self.commands['clear_errors_command']]

    def get_states_command(self,type=0):
        return [self.commands['get_feedback_command']]

    # @todo implement firmware flashing
    def get_firmware_command(self,drivers):
        return [self.commands['firmware_update_command'],drivers]

    def update_config_command(self,config_type:int):
        """
        Trigger the hand to enter ACTUATOR_CONFIG for an onboard config write.
        :param config_type: 1 for WiFi SSID, 2 for WiFi password
        """
        return [self.commands['update_config_command'],config_type]

    def update_config_len_command(self,config_reg:list,config_value:str):
        """
        @param config_reg: list of packed 16-bit registers (see NewCommands helper below
               or ArtusAPI_V2.string_to_registers) representing config_value
        @param config_value: the raw string being written, used only for its length
        @return command_list: length-prefixed register payload written starting at register 0
        """
        return [len(config_value),*config_reg]

