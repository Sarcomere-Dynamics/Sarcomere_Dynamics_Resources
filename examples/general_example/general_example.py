"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Interactive CLI demo for exercising the ArtusAPI_V2 hand interface.

Loads the robot configuration, connects to the configured ARTUS hand, and
presents a numbered menu for connecting/disconnecting, waking/sleeping,
calibrating, sending saved hand poses, and reading back feedback data
(position, velocity, torque, fingertip forces, voltage, temperature, and
error reports).
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
from ArtusAPI.common import ModbusMap

# ------------------------------------------------------------------------------
# -------------------------------- Main Menu -----------------------------------
# ------------------------------------------------------------------------------
def main_menu():
    """Prints the interactive command menu and prompts for a selection.

    Returns:
        str: The raw text entered by the user at the prompt.
    """
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
    ║   12 -> Get Fingertip Forces                                     ║
    ║   13 -> Get Voltage                                              ║
    ║   14 -> Get Average Temperature                                  ║
    ║   15 -> Get Joint Temperatures                                   ║
    ║   16 -> Get Error Report                                         ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    >> Input Command Code (1-16): """
    
    )

# ------------------------------------------------------------------------------
# -------------------------------- Logger Setup --------------------------------
# ------------------------------------------------------------------------------
import logging

def setup_logger(level='ERROR',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    """Creates (or reuses) a console logger for the ArtusAPI example.

    Args:
        level: Logging level for both the logger and its console handler
            (e.g. 'ERROR', 'INFO').
        format: Format string passed to logging.Formatter for console
            output.

    Returns:
        logging.Logger: Logger named 'ArtusAPI_Example' with a console
        handler attached (attached only once across repeated calls).
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
# ------------------------------ Command Dispatch --------------------------------
# -------------------------------------------------------------------------------
def handle_command(artusapi, user_input, logger, hand_poses_path):
    """Dispatches a single main_menu() selection against an ArtusAPI_V2 instance.

    Shared between general_example.py and any other example (e.g.
    urarm_rs485_example.py) that presents main_menu() and drives an
    ArtusAPI_V2-connected hand, regardless of the underlying transport.

    Args:
        artusapi: Connected ArtusAPI_V2 instance to operate on.
        user_input: Raw menu selection string returned by main_menu().
        logger: Logger used for status/error output.
        hand_poses_path: Directory containing the saved hand pose JSON
            files (grasp_example.json, grasp_open.json).
    """
    match user_input:
        case '1':
            artusapi.connect()
        case '2':
            artusapi.disconnect()
        case '3':
            control_type = int(input("Enter control type (1: torque, 2: velocity, 3: position): "))
            if control_type not in [1,2,3]:
                logger.warning("Invalid control type, defaulting to position control")
                control_type = 3
            artusapi.wake_up(control_type=control_type)
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
        case 'c':
            artusapi.clear_errors()
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

# -------------------------------------------------------------------------------
# --------------------------------- Example -------------------------------------
# -------------------------------------------------------------------------------
def example():
    """Runs the interactive menu loop for controlling the configured ARTUS hand.

    Loads the robot configuration and API instance, then repeatedly shows
    main_menu() and dispatches the entered command via handle_command().
    Runs until interrupted; per-iteration exceptions are logged and the
    loop continues.
    """
    # Load the configuration file
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
            handle_command(artusapi, user_input, logger, hand_poses_path)
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
# ----------------------------------------------------------------------------------
# ---------------------------------- Main ------------------------------------------
# ----------------------------------------------------------------------------------
if __name__ == '__main__':
    example()
    # import serial
    # x = serial.Serial(port='COM13',baudrate=250000, timeout= 1)
    
    # n = bytearray([0x33])*139
    
    # while True:
    #     x.write(n)
    #     time.sleep(1)
    
    
