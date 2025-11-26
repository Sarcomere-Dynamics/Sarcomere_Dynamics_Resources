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

import cv2
import numpy as np
import mediapipe as mp
import math
import time

# ------------------------------------------------------------------------------
# ---------------------------- Import Libraries --------------------------------
# ------------------------------------------------------------------------------
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

# ============================================================
#  CAMERA AUTO-DETECTION
# ============================================================

def find_working_camera(max_tested=10):
    """
    Scans camera indices from 0 up to max_tested-1.
    Returns the first index that opens successfully and produces frames.
    """
    print("Scanning for available camera...")
    for i in range(max_tested):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                cap.release()
                print(f"✓ Found working camera at index {i}")
                return i
        cap.release()
    raise RuntimeError("✗ No working camera found.")


# ============================================================
#  MEDIAPIPE HAND SETUP
# ============================================================

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

# Landmark index triplets for angle computation
JOINTS = {
    "thumb_cmc": (0, 1, 2),
    "thumb_mcp": (1, 2, 3),
    "thumb_ip":  (2, 3, 4),

    "index_mcp": (0, 5, 6),
    "index_pip": (5, 6, 7),
    "index_dip": (6, 7, 8),

    "middle_mcp": (0, 9, 10),
    "middle_pip": (9, 10, 11),
    "middle_dip": (10, 11, 12),

    "ring_mcp": (0, 13, 14),
    "ring_pip": (13, 14, 15),
    "ring_dip": (14, 15, 16),

    "pinky_mcp": (0, 17, 18),
    "pinky_pip": (17, 18, 19),
    "pinky_dip": (18, 19, 20),
}


# ============================================================
#  ANGLE COMPUTATION FUNCTIONS
# ============================================================

def angle_between_3d(p1, p2, p3):
    """
    Compute geometric angle (deg) at p2 using 3D vectors.
    """
    v1 = p1 - p2
    v2 = p3 - p2

    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return 0.0

    cosang = np.dot(v1, v2) / (n1 * n2)
    cosang = np.clip(cosang, -1.0, 1.0)

    return math.degrees(math.acos(cosang))


def geometric_to_flex(angle_deg):
    """
    Convert geometric angle to flexion angle:
    0° = fully extended, increases with flexion.
    """
    flex = 180.0 - angle_deg
    return max(0, min(180, flex))


def compute_hand_joint_angles(landmarks):
    """
    Compute flexion angles for all joints from MediaPipe's 3D points.
    """
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])

    angles = {}
    for name, (i1, i2, i3) in JOINTS.items():
        geometric = angle_between_3d(pts[i1], pts[i2], pts[i3])
        angles[name] = geometric_to_flex(geometric)

    return angles


# ============================================================
#  DRAWING THE ANGLES ON THE IMAGE
# ============================================================

def draw_finger_angles(image, angles, origin=(10, 30)):
    x, y = origin
    dy = 20

    cv2.putText(image, "Joint Flex Angles (deg):", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    y += dy

    show = [
        "thumb_mcp", "thumb_ip",
        "index_mcp", "index_pip",
        "middle_mcp", "middle_pip",
        "ring_mcp", "ring_pip",
        "pinky_mcp", "pinky_pip"
    ]

    for key in show:
        if key in angles:
            txt = f"{key}: {angles[key]:5.1f}"
            cv2.putText(image, txt, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,255,0), 1)
            y += dy


# ============================================================
#  MAIN PROGRAM
# ============================================================

def main():
    # hand joints dict holder
    hand_joints = {0:'0',1:'0',2:'0',3:'0',4:'0',5:'0',6:'0',7:'0',8:'0',9:'0',10:'0',11:'0',12:'0',13:'0',14:'0',15:'0'}

    # Auto-detect camera
    cam_index = find_working_camera()

    # Open camera
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("✗ Failed to open camera.")
        return
    
    # ArtusAPI 
    # @TODO CHANGE CONFIGS HERE
    # Initialize ArtusAPI with specified parameters
    artus = ArtusAPI(
        communication_method='UART',
        communication_channel_identifier="/dev/ttyUSB0", ### @TODO EDIT ME ###
        robot_type='artus_lite', ### @TODO EDIT ME ###
        hand_type='right',
        reset_on_start=0,
        communication_frequency=40,
        stream=False
    )

    last_print = 0
    print_interval = 0.5

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame read error.")
            continue

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        if result.multi_hand_landmarks and result.multi_handedness:
            # Only use the first detected hand
            hand_lms = result.multi_hand_landmarks[0]
            handedness = result.multi_handedness[0]

            mp_drawing.draw_landmarks(
                frame, hand_lms,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0,255,0), thickness=2),
                mp_drawing.DrawingSpec(color=(0,255,0), thickness=1)
            )

            angles = compute_hand_joint_angles(hand_lms.landmark)

            ## @TODO turn angles into usable angles for artus lite
            angles_mapped = None

            # make sure all ints
            joint_angles = [int(i) for i in angles_mapped]

            for i in range(16):
                joint = {'index':i, 'target_angle': joint_angles[i], 'velocity' : 60}
                hand_joints[i] = joint

            # send angles to artus lite
            artus.set_joint_angles(hand_joints)

            now = time.time()
            if now - last_print > print_interval:
                label = handedness.classification[0].label
                print(f"\n{label} Hand Joint Flex Angles:")
                for name, val in angles.items():
                    print(f"  {name:10s}: {val:5.1f}")
                last_print = now

            draw_finger_angles(frame, angles)
        cv2.imshow("Hand Tracking with Auto Camera Detection", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()