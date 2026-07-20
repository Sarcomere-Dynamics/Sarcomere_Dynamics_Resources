"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Loads Standard Bots API credentials/IDs used by the StandardBotsDemo scripts."""

import os
import yaml

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(CONFIG_DIR, 'standard_bots_config.yaml')
EXAMPLE_CONFIG_PATH = os.path.join(CONFIG_DIR, 'standard_bots_config.example.yaml')


def load_standard_bots_config() -> dict:
    """Loads Standard Bots credentials/IDs from standard_bots_config.yaml.

    That file is gitignored since it holds a real API token - copy
    standard_bots_config.example.yaml to standard_bots_config.yaml in this
    folder and fill in your own values before running the demo scripts.

    Returns:
        dict: The 'standard_bots' section of the YAML file, containing
        keys such as url, token, robot_kind, routine_id, first_target_id,
        and second_target_id.

    Raises:
        FileNotFoundError: If standard_bots_config.yaml does not exist in
            this folder.
    """
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"{CONFIG_PATH} not found. Copy {EXAMPLE_CONFIG_PATH} to "
            f"'standard_bots_config.yaml' in this folder and fill in your own values."
        )
    with open(CONFIG_PATH, 'r') as file:
        config_dict = yaml.safe_load(file)
    return config_dict['standard_bots']
