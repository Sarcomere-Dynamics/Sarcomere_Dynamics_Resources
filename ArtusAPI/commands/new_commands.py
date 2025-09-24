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
            if not hasattr(joint_data, 'target_torque'):
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
            command_list.insert(0, 0)
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

    def get_decoded_feedback_data(self,feedback_data:list) -> list:
        """
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
            if len(decoded_data) != self.num_joints:
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

        # from here, guess how much data was sent
        # @todo enumerate feedback types
        if size_of_feedback_data == math.ceil(self.num_joints/2) + 1: # only position data and status
            estimated_feedback_type = FeedbackTypes.POSITION.value
        elif size_of_feedback_data == math.ceil(self.num_joints/2) + 1 + self.num_joints*2  : # both position and torque data and status
            estimated_feedback_type = FeedbackTypes.POSITION_TORQUE.value
        
        elif size_of_feedback_data == self.num_joints*2 : # only torque data
            estimated_feedback_type = FeedbackTypes.TORQUE.value

        elif size_of_feedback_data == math.ceil(self.num_joints/2) : # only temperature data
            estimated_feedback_type = FeedbackTypes.TEMPERATURE.value

        else:
            self.logger.error(f"Unknown feedback data type - feedback length received: {size_of_feedback_data}")
            return None

        self.logger.info(f"Estimated feedback type: {estimated_feedback_type}")


        # do the actual decoding
        decoded_data = []
        match estimated_feedback_type:
            case FeedbackTypes.POSITION.value:
                # create different lists for data
                position_data = feedback_data[1:math.ceil(self.num_joints/2)+1] # position data
                decoded_data = helper_decode_feedback_16b_8b(position_data)
            case FeedbackTypes.POSITION_TORQUE.value:
                # create different lists for data
                position_data = feedback_data[1:math.ceil(self.num_joints/2)+1] # position data
                torque_data = feedback_data[int(self.num_joints/2)+1:] # torque data until the end
                decoded_data = helper_decode_feedback_16b_8b(position_data)
                decoded_data += helper_decode_feedback_16b_float(torque_data)
            case FeedbackTypes.TORQUE.value:
                torque_data = feedback_data # torque data until the end
                decoded_data = helper_decode_feedback_16b_float(torque_data)
            case FeedbackTypes.TEMPERATURE.value:
                temperature_data = feedback_data # temperature data until the end
                decoded_data = helper_decode_feedback_16b_8b(temperature_data)
            case _:
                self.logger.error(f"Unknown feedback data type - feedback length received: {size_of_feedback_data}")
                decoded_data = None

        # decode uiint16_t to uint8_t status data in reg 0
        status_data = [(feedback_data[0] >> 8) & 0xFF, feedback_data[0] & 0xFF]
        return status_data,decoded_data



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
        
        expected = [1, 45]  # start_reg + index/2, target_angle
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
        
        expected = [1, 30, 60]  # start_reg, joint1_angle, joint2_angle
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
        """Test get_decoded_feedback_data with position data only (type 0)"""
        # For 5 joints, we expect int(num_joints/2) + 1 = int(2.5) + 1 = 2 + 1 = 3 values
        # Status byte + position data for 5 joints (2 registers, rounded down)
        feedback_data = [0x01, 0x1234, 0x5678,0x1200]  # status + 2 position registers
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data)
        
        # Position data should be decoded from 16-bit to 8-bit pairs
        # Skipping first element (status), decode remaining elements
        expected = [
            0x12, 0x34,  # First position register
            0x56, 0x78,
            0x12  
        ]
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_position_and_torque(self):
        """Test get_decoded_feedback_data with position and torque data (type 1)"""
        # For 5 joints: num_joints/2 + 1 + num_joints*2 = 2.5 + 1 + 10 = 13.5 (rounded to 14)
        # But the actual calculation is: 5/2 + 1 + 5*2 = 2.5 + 1 + 10 = 13.5
        # Since we're dealing with integer division, let's use 4 joints for cleaner math
        test_commands = NewCommands(num_joints=4)
        
        # 4 joints: 4/2 + 1 + 4*2 = 2 + 1 + 8 = 11 total values
        feedback_data = [0x01,  # status
                        0x1234, 0x5678,  # position data (2 registers for 4 joints)
                        0x0000, 0x3F80,  # torque 1 (float 1.0)
                        0x0000, 0x4000,  # torque 2 (float 2.0)  
                        0x0000, 0x4040,  # torque 3 (float 3.0)
                        0x0000, 0x4080]  # torque 4 (float 4.0)
        
        result = test_commands.get_decoded_feedback_data(feedback_data)
        
        # Position data (8-bit pairs) + torque data (floats)
        expected_position = [0x12, 0x34, 0x56, 0x78]
        expected_torques = [1.0, 2.0, 3.0, 4.0]
        expected = expected_position + expected_torques
        
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_torque_only(self):
        """Test get_decoded_feedback_data with torque data only (type 2)"""
        # For 5 joints: num_joints*2 = 10 values (5 torque floats, 2 registers each)
        feedback_data = [0x0000, 0x3F80,  # 1.0
                        0x0000, 0x4000,   # 2.0
                        0x0000, 0x4040,   # 3.0
                        0x0000, 0x4080,   # 4.0
                        0x0000, 0x40A0]   # 5.0
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data)
        
        expected = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_temperature_only(self):
        """Test get_decoded_feedback_data with temperature data only (type 3)"""
        # For 5 joints: num_joints/2 = 2.5 (rounded to 3) = 3 values
        test_commands = NewCommands(num_joints=6)  # Use 6 joints for cleaner math
        feedback_data = [0x1A2B, 0x3C4D, 0x5E6F]  # 3 temperature registers for 6 joints
        
        result = test_commands.get_decoded_feedback_data(feedback_data)
        
        # Temperature data should be decoded from 16-bit to 8-bit pairs
        expected = [0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F]
        self.assertEqual(result, expected)
    
    def test_get_decoded_feedback_data_unknown_type(self):
        """Test get_decoded_feedback_data with unknown data type"""
        # Provide data that doesn't match any expected pattern
        feedback_data = [0x01, 0x02]  # Too small for any known type
        print(f"Feedback data: {feedback_data} and num joints: {self.new_commands.num_joints}")
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data)
        
        self.assertIsNone(result)
    
    def test_get_decoded_feedback_data_empty(self):
        """Test get_decoded_feedback_data with empty data"""
        feedback_data = []
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data)
        
        self.assertIsNone(result)
    
    def test_helper_decode_feedback_16b_8b(self):
        """Test the helper function for 16-bit to 8-bit conversion"""
        # Create a test instance to access the helper method
        test_data = [0x1234, 0x5678, 0xABCD]
        
        # Since helper functions are nested, we'll test them indirectly through the main function
        # Use temperature data type (type 3) which uses the 16b->8b helper
        test_commands = NewCommands(num_joints=6)
        result = test_commands.get_decoded_feedback_data(test_data)
        
        expected = [18, 52, 86, 120, 171-256, 205-256]
        self.assertEqual(result, expected)
    
    def test_helper_decode_feedback_16b_float(self):
        """Test the helper function for 16-bit to float conversion"""
        # Test torque-only data (type 2) which uses the 16b->float helper
        feedback_data = [0x0000, 0x3F80,  # 1.0
                        0x0000, 0x4000,   # 2.0
                        0x0000, 0x4040,   # 3.0
                        0x0000, 0x4080,   # 4.0
                        0x0000, 0x40A0]   # 5.0
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data)
        
        expected = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(result, expected)
    
    def test_feedback_data_size_calculations(self):
        """Test that feedback data size calculations work correctly"""
        # Test different joint counts
        for num_joints in [4, 6, 8, 10]:
            test_commands = NewCommands(num_joints=num_joints)
            
            # Type 0: position only - should be num_joints/2 + 1
            size_type0 = int(num_joints/2) + 1
            mock_data = [0] * size_type0
            result = test_commands.get_decoded_feedback_data(mock_data)
            self.assertIsNotNone(result, f"Type 0 failed for {num_joints} joints")
            
            # Type 1: position + torque - should be num_joints/2 + 1 + num_joints*2  
            size_type1 = int(num_joints/2) + 1 + num_joints*2
            mock_data = [0] * size_type1
            result = test_commands.get_decoded_feedback_data(mock_data)
            self.assertIsNotNone(result, f"Type 1 failed for {num_joints} joints")
            
            # Type 2: torque only - should be num_joints*2
            size_type2 = num_joints*2
            mock_data = [0] * size_type2  
            result = test_commands.get_decoded_feedback_data(mock_data)
            self.assertIsNotNone(result, f"Type 2 failed for {num_joints} joints")
            
            # Type 3: temperature only - should be num_joints/2
            size_type3 = int(num_joints/2)
            mock_data = [0] * size_type3
            result = test_commands.get_decoded_feedback_data(mock_data)
            self.assertIsNotNone(result, f"Type 3 failed for {num_joints} joints")
    
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
        
        result = self.new_commands.get_decoded_feedback_data(feedback_data)
        
        # Should get back the original float values (with some float precision tolerance)
        self.assertEqual(len(result), len(test_floats))
        for i, expected_float in enumerate(test_floats):
            self.assertAlmostEqual(result[i], expected_float, places=2)

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