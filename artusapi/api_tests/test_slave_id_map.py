"""Tests for ArtusAPI.common.SlaveIDMap (no I/O)."""

import unittest

from ArtusAPI.common.SlaveIDMap import (
    SLAVE_ID_BY_ROBOT_HAND,
    expected_slave_id,
    normalize_robot_hand_key,
    robot_hand_from_slave_id,
)


class TestSlaveIDMap(unittest.TestCase):
    """Verifies SlaveIDMap's robot/hand-to-slave-ID mapping and its inverse."""

    def test_expected_ids_unique(self):
        """Verifies every configured slave ID is unique across robot/hand combinations."""
        vals = list(SLAVE_ID_BY_ROBOT_HAND.values())
        self.assertEqual(len(vals), len(set(vals)))

    def test_inverse_matches(self):
        """Verifies robot_hand_from_slave_id inverts every entry in SLAVE_ID_BY_ROBOT_HAND."""
        for (rtype, htype), sid in SLAVE_ID_BY_ROBOT_HAND.items():
            resolved = robot_hand_from_slave_id(sid)
            self.assertIsNotNone(resolved)
            er, eh = resolved
            self.assertEqual(er, rtype)
            self.assertEqual(eh, htype)

    def test_expected_artus_lite_left_right(self):
        """Verifies the expected slave IDs for artus_lite left and right hands."""
        self.assertEqual(expected_slave_id("artus_lite", "left"), 1)
        self.assertEqual(expected_slave_id("artus_lite", "right"), 2)

    def test_expected_talos(self):
        """Verifies the expected slave IDs for artus_talos left and right hands."""
        self.assertEqual(expected_slave_id("artus_talos", "left"), 5)
        self.assertEqual(expected_slave_id("artus_talos", "right"), 6)

    def test_scorpion_normalizes_hand(self):
        """Verifies artus_scorpion/right normalizes to the shared left-hand slave ID."""
        self.assertEqual(normalize_robot_hand_key("artus_scorpion", "right"), ("artus_scorpion", "left"))
        self.assertEqual(expected_slave_id("artus_scorpion", "right"), 7)

    def test_unknown_slave_id(self):
        """Verifies an unmapped slave ID resolves to None."""
        self.assertIsNone(robot_hand_from_slave_id(0xFF))

    def test_slave_id_masked_to_uint8(self):
        """Verifies robot_hand_from_slave_id masks its input to a uint8 before lookup."""
        self.assertEqual(robot_hand_from_slave_id(0x105), robot_hand_from_slave_id(5))


if __name__ == "__main__":
    unittest.main()
