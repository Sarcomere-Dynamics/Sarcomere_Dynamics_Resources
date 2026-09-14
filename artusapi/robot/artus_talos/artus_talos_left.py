"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from .artus_talos import ArtusTalos


class ArtusTalosLeft(ArtusTalos):
    """Left-hand variant of the ARTUS Talos."""

    def __init__(self, logger):
        """Initializes the left ARTUS Talos hand with its narrower thumb-spread limits.

        Args:
            logger: Logger instance passed through to ``ArtusTalos``.
        """
        super().__init__(type="left", logger=logger)
