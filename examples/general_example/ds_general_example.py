"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""
    This repository has been  modified to work on Sarcomere Dynamics' Demostration and Testing Platform Device.
    The functionality in this repository may not work for normal operation on a standard computer.
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

# ------------------------------------------------------------------------------
# -------------------------------- Main Menu -----------------------------------
# ------------------------------------------------------------------------------
# TODO Need to change this to take in character inputs from DSManager instead of the command line
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
    # TODO Implement functionality in ArtusConfig() to cycle through the slave_id so that it will automatically match with the correct device type
    config = ArtusConfig()

    artusapi = None
    hand_poses_path = os.path.join(PROJECT_ROOT,'data','hand_poses')
    logger = setup_logger(level=config.config.logging.level,format=config.config.logging.format)
    # new api
    artusapi = config.get_api(logger=logger)

    # while True:
    #     artusapi.get_fingertip_forces()
    #     time.sleep(0.5)
    
    
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
                    logger.info(f"Setting joint angles to: {grasp_example_dict} and setting velocity and force to defaults")
                    for key,value in grasp_example_dict.items():
                        grasp_example_dict[key]['target_velocity'] = artusapi._robot_handler.robot.default_velocity
                        grasp_example_dict[key]['target_force'] = artusapi._robot_handler.robot.default_force
                    artusapi.set_joint_angles(grasp_example_dict)
                case '7':
                    logger.info(artusapi.get_robot_status())
                case '8':
                    with open(os.path.join(hand_poses_path ,'grasp_open.json'),'r') as file:
                        grasp_dict = json.load(file)
                    logger.info(f"Setting joint angles to: {grasp_dict} and setting velocity and force to defaults")
                    for key,value in grasp_dict.items():
                        grasp_dict[key]['target_velocity'] = artusapi._robot_handler.robot.default_velocity
                        grasp_dict[key]['target_force'] = artusapi._robot_handler.robot.default_force
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
                case '13':
                    artusapi.get_voltage()
                case '14':
                    artusapi.get_avg_temperature()
                case '15':
                    artusapi.get_joint_temperatures()
                case '16':
                    artusapi.get_error_report()
                case 'r':
                    artusapi.reset()
                case 'f':
                    if input(f"DO NOT USE UNLESS SPECIFIED BY SARCOMERE DYNAMICS TEAM. Press `e` to continue") == 'e':
                        driver = int(input("Enter driver to flash: "))
                        if (driver > artusapi._robot_handler.robot.number_of_controllers or driver < 0):
                            logger.error(f"Invalid driver number, please try again")
                        else:
                            file_location_ = input(f'enter file location of driver: ')
                            artusapi.update_firmware(file_location=file_location_,drivers_to_flash=driver)
                            logger.info(f"Firmware flashed successfully")
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
# ----------------------------------------------------------------------------------
# ---------------------------------- Main ------------------------------------------
# ----------------------------------------------------------------------------------
if __name__ == '__main__':
    example()
