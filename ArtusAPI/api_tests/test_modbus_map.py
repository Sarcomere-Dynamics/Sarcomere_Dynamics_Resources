"""Tests for ArtusAPI.common.ModbusMap."""

import unittest

from ArtusAPI.common.ModbusMap import ModbusMap, ActuatorState, CommandType


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


if __name__ == "__main__":
    unittest.main()
