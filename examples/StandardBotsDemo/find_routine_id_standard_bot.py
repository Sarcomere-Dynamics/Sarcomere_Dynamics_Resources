"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import os
import sys

try:
    from standardbots import StandardBotsRobot
except ImportError as e:
    raise ImportError(
        "The 'standardbots' package is required for this script. Install it with:\n"
        "  pip install -r examples/StandardBotsDemo/requirements.txt"
    ) from e

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from examples.StandardBotsDemo.standard_bots_config import load_standard_bots_config

# ------------------------------------------------------------------------------
# Utility: list the routines available on your Standard Bots robot, and their
# IDs, so you can populate routine_id/first_target_id/second_target_id in
# standard_bots_config.yaml for standard_bot_example.py.
# ------------------------------------------------------------------------------

sb_config = load_standard_bots_config()

sdk = StandardBotsRobot(
    url=sb_config['url'],
    token=sb_config['token'],
    robot_kind=getattr(StandardBotsRobot.RobotKind, sb_config['robot_kind']),
)

print("Attempting to connect to standard bot...")

with sdk.connection():
    try:
        response = sdk.routine_editor.routines.list(
            limit=100,
            offset=0
        )

        paginated_response = response.ok()

        routines = paginated_response.items

        print("\nConnection Successful! Here is a list of the routines:")
        print("-" * 40)

        for routine in routines:
            print(f"Name: {routine.name}")
            print(f"ID:   {routine.id}")
            print("-" * 40)

    except Exception as e:
        print("\nScript Failed.")
        print(f"Error details: {e}")
