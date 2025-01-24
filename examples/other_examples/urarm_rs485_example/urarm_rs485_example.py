
# ------------------------------------------------------------------------------
# ---------------------------- Import Libraries --------------------------------
# ------------------------------------------------------------------------------
import time
import json
# Add the desired path to the system path
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
# import ArtusAPI
from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI
# import the configuration file
from Sarcomere_Dynamics_Resources.examples.general_example.config.config import ArtusLiteConfig
# import ArtusAPIPortForwarder
from Sarcomere_Dynamics_Resources.examples.other_examples.urarm_rs485_example.artus_api_port_forwarder import ArtusAPIPortForwarder


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
    # Artus API Port Forwarder
    ROBOT_IP = "192.168.194.129"
    artusAPIPortForwarder = ArtusAPIPortForwarder(robot_ip=ROBOT_IP)
    local_device_name = artusAPIPortForwarder.get_local_device_name()
    communication_method = 'UART'
    
    # Load the configuration file
    config = ArtusLiteConfig()
    # Create an instance of the ArtusAPI class using the configuration file
    artusapi = ArtusAPI(hand_type=config.config.robot.artusLite.hand_type,
                        communication_method=communication_method,
                        communication_channel_identifier=local_device_name,
                        reset_on_start=config.config.robot.artusLite.reset_on_start,
                        awake = config.config.robot.artusLite.awake)
    # Path to the hand poses
    hand_poses_path = os.path.join(PROJECT_ROOT,'data','hand_poses')
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
                artusapi.calibrate()
            case "6":
                with open(os.path.join(hand_poses_path,'grasp_example.json'),'r') as file:
                    grasp_dict = json.load(file)
                    artusapi.set_joint_angles(grasp_dict)
            case "7":
                print(artusapi.get_joint_angles())
            case "8":
                with open(os.path.join(hand_poses_path ,'grasp_open.json'),'r') as file:
                    grasp_dict = json.load(file)
                    artusapi.set_joint_angles(grasp_dict) 
            case 'f':
                artusapi.update_firmware()  
            case 'r':
                artusapi.reset()
            case 'c':
                artusapi.hard_close()
            case 's':
                num = int(input('what index value should this be stored in? (1-6):'))
                if num == None:
                    artusapi.save_grasp_onhand()
                else:
                    artusapi.save_grasp_onhand(num)
            case 'g':
                artusapi.get_saved_grasps_onhand()
            case 'p':
                artusapi.update_param()
            case 'e':
                data = 0
                while 1:
                    data = int(input('enter grasp index to execute from memory (1-6):'))
                    if data in range(1,7):
                        break

                artusapi.execute_grasp(data)

# ----------------------------------------------------------------------------------
# ---------------------------------- Main ------------------------------------------
# ----------------------------------------------------------------------------------
if __name__ == '__main__':
    example()