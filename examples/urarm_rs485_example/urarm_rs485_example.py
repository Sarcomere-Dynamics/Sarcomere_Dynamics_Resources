"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Interactive CLI demo for controlling an ARTUS hand over a UR robot's RS485 port.

Uses ArtusAPIPortForwarder to expose the UR robot's onboard RS485 line as
a local serial device, connects to the ARTUS hand through it using the
ArtusAPI_V2 API, and presents a numbered menu for connecting/
disconnecting, waking/sleeping, calibrating, sending saved hand poses,
and reading back feedback data.
"""
# ------------------------------------------------------------------------------
# ---------------------------- Import Libraries --------------------------------
# ------------------------------------------------------------------------------
import time
import json
# Add the desired path to the system path
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

# import the configuration file
from examples.config.configuration import ArtusConfig

# new version of ArtusAPI use local version
from ArtusAPI.artus_api_new import ArtusAPI_V2

# import ArtusAPIPortForwarder
from examples.UR_PortForward.artus_api_port_forwarder import ArtusAPIPortForwarder

# reuse the interactive menu, logger setup, and command dispatch from the
# general example instead of duplicating them here
from examples.general_example.general_example import main_menu, setup_logger, handle_command

# -------------------------------------------------------------------------------
# --------------------------------- Example -------------------------------------
# -------------------------------------------------------------------------------
def example():
    """Runs the interactive menu loop for controlling an ARTUS hand via UR RS485.

    Starts an ArtusAPIPortForwarder to the UR robot's RS485 port, connects
    to the hand using the ArtusAPI_V2 API, and then repeatedly shows
    main_menu() and dispatches the entered command via handle_command()
    (both shared with general_example.py). Runs until interrupted;
    per-iteration exceptions are logged and the loop continues.
    """
    # Load the configuration file
    config = ArtusConfig()

    # Artus API Port Forwarder
    ROBOT_IP = "192.168.194.129"
    artusAPIPortForwarder = ArtusAPIPortForwarder(robot_ip=ROBOT_IP)
    local_device_name = artusAPIPortForwarder.get_local_device_name()

    hand_poses_path = None
    logger = setup_logger(level=config.config.logging.level,format=config.config.logging.format)

    # find robot type from robot config
    robot_type = config.find_single_robot_type()
    artusapi = ArtusAPI_V2(communication_method='RS485_RTU',
                        communication_channel_identifier=local_device_name,
                        robot_type=robot_type,
                        hand_type=config.config.robots.left_hand_robot.hand_type,
                        baudrate=115200)

    hand_poses_path = os.path.join(PROJECT_ROOT,'data','hand_poses')
    
    # Main loop (example)
    while True:
        try:
            user_input = main_menu()
            handle_command(artusapi, user_input, logger, hand_poses_path)
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
# ----------------------------------------------------------------------------------
# ---------------------------------- Main ------------------------------------------
# ----------------------------------------------------------------------------------
if __name__ == '__main__':
    example()
