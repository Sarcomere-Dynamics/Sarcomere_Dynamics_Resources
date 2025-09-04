"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from commands import Commands
import minimalmodbus
import logging
import struct
import unittest
from unittest.mock import Mock, patch


class ModbusMap:
    def __init__(self):
        self.modbus_reg_map = {
            'command_register': 0,
            'target_position_start_reg': 1,
            'target_torque_start_reg': 4,
            'feedback_register' : 100,
            'feedback_position_start_reg': 101,
            'feedback_torque_start_reg': 104,
            'feedback_temperature_start_reg': 116,
        }

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

    def get_robot_start_command(self, stream:bool, freq:int) -> list:
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
                command_list.append(int(joint_data.target_angle))
            starting_reg = list(hand_joints.values())[0].index # get first joint index
            
            attribute = 'target_angle'
            command_list.insert(0, self.modbus_reg_map['target_position_start_reg'] + int(starting_reg/2))
            self.logger.info(f"Starting register: {self.modbus_reg_map['target_position_start_reg'] + int(starting_reg/2)}")

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
                self.logger.info(f"Starting register: {self.modbus_reg_map['target_torque_start_reg'] + int(starting_reg*2)}")

        return command_list

    def get_set_zero_command(self):
        return [self.commands['set_zero_command']]

    def get_calibration_command(self):
        return [self.commands['calibrate_command']]

    def get_sleep_command(self):
        return [self.commands['sleep_command']]

    def get_states_command(self,type=0):
        return [self.commands['get_feedback_command']]

    # @todo implement firmware flashing


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
        
        expected = [8, int_high, int_low]  # start_reg + index*2, high_byte, low_byte
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
        mock_joint = Mock()
        mock_joint.target_torque = 3.14159
        mock_joint.index = 0
        hand_joints = {'joint1': mock_joint}
        
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'target_torque'):
            result = self.new_commands.get_target_position_command(hand_joints)
        
        # Verify the conversion process
        rounded_torque = round(3.14159, 2)  # Should be 3.14
        byte_representation = struct.pack('<f', rounded_torque)
        int_low = struct.unpack('<H', byte_representation[:2])[0]
        int_high = struct.unpack('<H', byte_representation[2:])[0]
        
        expected = [4, int_high, int_low]
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