"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.

REQUIRED PACKAGES:
- mediapipe<=0.10.21
"""

import numpy as np
import time
import logging
import cv2

# ------------------------------------------------------------------------------
# ---------------------------- Import Libraries --------------------------------
# ------------------------------------------------------------------------------
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(
        os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        ))
    )
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

from examples.Tracking.google_mp.artus_mediapipe import ArtusMediaPipe
from examples.Tracking.filter.kalman import AngleKalmanFilter
from examples.config.configuration import ArtusConfig

from ArtusAPI.artus_api import ArtusAPI
from ArtusAPI.artus_api_new import ArtusAPI_V2


# ============================================================
#  MAIN PROGRAM
# ============================================================
# create logger
# Configure logging only if it hasn't been configured yet
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.propagate = True  # Ensure logs propagate to parent loggers

def main():
    artus_media_pipe = ArtusMediaPipe()
    config = ArtusConfig()

    artus_api = config.get_api(logger=logger)

    artus_api.connect()

    if config.get_robot_wake_up(hand_type=artus_api._robot_handler.hand_type):
        artus_api.wake_up()
    if config.get_robot_calibrate(hand_type=artus_api._robot_handler.hand_type):
        artus_api.calibrate()

    # hand joints dict holder
    # @todo : future proof for Artus Dex 
    hand_joints = {artus_media_pipe.ARTUS_JOINT_NAMES[i]: {'target_angle': 0} for i in range(16)}

    # Auto-detect camera
    cam_index = artus_media_pipe.find_working_camera()

    # Open camera
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("✗ Failed to open camera.")
        return

    # === CALIBRATION STEP (FINGER LINK LENGTHS) ===
    finger_link_lengths = artus_media_pipe.calibrate_finger_lengths(cap, target_samples=50)

    # @todo : add calibration for thumb cmc joint

    # Kalman filters per joint name
    kalman_filters = {
        name: AngleKalmanFilter(process_var=5.0, measurement_var=150.0)
        for name in artus_media_pipe.JOINTS.keys()
    }

    last_print = 0.0
    print_interval = 0.5
    prev_time = time.time()

    # Hand tracking state (to avoid switching when new hands appear)
    tracked_wrist = None
    hand_lost_frames = 0
    max_hand_lost_frames = 10
    max_reacquire_distance = 0.30

    # Main While Loop
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame read error.")
            continue

        # Compute dt for Kalman filters
        now = time.time()
        dt = now - prev_time
        prev_time = now
        dt = max(1e-3, min(dt, 0.1))

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = artus_media_pipe.hands.process(rgb)

        if result.multi_hand_landmarks and result.multi_handedness:
            num_hands = len(result.multi_hand_landmarks)

            wrists = []
            for i in range(num_hands):
                lm = result.multi_hand_landmarks[i].landmark[0]  # wrist
                wrists.append(np.array([lm.x, lm.y], dtype=np.float32))

            chosen_index = None

            if tracked_wrist is None or hand_lost_frames >= max_hand_lost_frames:
                # First acquisition (or re-acquire) – prefer RIGHT hand
                right_indices = [
                    i for i, handedness_info in enumerate(result.multi_handedness)
                    if handedness_info.classification[0].label == "Right"
                ]
                if right_indices:
                    chosen_index = right_indices[0]
                else:
                    chosen_index = 0

                tracked_wrist = wrists[chosen_index].copy()
                hand_lost_frames = 0
            else:
                # Keep the closest wrist to the tracked one
                dists = [np.linalg.norm(w - tracked_wrist) for w in wrists]
                min_i = int(np.argmin(dists))
                min_dist = dists[min_i]

                if min_dist < max_reacquire_distance:
                    chosen_index = min_i
                    tracked_wrist = wrists[min_i].copy()
                    hand_lost_frames = 0
                else:
                    hand_lost_frames += 1
                    # Skip this frame to avoid switching to a new hand
                    continue

            hand_lms = result.multi_hand_landmarks[chosen_index]
            handedness = result.multi_handedness[chosen_index]

            # Draw landmarks
            artus_media_pipe.mp_drawing.draw_landmarks(
                frame, hand_lms,
                artus_media_pipe.mp_hands.HAND_CONNECTIONS,
                artus_media_pipe.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2),
                artus_media_pipe.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1)
            )

            # === IK-based joint angles (with calibrated lengths) ===
            raw_angles = artus_media_pipe.compute_hand_joint_angles_with_ik(
                hand_lms.landmark,
                finger_link_lengths
            )

            # Kalman-smoothed angles
            smoothed_angles = {}
            for name, val in raw_angles.items():
                smoothed = kalman_filters[name].update(val, dt)
                smoothed_angles[name] = smoothed

            # === Map smoothed_angles -> Artus joint commands in fixed order ===
            # Build angles_mapped as a list in JOINT_ORDER
            angles_mapped = [
                artus_media_pipe.map_angle_for_artus(joint_name, smoothed_angles.get(joint_name, 0.0))
                for joint_name in artus_media_pipe.JOINT_ORDER
            ]

            # print(f"smoothed_angles: {smoothed_angles}")

            # angles_mapped is now a list of 16 ints, one per joint index
            joint_angles = angles_mapped

            # Fill hand_joints with these angles
            # @todo : change if you'd like
            for i, angle in enumerate(joint_angles):
                joint = {
                    'index': i,
                    'target_angle': angle,
                    'target_force': 10, # forward compatible for Artus BLDC
                    'velocity': 60 # backward compatible for Artus Lite
                }
                hand_joints[artus_media_pipe.ARTUS_JOINT_NAMES[i]] = joint

            # @todo : thumb spread offset
            hand_joints['thumb_spread']['target_angle'] = 0

            # Send angles to Artus Lite
            artus_api.set_joint_angles(joint_angles=hand_joints)

            # Console print (smoothed + mapped)
            if now - last_print > print_interval:
                label = handedness.classification[0].label
                # print(f"\n{label} Hand Joint Flex Angles (IK + Kalman):")
                # for name, val in smoothed_angles.items():
                    # print(f"  {name:10s}: {val:.1f}")

                # print("Mapped joint angles (Artus order):")
                # print("JOINT_ORDER:", artus_media_pipe.JOINT_ORDER)
                # print("angles_mapped:", joint_angles)

                last_print = now

            # # Draw smoothed angles on frame
            # draw_finger_angles(frame, smoothed_angles)
            # Build a dict of mapped angles keyed by joint name for drawing
            mapped_angle_dict = {
                joint_name: float(angle)
                for joint_name, angle in zip(artus_media_pipe.JOINT_ORDER, joint_angles)
            }

            # Draw **mapped** joint angles on frame
            artus_media_pipe.draw_finger_angles(frame, mapped_angle_dict)

        cv2.imshow("Hand Tracking with IK + Kalman", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()