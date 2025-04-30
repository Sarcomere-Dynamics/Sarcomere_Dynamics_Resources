"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.

=========================================================
DEPRACATED DEPRACATED DEPRACATED DEPRACATED DEPRACATED DEPRACATED
=========================================================
"""
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
try:
    from ArtusAPI.artus_api import ArtusAPI  # Attempt to import the pip-installed version
    print("Using pip-installed version of ArtusAPI")
except ModuleNotFoundError:
    from Sarcomere_Dynamics_Resources.ArtusAPI.artus_api import ArtusAPI  # Fallback to the local version
    print("Using local version of ArtusAPI")
comport = input("Please enter the USB Device COM Port: ")

def main(com):
    # Initialize ArtusAPI with specified parameters
    artus = ArtusAPI(
        communication_method='UART',
        communication_channel_identifier=com,
        robot_type='artus_lite',
        hand_type='right',
        reset_on_start=0
    )
    
    # number maps to joint name and joint index and motor`
    joint_lut_right_hand = {
        "1" : [0,0],
        "2" : [2,2],
        "3" : [3,1],
        "4" : [4,0],
        "5" : [6,1],
        "6" : [7,0],
        "7" : [9,2],
        "8" : [10,0],
        "9" : [12,1],
        "10": [13,0],
        "11": [15,2]
    }

    menu_options = """
    This script is a wrapper for resetting joints that are stuck closed.

    Please Enter the number corresponding to the joint. Options are the following:
    1. thumb_flex
    2. thumb_d2
    3. thumb_d1

    4. index_flex
    5. index_d2

    6. middle_flex
    7. middle_d2

    8. ring_flex
    9. ring_d2

    10. pinky_flex
    11. pinky_d2

    Enter Choice: 
    """

    # get joint
    lut = input(menu_options)
    joints = joint_lut_right_hand[lut]

    # start robot
    artus.connect()

    artus.reset(joints[0],joints[1])

    time.sleep(1)

    artus.disconnect()


if __name__ == "__main__":
    # gete com port
    comport = input("Please enter the USB Device COM Port: ")
    while True:
        try:
            main(comport)
        except Exception as e:
            print('Error = '+e)