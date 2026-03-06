"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from ...sensors import ForceSensor
from .artus_lite import ArtusLite


class ArtusLite_Plus(ArtusLite):
    """
    Artus Lite Plus: 16 joints with force sensors per finger.
    """

    def __init__(self,
                 joint_rotation_directions=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                 logger=None):
        super().__init__(joint_rotation_directions=joint_rotation_directions, logger=logger)

        # Force sensor init (one per finger, 3 axes each)
        self.force_sensors = {}
        fingers = ['thumb', 'index', 'middle', 'ring', 'pinky']
        # Joint indices per finger (thumb 0-3, index 4-6, middle 7-9, ring 10-12, pinky 13-15)
        indices = [[0, 1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14, 15]]

        for i in range(len(fingers)):
            self.force_sensors[fingers[i]] = {
                'data': ForceSensor(),
                'indices': indices[i]
            }

        self.available_feedback_types.append('feedback_force_sensor_start_reg')
