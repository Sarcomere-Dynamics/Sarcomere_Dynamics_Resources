"""Tests for ArtusAPI.robot.Robot model selection (no bus)."""

import unittest

from ArtusAPI.robot import Robot


class TestRobotModels(unittest.TestCase):
    def test_artus_lite_left(self):
        r = Robot(robot_type="artus_lite", hand_type="left")
        self.assertEqual(r.robot_type, "artus_lite")
        self.assertEqual(r.robot.number_of_joints, 16)

    def test_artus_lite_plus_right(self):
        r = Robot(robot_type="artus_lite_plus", hand_type="right")
        self.assertIsNotNone(r.robot)

    def test_artus_talos_right(self):
        r = Robot(robot_type="artus_talos", hand_type="right")
        self.assertIsNotNone(r.robot)

    def test_artus_scorpion(self):
        r = Robot(robot_type="artus_scorpion", hand_type="left")
        self.assertIsNotNone(r.robot)

    def test_artus_dex_left(self):
        r = Robot(robot_type="artus_dex", hand_type="left")
        self.assertIsNotNone(r.robot)

    def test_unknown_robot_raises(self):
        with self.assertRaises(ValueError):
            Robot(robot_type="not_a_robot", hand_type="left")

    def test_unknown_hand_raises(self):
        with self.assertRaises(ValueError):
            Robot(robot_type="artus_lite", hand_type="both")


if __name__ == "__main__":
    unittest.main()
