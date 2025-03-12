# ------------------------------------------------------------------------------
# ---------------------------- Import Libraries --------------------------------
# ------------------------------------------------------------------------------
import time
import json
# Add the desired path to the system path
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
# import ArtusAPI
from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI
# import the configuration file
from Sarcomere_Dynamics_Resources.examples.general_example.config.config import ArtusLiteConfig


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
    ║   2 -> Close connection                                          ║
    ║   3 -> Wakeup hand                                               ║
    ║   4 -> Enter hand sleep mode                                     ║
    ║   5 -> Calibrate                                                 ║
    ║   6 -> Send command from data/hand_poses/grasp_example           ║
    ║   7 -> Get robot states                                          ║
    ║   8 -> Send command from data/hand_poses/grasp_open              ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    >> Input Command Code (1-8): """
    
    )


# -------------------------------------------------------------------------------
# --------------------------------- Example -------------------------------------
# -------------------------------------------------------------------------------
def example():
    # Load the configuration file
    config = ArtusLiteConfig()
    # Create an instance of the ArtusAPI class using the configuration file
    artusapi = ArtusAPI(hand_type=config.config.robot.artusLite.hand_type,
                        communication_method=config.config.robot.artusLite.communication_method,
                        communication_channel_identifier=config.config.robot.artusLite.communication_channel_identifier,
                        reset_on_start=config.config.robot.artusLite.reset_on_start,
                        awake = config.config.robot.artusLite.awake,
                        communication_frequency=33)
    # Path to the hand poses
    hand_poses_path = os.path.join(PROJECT_ROOT,'Sarcomere_Dynamics_Resources','data','hand_poses')
    # Main loop (example)
    while True:
        user_input = main_menu()

        match user_input:
            case "1":
                artusapi.connect()
            case "2":
                artusapi.disconnect()
            case "3":
                # artusapi._command_handler.reset_on_start = 1
                artusapi.wake_up()
            case "4":
                artusapi.sleep()
            case "5":
                # artusapi.calibrate(joint=3)
                # time.sleep(1)
                # artusapi.calibrate(joint=8)
                # time.sleep(1)
                # artusapi.calibrate(joint=15)
                # time.sleep(1)
                # artusapi.calibrate(joint=13)
                # artusapi.calibrate(joint=13)

                artusapi.calibrate(calibration_type=1)
            case "6":
                with open(os.path.join(hand_poses_path,'grasp_example.json'),'r') as file:
                    grasp_dict = json.load(file)
                    artusapi.set_joint_angles(grasp_dict)
            case "7":
                try:
                    print(artusapi.get_joint_angles())
                except Exception as e:
                    print(e)
            case "8":
                with open(os.path.join(hand_poses_path ,'grasp_open.json'),'r') as file:
                    grasp_dict = json.load(file)
                    artusapi.set_joint_angles(grasp_dict) 
            case 'f':
                artusapi.update_firmware(upload_flag=None,file_location=None,drivers_to_flash=None)  
            case 'r':
                artusapi.reset()
            case 'c':
                artusapi.hard_close()
            case 's':
                while True:
                    n = input('Enter index value to save grasp in (1-6):')
                    num = None if not n else int(n) if n.isdigit() and 1 <= int(n) <= 6 else None
                    if num is not None or num is None and not n:
                        break
                if num == None:
                    artusapi.save_grasp_onhand() # default save index 1
                else:
                    artusapi.save_grasp_onhand(num)
            case 'g':
                artusapi.get_saved_grasps_onhand()
            case 'p':
                artusapi.update_param()
            case 'e':
                while True:
                    n = input('Enter index value to execute grasp from (1-6):')
                    num = None if not n else int(n) if n.isdigit() and 1 <= int(n) <= 6 else None
                    if num is not None:
                        break

                artusapi.execute_grasp(num)
            case 'w':
                artusapi.wipe_sd()
            case 'q':
                artusapi.set_zero_manual_calibration()


# ----------------------------------------------------------------------------------
# ---------------------------------- Main ------------------------------------------
# ----------------------------------------------------------------------------------
if __name__ == '__main__':
    example()
