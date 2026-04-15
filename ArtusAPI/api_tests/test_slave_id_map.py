"""Tests for ArtusAPI.common.SlaveIDMap (no I/O)."""

import unittest

from ArtusAPI.common.SlaveIDMap import (
    SLAVE_ID_BY_ROBOT_HAND,
    expected_slave_id,
    normalize_robot_hand_key,
    robot_hand_from_slave_id,
)


class TestSlaveIDMap(unittest.TestCase):
    def test_expected_ids_unique(self):
        vals = list(SLAVE_ID_BY_ROBOT_HAND.values())
        self.assertEqual(len(vals), len(set(vals)))

    def test_inverse_matches(self):
        for (rtype, htype), sid in SLAVE_ID_BY_ROBOT_HAND.items():
            resolved = robot_hand_from_slave_id(sid)
            self.assertIsNotNone(resolved)
            er, eh = resolved
            self.assertEqual(er, rtype)
            self.assertEqual(eh, htype)

    def test_expected_artus_lite_left_right(self):
        self.assertEqual(expected_slave_id("artus_lite", "left"), 1)
        self.assertEqual(expected_slave_id("artus_lite", "right"), 2)

    def test_expected_talos(self):
        self.assertEqual(expected_slave_id("artus_talos", "left"), 5)
        self.assertEqual(expected_slave_id("artus_talos", "right"), 6)

    def test_scorpion_normalizes_hand(self):
        self.assertEqual(normalize_robot_hand_key("artus_scorpion", "right"), ("artus_scorpion", "left"))
        self.assertEqual(expected_slave_id("artus_scorpion", "right"), 7)

    def test_unknown_slave_id(self):
        self.assertIsNone(robot_hand_from_slave_id(0xFF))

    def test_slave_id_masked_to_uint8(self):
        self.assertEqual(robot_hand_from_slave_id(0x105), robot_hand_from_slave_id(5))


if __name__ == "__main__":
    unittest.main()
