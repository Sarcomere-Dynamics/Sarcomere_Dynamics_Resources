"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from .artus_lite_plus import ArtusLite_Plus


class ArtusLite_Plus_RightHand(ArtusLite_Plus):
    def __init__(self, logger=None):
        super().__init__(
            joint_rotation_directions=[-1, 1, 1, 1,  # thumb
                                       -1, 1, 1,  # index
                                       -1, 1, 1,  # middle
                                       -1, 1, 1,  # ring
                                       -1, 1, 1],  # pinky
            logger=logger
        )
