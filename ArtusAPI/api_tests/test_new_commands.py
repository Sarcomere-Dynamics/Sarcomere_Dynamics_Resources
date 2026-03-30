"""Unit tests for ArtusAPI.commands.new_commands.NewCommands (no hardware)."""

import logging
import struct
import unittest
from types import SimpleNamespace
from ArtusAPI.commands.new_commands import NewCommands


class TestNewCommands(unittest.TestCase):
    def setUp(self):
        self.nc = NewCommands(num_joints=16, logger=logging.getLogger("test_nc"))

    def test_get_robot_start_command(self):
        cmd = self.nc.get_robot_start_command(control_type=3)
        self.assertEqual(cmd, [self.nc.commands["start_command"], 3])

    def test_get_sleep_command(self):
        self.assertEqual(self.nc.get_sleep_command(), [self.nc.commands["sleep_command"]])

    def test_get_calibration_command(self):
        self.assertEqual(self.nc.get_calibration_command(), [self.nc.commands["calibrate_command"]])

    def test_get_firmware_command(self):
        self.assertEqual(
            self.nc.get_firmware_command(2),
            [self.nc.commands["firmware_update_command"], 2],
        )

    def test_get_reset_command(self):
        self.assertEqual(self.nc.get_reset_command(4), [self.nc.commands["reset_command"], 4])

    def test_get_target_position_single_joint(self):
        j = SimpleNamespace(target_angle=45)
        hand = {"thumb_spread": j}
        out = self.nc.get_target_position_command(hand)
        self.assertEqual(out[0], self.nc.modbus_reg_map["target_position_start_reg"])
        self.assertEqual(len(out), 2)
        self.assertEqual(out[1], (45 << 8) | 0)

    def test_get_target_position_two_joints(self):
        a = SimpleNamespace(target_angle=30)
        b = SimpleNamespace(target_angle=60)
        hand = {"j0": a, "j1": b}
        out = self.nc.get_target_position_command(hand)
        self.assertEqual(out[1], (30 << 8) | 60)

    def test_decode_slave_id_reg(self):
        raw = self.nc.get_decoded_feedback_data(0x00AB, modbus_key="slave_id_reg")
        self.assertEqual(raw, [0xAB & 0xFF])

    def test_decode_feedback_register_int(self):
        raw = self.nc.get_decoded_feedback_data(0xFF09, modbus_key="feedback_register")
        self.assertEqual(raw, [((0xFF09 + 2**15) % 2**16 - 2**15)])

    def test_decode_signed_16b_list(self):
        data = [0x0001, 0xFFFF]
        raw = self.nc.get_decoded_feedback_data(data, modbus_key="feedback_velocity_start_reg")
        self.assertEqual(raw[0], 1)
        self.assertEqual(raw[1], -1)

    def test_decode_float_feedback(self):
        f = 1.25
        b = struct.pack("<f", f)
        w0 = struct.unpack("<H", b[0:2])[0]
        w1 = struct.unpack("<H", b[2:4])[0]
        out = self.nc.get_decoded_feedback_data([w0, w1], modbus_key="feedback_force_start_reg")
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out[0], 1.25, places=5)

    def test_decode_position_8b_packed(self):
        nc4 = NewCommands(num_joints=4, logger=self.nc.logger)
        regs = [(5 << 8) | 6, (7 << 8) | 8]
        out = nc4.get_decoded_feedback_data(regs, modbus_key="feedback_position_start_reg")
        self.assertEqual(len(out), 4)
        self.assertEqual(out, [5, 6, 7, 8])

    def test_get_target_velocity_command(self):
        j = SimpleNamespace(target_velocity=100)
        hand = {"thumb_spread": j}
        out = self.nc.get_target_velocity_command(hand)
        self.assertEqual(out[0], self.nc.modbus_reg_map["target_velocity_start_reg"])
        self.assertIn(100, out)

    def test_get_target_force_command_nonzero(self):
        j = SimpleNamespace(target_force=2.5)
        hand = {"thumb_spread": j}
        out = self.nc.get_target_force_command(hand)
        self.assertEqual(out[0], self.nc.modbus_reg_map["target_force_start_reg"])
        self.assertGreater(len(out), 2)


if __name__ == "__main__":
    unittest.main()
