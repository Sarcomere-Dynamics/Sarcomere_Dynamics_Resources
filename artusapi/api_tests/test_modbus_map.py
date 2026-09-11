"""Tests for ArtusAPI.common.ModbusMap."""

import unittest

from artusapi.common.ModbusMap import (
    ModbusMap,
    ActuatorState,
    CommandType,
    TrajectoryReturn,
)


class TestModbusMap(unittest.TestCase):
    """Verifies ModbusMap register layout and the related state/command enums."""

    def setUp(self):
        """Creates a fresh ModbusMap instance for each test."""
        self.m = ModbusMap()

    def test_slave_id_reg_after_avg_temperature(self):
        """Verifies the slave ID register is addressed after the average temperature feedback register."""
        regs = self.m.modbus_reg_map
        self.assertLess(
            regs["feedback_avg_temperature_start_reg"], regs["slave_id_reg"]
        )

    def test_reg_maps_have_same_keys(self):
        """Verifies every register has a corresponding data-type multiplier entry."""
        self.assertEqual(
            set(self.m.modbus_reg_map.keys()),
            set(self.m.data_type_multiplier_map.keys()),
        )

    def test_command_register_zero(self):
        """Verifies the command register is fixed at address 0."""
        self.assertEqual(self.m.modbus_reg_map["command_register"], 0)

    def test_actuator_state_enum(self):
        """Verifies ACTUATOR_IDLE has the expected enum value."""
        self.assertEqual(ActuatorState.ACTUATOR_IDLE.value, 1)

    def test_command_type_values(self):
        """Verifies SETUP_COMMANDS, TARGET_COMMAND, and READ_WRITE_COMMAND opcodes."""
        self.assertEqual(CommandType.SETUP_COMMANDS.value, 6)
        self.assertEqual(CommandType.TARGET_COMMAND.value, 16)
        self.assertEqual(CommandType.READ_WRITE_COMMAND.value, 23)

    def test_config_command_matches_update_config_opcode(self):
        """Verifies CONFIG_COMMAND (68) equals the 0x44 update_config_command opcode."""
        # CONFIG_COMMAND (68) must equal update_config_command's 0x44 opcode -
        # both identify the same onboard-config write to the firmware.
        self.assertEqual(CommandType.CONFIG_COMMAND.value, 0x44)

    def test_actuator_config_states(self):
        """Verifies the ACTUATOR_CONFIG and ACTUATOR_CONFIG_FINISH enum values."""
        self.assertEqual(ActuatorState.ACTUATOR_CONFIG.value, 14)
        self.assertEqual(ActuatorState.ACTUATOR_CONFIG_FINISH.value, 15)

    def test_trajectory_return_enum(self):
        """Verifies the TrajectoryReturn enum values for running, stopped, and complete states."""
        self.assertEqual(TrajectoryReturn.TRAJECTORY_RUNNING.value, 0)
        self.assertEqual(TrajectoryReturn.TRAJECTORY_STOPPED.value, 1)
        self.assertEqual(TrajectoryReturn.TRAJECTORY_COMPLETE.value, 2)

    def test_scalar_feedback_keys_are_in_the_register_map(self):
        """Verifies every scalar feedback key has a register address and multiplier."""
        for key in ModbusMap.SCALAR_FEEDBACK_KEYS:
            self.assertIn(key, self.m.modbus_reg_map)
            self.assertIn(key, self.m.data_type_multiplier_map)

    def test_fingertip_axes_match_names(self):
        """Verifies FINGERTIP_AXES matches the named axis tuple."""
        self.assertEqual(ModbusMap.FINGERTIP_AXES, len(ModbusMap.FINGERTIP_AXIS_NAMES))
        self.assertIn(ModbusMap.FINGERTIP_FEEDBACK_KEY, self.m.modbus_reg_map)

    def test_feedback_register_count_scalar_ignores_joint_count(self):
        """Verifies whole-hand scalar fields use the multiplier as a fixed register count."""
        self.assertEqual(
            self.m.feedback_register_count("feedback_voltage_start_reg", 16), 2
        )
        self.assertEqual(
            self.m.feedback_register_count("feedback_avg_temperature_start_reg", 16), 1
        )
        self.assertEqual(self.m.feedback_register_count("slave_id_reg", 16), 1)

    def test_feedback_register_count_per_joint(self):
        """Verifies per-joint fields scale by the multiplier and joint count."""
        self.assertEqual(
            self.m.feedback_register_count("feedback_velocity_start_reg", 16), 16
        )
        self.assertEqual(
            self.m.feedback_register_count("feedback_force_start_reg", 16), 32
        )

    def test_feedback_register_count_fingertip(self):
        """Verifies fingertip fields scale by sensor count and axes, not joint count."""
        self.assertEqual(
            self.m.feedback_register_count(
                ModbusMap.FINGERTIP_FEEDBACK_KEY, 16, number_of_sensors=5
            ),
            5 * ModbusMap.FINGERTIP_AXES * 2,
        )


if __name__ == "__main__":
    unittest.main()
