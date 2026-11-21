"""Manus glove teleoperation example tests with the ArtusAPI mocked (no hardware, no Manus SDK)."""

from __future__ import annotations

import unittest
from unittest.mock import create_autospec

from ArtusAPI.artus_api_new import ArtusAPI_V2
from examples.Teleoperation.ManusGloveControl.manus_glove_controller import ManusGloveController


class TestManusGloveExample(unittest.TestCase):
    """Checks the example calls ArtusAPI_V2 with arguments its real signature accepts."""

    def _controller(self):
        # Skip __init__ so no config file, serial port or Manus executable is needed.
        controller = ManusGloveController.__new__(ManusGloveController)
        controller.artus_api = create_autospec(ArtusAPI_V2, instance=True)
        return controller

    def test_send_joint_angles_matches_set_joint_angles_by_list_signature(self):
        """Verifies _send_joint_angles forwards each hand's list to set_joint_angles_by_list."""
        controller = self._controller()
        left = [1.0] * 16
        right = [2.0] * 16
        controller._send_joint_angles(left, right)
        calls = controller.artus_api.set_joint_angles_by_list.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].kwargs["joint_angles"], left)
        self.assertEqual(calls[1].kwargs["joint_angles"], right)


if __name__ == "__main__":
    unittest.main()
