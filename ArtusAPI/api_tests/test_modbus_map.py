"""Tests for ArtusAPI.common.ModbusMap."""

import unittest

from ArtusAPI.common.ModbusMap import ModbusMap, ActuatorState, CommandType, TrajectoryReturn


class TestModbusMap(unittest.TestCase):
    def setUp(self):
        self.m = ModbusMap()

    def test_slave_id_reg_after_avg_temperature(self):
        regs = self.m.modbus_reg_map
        self.assertLess(regs["feedback_avg_temperature_start_reg"], regs["slave_id_reg"])

    def test_reg_maps_have_same_keys(self):
        self.assertEqual(
            set(self.m.modbus_reg_map.keys()),
            set(self.m.data_type_multiplier_map.keys()),
        )

    def test_command_register_zero(self):
        self.assertEqual(self.m.modbus_reg_map["command_register"], 0)

    def test_actuator_state_enum(self):
        self.assertEqual(ActuatorState.ACTUATOR_IDLE.value, 1)

    def test_command_type_values(self):
        self.assertEqual(CommandType.SETUP_COMMANDS.value, 6)
        self.assertEqual(CommandType.TARGET_COMMAND.value, 16)

    def test_config_command_matches_update_config_opcode(self):
        # CONFIG_COMMAND (68) must equal update_config_command's 0x44 opcode -
        # both identify the same onboard-config write to the firmware.
        self.assertEqual(CommandType.CONFIG_COMMAND.value, 0x44)

    def test_actuator_config_states(self):
        self.assertEqual(ActuatorState.ACTUATOR_CONFIG.value, 14)
        self.assertEqual(ActuatorState.ACTUATOR_CONFIG_FINISH.value, 15)

    def test_trajectory_return_enum(self):
        self.assertEqual(TrajectoryReturn.TRAJECTORY_RUNNING.value, 0)
        self.assertEqual(TrajectoryReturn.TRAJECTORY_STOPPED.value, 1)
        self.assertEqual(TrajectoryReturn.TRAJECTORY_COMPLETE.value, 2)


if __name__ == "__main__":
    unittest.main()
