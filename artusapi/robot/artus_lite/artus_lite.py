"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from ..artus_base.artus_base import ArtusBase


class ArtusLite(ArtusBase):
    """ARTUS Lite hand model: 16 joints (5 fingers, no wrist), no force sensors."""

    def __init__(
        self,
        type: str,
        logger=None,
    ):
        """Initializes the ARTUS Lite joint model and speed/velocity/force defaults.

        Args:
            joint_max_angles: Maximum angle per joint (16 values across
                thumb, index, middle, ring, pinky).
            joint_min_angles: Minimum angle per joint.
            joint_default_angles: Default (home) angle per joint.
            joint_rotation_directions: +1/-1 rotation multiplier per joint.
            joint_forces: Per-joint force values (unused by base
                construction).
            joint_names: Ordered joint name strings.
            number_of_joints: Total number of joints (16).
            logger: Optional logger instance passed through to ``BLDCRobot``.
        """

        self.LEFT_ROTATION_DIRECTIONS = [
            -1,
            1,
            1,
            1,
            -1,
            1,
            1,
            -1,
            1,
            1,
            -1,
            1,
            1,
            -1,
            1,
            1,
        ]

        self.RIGHT_ROTATION_DIRECTIONS = [
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
        ]
        match type:
            case "left":
                self.joint_rotation_directions = self.LEFT_ROTATION_DIRECTIONS
            case "right":
                self.joint_rotation_directions = self.RIGHT_ROTATION_DIRECTIONS
            case _:
                self.joint_rotation_directions = self.LEFT_ROTATION_DIRECTIONS

        super().__init__(
            joint_max_angles=[
                40,
                90,
                90,
                90,
                17,
                90,
                90,
                17,
                90,
                90,
                17,
                90,
                90,
                17,
                90,
                90,
            ],
            joint_min_angles=[
                -40,
                0,
                0,
                0,
                -17,
                0,
                0,
                -17,
                0,
                0,
                -17,
                0,
                0,
                -17,
                0,
                0,
            ],
            joint_default_angles=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            joint_rotation_directions=self.joint_rotation_directions,
            joint_forces=[],
            joint_names=[
                "thumb_spread",
                "thumb_flex",
                "thumb_d2",
                "thumb_d1",
                "index_spread",
                "index_flex",
                "index_d2",
                "middle_spread",
                "middle_flex",
                "middle_d2",
                "ring_spread",
                "ring_flex",
                "ring_d2",
                "pinky_spread",
                "pinky_flex",
                "pinky_d2",
            ],
            number_of_joints=16,
            number_of_controllers=9,
            logger=logger,
        )

        # set sensors
        self.available_feedback_types = [
            "feedback_position_start_reg",
            "feedback_force_start_reg",
            "feedback_velocity_start_reg",
        ]

        # speeds (deg/s)
        self.max_velocity = 300
        self.min_velocity = 0
        self.default_velocity = 150

        # forces (N)
        self.max_force = 150
        self.min_force = 0
        self.default_force = 57
