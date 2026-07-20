"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import time
import json
import os
import sys
import logging

try:
    from standardbots import StandardBotsRobot
except ImportError as e:
    raise ImportError(
        "The 'standardbots' package is required for this demo. Install it with:\n"
        "  pip install -r examples/StandardBotsDemo/requirements.txt"
    ) from e

# ------------------------------------------------------------------------------
# ---------------------------- Artus Hand Setup --------------------------------
# ------------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

from examples.config.configuration import ArtusConfig
from examples.StandardBotsDemo.standard_bots_config import load_standard_bots_config

def setup_logger(level='ERROR', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    logger = logging.getLogger('ArtusAPI_Example')
    logger.setLevel(level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(format))
    if not logger.handlers:
        logger.addHandler(console_handler)
    return logger

# Initialize Configuration & API
config = ArtusConfig()
logger = setup_logger(level=config.config.logging.level, format=config.config.logging.format)
artusapi = config.get_api(logger=logger)
hand_poses_path = os.path.join(PROJECT_ROOT, 'data', 'hand_poses')

# Helper functions to trigger hand movements
def execute_grasp():
    logger.info("Executing Grasp")
    with open(os.path.join(hand_poses_path, 'grasp_example.json'), 'r') as file:
        pose_dict = json.load(file)
    for key in pose_dict.keys():
        pose_dict[key]['target_velocity'] = artusapi._robot_handler.robot.default_velocity
        pose_dict[key]['target_force'] = artusapi._robot_handler.robot.default_force
    artusapi.set_joint_angles(pose_dict)

def execute_open():
    logger.info("Executing Open")
    with open(os.path.join(hand_poses_path, 'grasp_open.json'), 'r') as file:
        pose_dict = json.load(file)
    for key in pose_dict.keys():
        pose_dict[key]['target_velocity'] = artusapi._robot_handler.robot.default_velocity
        pose_dict[key]['target_force'] = artusapi._robot_handler.robot.default_force
    artusapi.set_joint_angles(pose_dict)

# ------------------------------------------------------------------------------
# ----------------------- Artus Hand Initialization ----------------------------
# ------------------------------------------------------------------------------
print("Initializing Artus Hand...")
try:
    # Bypass the manual input prompt and directly start in Position Control (3)
    artusapi.wake_up(control_type=3)

    # Give the hand a couple of seconds to process the command and reach ACTUATOR_IDLE
    time.sleep(2)
    print("Hand is awake and ready in Position Control mode.\n")

except Exception as e:
    logger.error(f"Failed to initialize hand automatically: {e}")

# ------------------------------------------------------------------------------
# ----------------------- Standard Bots Monitor Setup --------------------------
# ------------------------------------------------------------------------------
sb_config = load_standard_bots_config()

sdk = StandardBotsRobot(
    url=sb_config['url'],
    token=sb_config['token'],
    robot_kind=getattr(StandardBotsRobot.RobotKind, sb_config['robot_kind']),
)

routine_id = sb_config['routine_id']
first_target_id = sb_config['first_target_id']
second_target_id = sb_config['second_target_id']

print(f"Monitoring routine: {routine_id}...\n")

last_seen_step = None

# We use a phase tracker to handle the alternating pick/place logic:
# Phase 0: Waiting at T1 to Pick (Grasp)
# Phase 1: Waiting at T2 to Drop (Open)
# Phase 2: Waiting at T1 (Empty Hand)
# Phase 3: Waiting at T2 to Pick (Grasp)
# Phase 4: Waiting at T1 to Drop (Open)
# Phase 5: Waiting at T2 (Empty Hand)
# Repeat the cycle
sequence_phase = 0

with sdk.connection():
    while True:
        try:
            response = sdk.routine_editor.routines.get_state(
                routine_id=routine_id,
            )

            data = response.ok()
            current_step = getattr(data, 'current_step_id', None)

            # Execute logic only when the step changes
            if current_step and current_step != last_seen_step:
                print(f"Robot is currently on step: {current_step}")

                if current_step == first_target_id:
                    if sequence_phase == 0:
                        print("Phase 0: First target reached. Grasping object.")
                        execute_grasp()
                        sequence_phase = 1

                    elif sequence_phase == 2:
                        print("Phase 2: Returned to first target empty. Waiting to move.")
                        # Do nothing, just advance phase
                        sequence_phase = 3

                    elif sequence_phase == 4:
                        print("Phase 4: Returned to first target with object. Releasing.")
                        execute_open()
                        sequence_phase = 5

                elif current_step == second_target_id:
                    if sequence_phase == 1:
                        print("Phase 1: Second target reached. Releasing object.")
                        execute_open()
                        sequence_phase = 2

                    elif sequence_phase == 3:
                        print("Phase 3: Second target reached. Grasping object.")
                        execute_grasp()
                        sequence_phase = 4

                    elif sequence_phase == 5:
                        print("Phase 5: Returned to second target empty. Waiting to move.")
                        # Do nothing, cycle back
                        sequence_phase = 0

                last_seen_step = current_step

        except Exception as e:
            print(f"Network or SDK error: {e}")

        time.sleep(0.5)
