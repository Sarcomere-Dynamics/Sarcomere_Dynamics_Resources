"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
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
from ArtusAPI.common import ModbusMap
# old ArtusAPI
from ArtusAPI.artus_api import ArtusAPI

# ------------------------------------------------------------------------------
# -------------------------------- Main Menu -----------------------------------
# ------------------------------------------------------------------------------
def main_menu():
    return input(
    """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                          Artus API 2.0                           ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║ Command Options:                                                 ║
    ║                                                                  ║
    ║   1 -> Start connection to hand                                  ║
    ║   2 -> Disconnect from hand                                      ║
    ║   3 -> Wakeup hand                                               ║
    ║   4 -> Enter hand sleep mode                                     ║
    ║   5 -> Calibrate                                                 ║
    ║   6 -> Send command from data/hand_poses/grasp_example           ║
    ║   7 -> Get robot state                                           ║
    ║   8 -> Send command from data/hand_poses/grasp_open              ║
    ║   9 -> Get Feedback Position Data                                ║
    ║   10 -> Get Feedback Velocity Data                               ║
    ║   11 -> Get Feedback Torque Data                                 ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    >> Input Command Code (1-8): """
    
    )

# ------------------------------------------------------------------------------
# -------------------------------- Logger Setup --------------------------------
# ------------------------------------------------------------------------------
import logging

def setup_logger(level='ERROR',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    """
    Set up a logger for the ArtusAPI with proper formatting
    """
    logger = logging.getLogger('ArtusAPI_Example')
    logger.setLevel(level)
    
    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(format)
    console_handler.setFormatter(formatter)
    
    # Add handler to logger if not already added
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger


# -------------------------------------------------------------------------------
# --------------------------------- Example -------------------------------------
# -------------------------------------------------------------------------------
def example():
    # Load the configuration file
    config = ArtusConfig()

    artusapi = None
    hand_poses_path = os.path.join(PROJECT_ROOT,'data','hand_poses')
    logger = setup_logger(level=config.config.logging.level,format=config.config.logging.format)
    # new api
    artusapi = config.get_api(logger=logger)
    
    
    # Main loop (example)
    while True:
        try:
            user_input = main_menu()

            match user_input:
                case '1':
                    artusapi.connect()
                case '2':
                    artusapi.disconnect()
                case '3':
                    if isinstance(artusapi, ArtusAPI_V2):
                        control_type = int(input("Enter control type (1: torque, 2: velocity, 3: position): "))
                        if control_type not in [1,2,3]:
                            logger.warning("Invalid control type, defaulting to position control")
                            control_type = 3
                        artusapi.wake_up(control_type=control_type)
                    else:
                        artusapi.wake_up()
                case '4':
                    artusapi.sleep()
                case '5':
                    artusapi.calibrate()
                case '6':
                    with open(os.path.join(hand_poses_path ,'grasp_example.json'),'r') as file:
                        grasp_example_dict = json.load(file)
                    artusapi.set_joint_angles(grasp_example_dict)
                case '7':
                    logger.info(artusapi.get_robot_status())
                case '8':
                    with open(os.path.join(hand_poses_path ,'grasp_open.json'),'r') as file:
                        grasp_dict = json.load(file)
                    artusapi.set_joint_angles(grasp_dict)
                case '9':
                    artusapi.get_joint_angles()
                case '10':
                    artusapi.get_joint_speeds()
                case '11':
                    artusapi.get_joint_forces()
                case '12':
                    if artusapi._robot_handler.robot.force_sensors is not None:
                        artusapi.get_fingertip_forces()
                    else:
                        logger.error("Fingertip forces are not supported for this robot")
                case 'r':
                    artusapi.reset()
                case 'f':
                    if input(f"DO NOT USE UNLESS SPECIFIED BY SARCOMERE DYNAMICS TEAM. Press `e` to continue") == 'e':
                        driver = int(input("Enter driver to flash (1-6): "))
                        file_location_ = input(f'enter file location of driver: ')
                        artusapi.update_firmware(file_location=file_location_,drivers_to_flash=driver)
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
# ----------------------------------------------------------------------------------
# ---------------------------------- Main ------------------------------------------
# ----------------------------------------------------------------------------------
if __name__ == '__main__':
    example()
