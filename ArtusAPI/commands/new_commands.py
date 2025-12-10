"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import minimalmodbus
import logging
import struct
import unittest
from unittest.mock import Mock, patch
import math

from .commands import Commands
from ..common.ModbusMap import ModbusMap
from ..common.FeedbackTypes import FeedbackTypes
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

    def get_robot_start_command(self, stream:bool=False, freq:int=50) -> list:
        return [self.commands['start_command']]

    def get_target_position_command(self,hand_joints:dict) -> list:
        """
        @param hand_joints: a sorted dictionary of hand joints by index
        @return command_list: a list of commands to send to the hand
                first element is the starting register
                next elements are the data to be sent
        """
        command_list = []
        starting_reg = 0
        attribute = None # target_angle or target_torque

        # Sort joints by their index to ensure proper ordering
        # sorted_joints = dict(sorted(hand_joints.items(), key=lambda x: x[1].index))

        # check that ALL joints have a target angle
        all_have_target_angle = True
        for name, joint_data in hand_joints.items():
            if not hasattr(joint_data, 'target_angle'):
                all_have_target_angle = False
                break

        all_have_target_torque = True   
        for name, joint_data in hand_joints.items():
            if not hasattr(joint_data, 'target_torque') or joint_data.target_torque is None:
                all_have_target_torque = False
                break

        # fill command list with data
        
        if all_have_target_angle:
            self.logger.info(f"Setting target angles")
            for name, joint_data in hand_joints.items():
                # command_list.append(int(joint_data.target_angle))
                tmp = int(joint_data.target_angle)
                if tmp > 127 or tmp < -128:
                    self.logger.warning(f"Target angle {tmp} exceeds 8-bit range (-128 to 127), clamping value")
                    tmp = max(-128, min(127, tmp))
                self.logger.info(f"Target angle: {tmp}")
                if joint_data.index%2 == 0:
                    command_list.append(tmp)
                else:
                    command_list[-1] = command_list[-1] << 8 | tmp # this is assuming it is in order which is an OK assumption due to parameter requirement
            starting_reg = list(hand_joints.values())[0].index # get first joint index
            
            attribute = 'target_angle'
            command_list.insert(0, self.modbus_reg_map['target_position_start_reg'] + int(starting_reg/2))
            # self.logger.info(f"Starting register: {self.modbus_reg_map['target_position_start_reg'] + int(starting_reg/2)}")

        if all_have_target_torque:
            self.logger.info(f"Setting target angles")
            for name, joint_data in hand_joints.items():
                tmp = round(float(joint_data.target_torque), 2)
                self.logger.info(f"Target torque: {tmp}")
                # Convert float to 4 bytes (IEEE 754 format) and then to two 16-bit integers
                byte_representation = struct.pack('<f', tmp)  # Little-endian float to bytes
                int_low = struct.unpack('<H', byte_representation[:2])[0]  # First 2 bytes as uint16
                int_high = struct.unpack('<H', byte_representation[2:])[0]  # Last 2 bytes as uint16
                command_list.append(int_high) # high byte is first (even register index)
                command_list.append(int_low) # low byte is second (odd register index)
            
            
            if attribute is None: # only if target_angle is not actively being set/used
                starting_reg = list(hand_joints.values())[0].index # get first joint index
                command_list.insert(0, self.modbus_reg_map['target_torque_start_reg'] + int(starting_reg*2))
                # self.logger.info(f"Starting register: {self.modbus_reg_map['target_torque_start_reg'] + int(starting_reg*2)}")

        return command_list

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
                    decoded_data.append(float_value)
            return decoded_data

        # feedback type
        estimated_feedback_type = None
        # get size of feedback data
        size_of_feedback_data = len(feedback_data)
        self.logger.info(f"Size of feedback data: {size_of_feedback_data} & num joints: {self.num_joints}")

        # only 1 data type is allowed to be sent back at a time

        # do the actual decoding
        # todo update with more feedbacks
        decoded_data = []
        match ModbusMap().data_type_multiplier_map[modbus_key]:
            case 0.5:
                decoded_data = helper_decode_feedback_16b_8b(feedback_data)
            case 2:
                decoded_data = helper_decode_feedback_16b_float(feedback_data)
            case 1:
                decoded_data = [(feedback_data[0] >> 8) & 0xFF, feedback_data[0] & 0xFF] 

        return decoded_data



    def get_set_zero_command(self):
        return [self.commands['set_zero_command']]

    def get_calibration_command(self):
        return [self.commands['calibrate_command']]

    def get_sleep_command(self):
        return [self.commands['sleep_command']]

    def get_states_command(self,type=0):
        return [self.commands['get_feedback_command']]

    # @todo implement firmware flashing
    def get_firmware_command(self,drivers):
        return [self.commands['firmware_update_command'],drivers]


