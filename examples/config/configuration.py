"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Backward-compatible re-export of ArtusConfig.

Prefer importing from the package itself:

    from artusapi import ArtusConfig
"""

from artusapi.configuration import ArtusConfig, copy_default_config, resolve_config_file

__all__ = ["ArtusConfig", "copy_default_config", "resolve_config_file"]
