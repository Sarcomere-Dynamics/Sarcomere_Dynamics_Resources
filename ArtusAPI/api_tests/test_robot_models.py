"""Tests for ArtusAPI.robot.Robot model selection (no bus)."""

import unittest

from ArtusAPI.robot import Robot


class TestRobotModels(unittest.TestCase):
    """Verifies Robot instantiates the correct subclass for each robot/hand combination."""

    def test_artus_lite_left(self):
        """Verifies artus_lite/left resolves to a 16-joint robot model."""
        r = Robot(robot_type="artus_lite", hand_type="left")
        self.assertEqual(r.robot_type, "artus_lite")
        self.assertEqual(r.robot.number_of_joints, 16)

    def test_artus_lite_plus_right(self):
        """Verifies artus_lite_plus/right resolves to a robot model."""
        r = Robot(robot_type="artus_lite_plus", hand_type="right")
        self.assertIsNotNone(r.robot)

    def test_artus_talos_right(self):
        """Verifies artus_talos/right resolves to a robot model."""
        r = Robot(robot_type="artus_talos", hand_type="right")
        self.assertIsNotNone(r.robot)

    def test_artus_scorpion(self):
        """Verifies artus_scorpion/left resolves to a robot model."""
        r = Robot(robot_type="artus_scorpion", hand_type="left")
        self.assertIsNotNone(r.robot)

    def test_artus_dex_left(self):
        """Verifies artus_dex/left resolves to a robot model."""
        r = Robot(robot_type="artus_dex", hand_type="left")
        self.assertIsNotNone(r.robot)

    def test_unknown_robot_raises(self):
        """Verifies an unrecognized robot_type raises ValueError."""
        with self.assertRaises(ValueError):
            Robot(robot_type="not_a_robot", hand_type="left")

    def test_unknown_hand_raises(self):
        """Verifies an unrecognized hand_type raises ValueError."""
        with self.assertRaises(ValueError):
            Robot(robot_type="artus_lite", hand_type="both")


if __name__ == "__main__":
    unittest.main()
