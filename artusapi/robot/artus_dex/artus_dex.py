# Sarcomere Dynamics Software License Notice
# ------------------------------------------
# This software is developed by Sarcomere Dynamics Inc.
# for use with the ARTUS family of robotic products.
#
# Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.
#
# Licensed under the Sarcomere Dynamics Software License.
# See the LICENSE file in the repository for full details.

from ..artus_base import ArtusBase


class ArtusDex(ArtusBase):
    """ARTUS Dex hand model: 18 joints (5 fingers + wrist) with velocity/force defaults."""

    def __init__(
        self,
        logger=None,
    ):
        """Initializes the ARTUS Dex joint model and velocity/force defaults.

        Args:
            joint_max_angles: Maximum angle per joint (18 values: thumb,
                index, middle, ring, pinky, wrist).
            joint_min_angles: Minimum angle per joint.
            joint_default_angles: Default (home) angle per joint.
            joint_rotation_directions: +1/-1 rotation multiplier per joint.
            joint_forces: Per-joint force values (unused by base
                construction).
            joint_names: Ordered joint name strings.
            number_of_joints: Total number of joints (18).
            logger: Optional logger instance passed through to ``ArtusBase``.
        """
        super().__init__(
            joint_max_angles=[
                40,
                90,
                90,
                90,  # thumb
                17,
                90,
                90,  # index
                17,
                90,
                90,  # middle
                17,
                90,
                90,  # ring
                17,
                90,
                90,  # pinky
                45,  # pitch
                30,  # yaw
            ],  # wrist
            joint_min_angles=[
                -40,
                0,
                0,
                0,  # thumb
                -17,
                0,
                0,  # index
                -17,
                0,
                0,  # middle
                -17,
                0,
                0,  # ring
                -17,
                0,
                0,  # pinky
                -45,  # pitch
                -30,  # yaw
            ],  # wrist
            joint_default_angles=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            joint_rotation_directions=[
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
                1,
                1,
            ],
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
                "wrist_pitch",
                "wrist_yaw",
            ],
            number_of_joints=18,
            number_of_controllers=24,
            logger=logger,
        )

        # 23 motor boards in firmware actuator order (bldc_c_master dex.h,
        # protocols/robot_errors.yaml motors_list): index = position in this list.
        self.motor_names = [
            "thumb_d3_1",
            "thumb_d3_2",
            "thumb_d2",
            "thumb_d1",
            "index_d3_1",
            "index_d3_2",
            "index_d2",
            "middle_d3_1",
            "middle_d3_2",
            "middle_d2",
            "ring_d3_1",
            "ring_d3_2",
            "ring_d2",
            "pinky_d3_1",
            "pinky_d3_2",
            "pinky_d2",
            "wrist_1",
            "wrist_2",
            "thumb_ext",
            "index_ext",
            "middle_ext",
            "ring_ext",
            "pinky_ext",
        ]

        # speeds (deg/s)
        self.max_velocity = 900
        self.min_velocity = 0
        self.default_velocity = 150

        # forces (N)
        self.max_force = 20
        self.min_force = 0
        self.default_force = 10
