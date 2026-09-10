"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import logging
from .artus_dex import ArtusDex


class ArtusDex_Left(ArtusDex):
    """Left-hand variant of the ARTUS Dex."""
    def __init__(self,
                 logger=None):
        """Initializes the left ARTUS Dex hand.

        Args:
            logger: Optional logger instance passed through to ``ArtusDex``.
        """
        super().__init__(logger=logger)