class TestNewCommands(unittest.TestCase):
    """Unit tests for the NewCommands class"""
    
    def setUp(self):
        """Set up test fixtures"""
        
        # Create a mock NewCommands instance
        self.new_commands = NewCommands(num_joints=5)
    
    def test_get_target_position_command_with_target_angle(self):
        """Test get_target_position_command with target_angle"""
        # Create mock hand joints with target_angle
        mock_joint = Mock(spec_set=['target_angle','index'])
        mock_joint.target_angle = 45
        mock_joint.index = 0
        hand_joints = {'joint1': mock_joint}
        
        result = self.new_commands.get_target_position_command(hand_joints)
        
        expected = [0, 1, 45]  # 0, start_reg + index/2, target_angle
        self.assertEqual(result, expected)
        # self.logger.info.assert_called()
    
    def test_get_target_position_command_with_target_torque(self):
        """Test get_target_position_command with target_torque"""
        # Create mock hand joints with target_torque
        mock_joint = Mock()
        mock_joint.target_torque = 1.5
        mock_joint.index = 2
        hand_joints = {'joint1': mock_joint}
        
        # Mock hasattr to return False for target_angle, True for target_torque
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'target_torque'):
            result = self.new_commands.get_target_position_command(hand_joints)
        
        # Convert 1.5 to IEEE 754 format
        byte_representation = struct.pack('<f', 1.5)
        int_low = struct.unpack('<H', byte_representation[:2])[0]
        int_high = struct.unpack('<H', byte_representation[2:])[0]
        
        expected = [self.new_commands.modbus_reg_map['target_torque_start_reg'] + int(mock_joint.index*2), int_high, int_low]  # start_reg + index*2, high_byte, low_byte
        self.assertEqual(result, expected)
    
    def test_get_target_position_command_multiple_joints(self):
        """Test get_target_position_command with multiple joints"""
        # Create multiple mock joints
        mock_joint1 = Mock(spec_set=['target_angle','index'])
        mock_joint1.target_angle = 30
        mock_joint1.index = 0
        
        mock_joint2 = Mock(spec_set=['target_angle','index'])
        mock_joint2.target_angle = 60
        mock_joint2.index = 1
        
        hand_joints = {'joint1': mock_joint1, 'joint2': mock_joint2}
        
        result = self.new_commands.get_target_position_command(hand_joints)
        
        # The function packs joint1 (index 0, even) and joint2 (index 1, odd) into one 16-bit value
        # joint1 (30) goes in first, joint2 (60) gets shifted and ORed: 30 << 8 | 60 = 7740
        expected = [0, 1, 7740]  # 0, start_reg, packed_angles
        self.assertEqual(result, expected)
    
    def test_get_set_zero_command(self):
        """Test get_set_zero_command"""
        result = self.new_commands.get_set_zero_command()
        expected = [self.new_commands.commands['set_zero_command']]
        self.assertEqual(result, expected)
    
    def test_get_calibration_command(self):
        """Test get_calibration_command"""
        result = self.new_commands.get_calibration_command()
        expected = [self.new_commands.commands['calibrate_command']]
        self.assertEqual(result, expected)
    
    def test_get_sleep_command(self):
        """Test get_sleep_command"""
        result = self.new_commands.get_sleep_command()
        expected = [self.new_commands.commands['sleep_command']]
        self.assertEqual(result, expected)
    
    def test_get_states_command(self):
        """Test get_states_command"""
        result = self.new_commands.get_states_command()
        expected = [self.new_commands.commands['get_feedback_command']]
        self.assertEqual(result, expected)
        
        # Test with type parameter
        result_with_type = self.new_commands.get_states_command(type=1)
        self.assertEqual(result_with_type, expected)
    
    def test_torque_conversion_accuracy(self):
        """Test that torque conversion maintains accuracy"""
        mock_joint = Mock(spec_set=['target_torque','index'])
        mock_joint.target_torque = 3.14159
        mock_joint.index = 0
        hand_joints = {'joint1': mock_joint}
        
        # Mock hasattr to return False for target_angle and True for target_torque
        def mock_hasattr(obj, attr):
            if attr == 'target_angle':
                return False
            elif attr == 'target_torque':
                return True
            return False
        
        with patch('builtins.hasattr', side_effect=mock_hasattr):
            result = self.new_commands.get_target_position_command(hand_joints)
        
        # Verify the conversion process
        rounded_torque = round(3.14159, 2)  # Should be 3.14
        byte_representation = struct.pack('<f', rounded_torque)
        int_low = struct.unpack('<H', byte_representation[:2])[0]
        int_high = struct.unpack('<H', byte_representation[2:])[0]
        
        # For torque command, starting register is target_torque_start_reg + index/2
        expected = [self.new_commands.modbus_reg_map['target_torque_start_reg'] + int(mock_joint.index/2), int_high, int_low]
        self.assertEqual(result, expected)

    def test_get_decoded_feedback_data_position_only(self):
        """Test get_decoded_feedback_data with position data only"""
        # Position data for 5 joints (3 registers to cover 5 joints)
        feedback_data = [0x1234, 0x5678, 0x1200]  # 3 position registers
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_position_start_reg')
        
        # Position data should be decoded from 16-bit to 8-bit pairs
        # All elements decoded, then trimmed to match num_joints (5)
        expected = [
            0x12, 0x34,  # First position register
            0x56, 0x78,  # Second position register
            0x12         # Third position register (trimmed to 5 joints)
        ]
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_position_separate(self):
        """Test get_decoded_feedback_data with position data using position register"""
        # Use 4 joints for cleaner math
        test_commands = NewCommands(num_joints=4)
        
        # Position data for 4 joints (2 registers)
        feedback_data = [0x1234, 0x5678]  # position data (2 registers for 4 joints)
        
        result = test_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_position_start_reg')
        
        # Position data should be decoded from 16-bit to 8-bit pairs
        expected = [0x12, 0x34, 0x56, 0x78]
        
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_torque_only(self):
        """Test get_decoded_feedback_data with torque data only"""
        # For 5 joints: num_joints*2 = 10 values (5 torque floats, 2 registers each)
        feedback_data = [0x0000, 0x3F80,  # 1.0
                        0x0000, 0x4000,   # 2.0
                        0x0000, 0x4040,   # 3.0
                        0x0000, 0x4080,   # 4.0
                        0x0000, 0x40A0]   # 5.0
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_torque_start_reg')
        
        expected = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_temperature_only(self):
        """Test get_decoded_feedback_data with temperature data only"""
        # For 6 joints: num_joints/2 = 3 registers
        test_commands = NewCommands(num_joints=6)  # Use 6 joints for cleaner math
        feedback_data = [0x1A2B, 0x3C4D, 0x5E6F]  # 3 temperature registers for 6 joints
        
        result = test_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_temperature_start_reg')
        
        # Temperature data should be decoded from 16-bit to 8-bit pairs
        expected = [0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F]
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_status_register(self):
        """Test get_decoded_feedback_data with status register (multiplier = 1)"""
        # Status register returns status bytes
        feedback_data = [0x1234]  # Single status register
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_register')
        
        # Should return high and low bytes of the status register
        expected = [0x12, 0x34]
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_empty(self):
        """Test get_decoded_feedback_data with empty data"""
        feedback_data = []
        
        # For position/temperature data (0.5 multiplier), empty data should return empty list
        result = self.new_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_position_start_reg')
        expected = []
        self.assertEqual(result, expected)
        
        # For torque data (2 multiplier), empty data should return empty list
        result = self.new_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_torque_start_reg')
        expected = []
        self.assertEqual(result, expected)
    
    def test_helper_decode_feedback_16b_8b(self):
        """Test the helper function for 16-bit to 8-bit conversion"""
        # Create a test instance to access the helper method
        test_data = [0x1234, 0x5678, 0xABCD]
        
        # Since helper functions are nested, we'll test them indirectly through the main function
        # Use temperature data type which uses the 16b->8b helper
        test_commands = NewCommands(num_joints=6)
        result = test_commands.get_decoded_feedback_data(test_data, modbus_key='feedback_temperature_start_reg')
        
        expected = [18, 52, 86, 120, 171-256, 205-256]
        self.assertEqual(result, expected)
    
    def test_helper_decode_feedback_16b_float(self):
        """Test the helper function for 16-bit to float conversion"""
        # Test torque data which uses the 16b->float helper
        feedback_data = [0x0000, 0x3F80,  # 1.0
                        0x0000, 0x4000,   # 2.0
                        0x0000, 0x4040,   # 3.0
                        0x0000, 0x4080,   # 4.0
                        0x0000, 0x40A0]   # 5.0
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_torque_start_reg')
        
        expected = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(result, expected)
    
    def test_feedback_data_different_modbus_keys(self):
        """Test that different modbus keys work correctly with appropriate data"""
        # Test different joint counts
        for num_joints in [4, 6, 8, 10]:
            test_commands = NewCommands(num_joints=num_joints)
            
            # Position data - multiplier 0.5 (byte data)
            size_position = int(num_joints/2) if num_joints % 2 == 0 else int(num_joints/2) + 1
            mock_data = [0] * size_position
            result = test_commands.get_decoded_feedback_data(mock_data, modbus_key='feedback_position_start_reg')
            self.assertIsNotNone(result, f"Position failed for {num_joints} joints")
            
            # Torque data - multiplier 2 (float data)
            size_torque = num_joints * 2
            mock_data = [0] * size_torque  
            result = test_commands.get_decoded_feedback_data(mock_data, modbus_key='feedback_torque_start_reg')
            self.assertIsNotNone(result, f"Torque failed for {num_joints} joints")
            
            # Temperature data - multiplier 0.5 (byte data)
            size_temperature = int(num_joints/2) if num_joints % 2 == 0 else int(num_joints/2) + 1
            mock_data = [0] * size_temperature
            result = test_commands.get_decoded_feedback_data(mock_data, modbus_key='feedback_temperature_start_reg')
            self.assertIsNotNone(result, f"Temperature failed for {num_joints} joints")
            
            # Status register - multiplier 1 (status data)
            mock_data = [0x1234]
            result = test_commands.get_decoded_feedback_data(mock_data, modbus_key='feedback_register')
            self.assertIsNotNone(result, f"Status failed for {num_joints} joints")
    
    def test_struct_packing_accuracy(self):
        """Test that struct packing/unpacking maintains float accuracy"""
        # Test with known float values that should pack/unpack precisely
        test_floats = [1.0, -1.0, 0.0, 3.14159, -2.718]
        
        feedback_data = []
        for float_val in test_floats:
            # Pack float to bytes, then unpack as two 16-bit values
            byte_representation = struct.pack('<f', float_val)
            int_high = struct.unpack('<H', byte_representation[:2])[0]
            int_low = struct.unpack('<H', byte_representation[2:])[0]
            feedback_data.extend([int_high,int_low])
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_torque_start_reg')
        
        # Should get back the original float values (with some float precision tolerance)
        self.assertEqual(len(result), len(test_floats))
        for i, expected_float in enumerate(test_floats):
            self.assertAlmostEqual(result[i], expected_float, places=2)
    
    def test_get_decoded_feedback_data_force_sensor(self):
        """Test get_decoded_feedback_data with force sensor data"""
        # Force sensor data (multiplier = 2, same as torque)
        feedback_data = [0x0000, 0x3F80,  # 1.0 N
                        0x0000, 0x4000,   # 2.0 N
                        0x0000, 0x4040,   # 3.0 N
                        0x0000, 0x4080,   # 4.0 N
                        0x0000, 0x40A0]   # 5.0 N
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_force_sensor_start_reg')
        
        expected = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_error_register(self):
        """Test get_decoded_feedback_data with error register data"""
        # Error register data (multiplier = 0.5, byte data)
        test_commands = NewCommands(num_joints=6)
        feedback_data = [0x0102, 0x0304, 0x0506]  # 3 registers for 6 joints
        
        result = test_commands.get_decoded_feedback_data(feedback_data, modbus_key='feedback_actuator_error_reg')
        
        # Should decode to individual bytes
        expected = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
        self.assertEqual(result, expected)

    @classmethod
    def run_tests(cls):
        """Run all unit tests for the NewCommands class"""
        suite = unittest.TestLoader().loadTestsFromTestCase(cls)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()


if __name__ == "__main__":
    # Run unit tests if this file is executed directly
    TestNewCommands.run_tests()