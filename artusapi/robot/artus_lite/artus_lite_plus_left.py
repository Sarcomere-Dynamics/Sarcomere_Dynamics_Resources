"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from .artus_lite_plus import ArtusLitePlus


class ArtusLitePlusLeft(ArtusLitePlus):
    """Left-hand variant of the ARTUS Lite Plus."""

    def __init__(self, logger=None):
        """Initializes the left ARTUS Lite Plus hand with mirrored spread joints.

        Args:
            logger: Optional logger instance passed through to
                ``ArtusLitePlus``.
        """
        super().__init__(type="left", logger=logger)
