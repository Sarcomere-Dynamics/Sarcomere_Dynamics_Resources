"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.

Uses MediaPipe Tasks API (HandLandmarker). Requires: pip install mediapipe (>= 0.10.31).
On first run, hand_landmarker.task is downloaded to this script's directory.
"""

import cv2
import numpy as np
import math
import time
import urllib.request

# ------------------------------------------------------------------------------
# ---------------------------- Import Libraries --------------------------------
# ------------------------------------------------------------------------------
import json
import os
import sys

import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)
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
#  MEDIAPIPE TASKS HAND LANDMARKER (NEW API)
# ============================================================

mp_hand_connections = vision.HandLandmarksConnections
mp_drawing = vision.drawing_utils
mp_drawing_styles = vision.drawing_styles

HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)


def get_hand_landmarker_model_path():
    """Return path to hand_landmarker.task; download if missing."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, "hand_landmarker.task")
    if os.path.isfile(model_path):
        return model_path
    print("Downloading hand_landmarker.task (one-time)...")
    try:
        urllib.request.urlretrieve(HAND_LANDMARKER_MODEL_URL, model_path)
        print(f"Saved to {model_path}")
    except Exception as e:
        raise RuntimeError(
            f"Could not download hand_landmarker.model. Download from:\n{HAND_LANDMARKER_MODEL_URL}\n"
            f"and place at {model_path}\nError: {e}"
        ) from e
    return model_path


def create_hand_landmarker():
    """Create HandLandmarker in VIDEO mode for webcam."""
    model_path = get_hand_landmarker_model_path()
    base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.VIDEO,
    )
    return vision.HandLandmarker.create_from_options(options)


def rgb_frame_to_mp_image(rgb):
    """Convert numpy RGB (H,W,3) uint8 to MediaPipe Image."""
    rgb = np.ascontiguousarray(rgb)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def draw_hand_landmarks_on_image(rgb_image, hand_landmarks):
    """Draw hand landmarks on RGB image (mutates in place)."""
    mp_drawing.draw_landmarks(
        rgb_image,
        hand_landmarks,
        mp_hand_connections.HAND_CONNECTIONS,
        mp_drawing_styles.get_default_hand_landmarks_style(),
        mp_drawing_styles.get_default_hand_connections_style(),
    )


# Landmark index triplets for angle computation (geometric method)
JOINTS = {
    "thumb_cmc": (5, 0, 1),
    "thumb_mcp": (1, 2, 3),
    "thumb_ip":  (2, 3, 4),
    "thumb_dip": (2,3,4),

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

# Order of joints as expected by the Artus Lite (16 joints)
JOINT_ORDER = [
    "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_dip",
    "index_mcp", "index_pip", "index_dip",
    "middle_mcp", "middle_pip", "middle_dip",
    "ring_mcp", "ring_pip", "ring_dip",
    "pinky_mcp", "pinky_pip", "pinky_dip",
]

def map_range(value, in_min, in_max, out_min, out_max, clamp=True):
    """
    Linearly map a value from one range to another.

    value   : number to transform
    in_min  : lower bound of input range
    in_max  : upper bound of input range
    out_min : lower bound of output range
    out_max : upper bound of output range
    clamp   : if True, restrict output to [out_min, out_max]

    Returns a float.
    """

    # Avoid division by zero
    if in_max - in_min == 0:
        raise ValueError("Input range cannot be zero.")

    # Linear interpolation
    scaled = (value - in_min) / (in_max - in_min)
    mapped = out_min + scaled * (out_max - out_min)

    # Clamp output
    if clamp:
        if out_min < out_max:
            mapped = max(out_min, min(out_max, mapped))
        else:
            mapped = max(out_max, min(out_min, mapped))

    return mapped

def map_angle_for_artus(joint_name, flex_deg):
    """
    Map flexion angle (0–180°, where 0 = extended, 180 = flexed) into
    Artus Lite joint command space with per-joint ROM:

        • thumb_cmc        →  -45°   to  +45°
        • finger MCPs     →  -17°   to  +17°
        • all other joints →   0°    to   90°

    Returns an integer command value.
    """

    # Clamp input to valid flexion range
    flex = max(0.0, min(180.0, float(flex_deg)))

    # =========== SPECIAL CASES ============
    if joint_name == "thumb_cmc":
        # 0 → -45    |   180 → +45
        # slope = 90 / 180 = 0.5
        # intercept = -45
        #cmd = 0.5 * flex - 45.0
        cmd = map_range(flex, 120, 140, -45, 45, True)
        #cmd = flex

    elif joint_name in {"index_mcp", "middle_mcp", "ring_mcp", "pinky_mcp"}:
        # 0 → -17    |   180 → +17
        # slope = 34 / 180
        #cmd = (34.0 / 180.0) * flex - 17.0
        #cmd = flex*1.25-10.0
        cmd = map_range(flex, 9, 20, -17, 17, True)

    # ============ DEFAULT CASE ============
    else:
        # 0 → 0      |   180 → 90
        # slope = 90 / 180 = 0.5
        if flex >= 90.0:
            flex = 90.0
        cmd = flex

    return int(round(cmd))


# Finger chains for link-length calibration (landmark indices)
FINGER_CHAINS = {
    "thumb":  [1, 2, 3, 4],     # CMC -> MCP -> IP -> TIP
    "index":  [5, 6, 7, 8],     # MCP -> PIP -> DIP -> TIP
    "middle": [9, 10, 11, 12],
    "ring":   [13, 14, 15, 16],
    "pinky":  [17, 18, 19, 20],
}


# ============================================================
#  ANGLE COMPUTATION FUNCTIONS (GEOMETRIC)
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


def compute_hand_joint_angles_geometric(landmarks):
    """
    Compute flexion angles for all joints from MediaPipe's 3D points,
    using the simple 3-point geometric method.
    """
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])

    angles = {}
    for name, (i1, i2, i3) in JOINTS.items():
        geometric = angle_between_3d(pts[i1], pts[i2], pts[i3])
        angles[name] = geometric_to_flex(geometric)

    return angles


# ============================================================
#  SIMPLE 1D KALMAN FILTER FOR ANGLES
# ============================================================

class AngleKalmanFilter:
    """
    Constant-velocity Kalman filter for a single joint angle.
    State x = [angle, angular_velocity]^T
    """

    def __init__(self, process_var=20.0, measurement_var=50.0):
        # State vector [angle; velocity]
        self.x = np.array([[0.0],
                           [0.0]], dtype=np.float32)
        # Covariance
        self.P = np.eye(2, dtype=np.float32) * 1000.0

        # Process and measurement noise
        self.Q_base = np.array([[0.25, 0.5],
                                [0.5,  1.0]], dtype=np.float32) * process_var
        self.R = np.array([[measurement_var]], dtype=np.float32)

        self.initialized = False

    def predict(self, dt):
        A = np.array([[1.0, dt],
                      [0.0, 1.0]], dtype=np.float32)

        self.x = A @ self.x
        self.P = A @ self.P @ A.T + self.Q_base

    def update(self, z, dt):
        """
        z: measured angle (deg)
        dt: time step (s)
        returns: filtered angle
        """
        z = float(z)

        # First measurement initializes the filter
        if not self.initialized:
            self.x[0, 0] = z
            self.x[1, 0] = 0.0
            self.P = np.eye(2, dtype=np.float32) * 10.0
            self.initialized = True
            return z

        # Predict
        self.predict(dt)

        H = np.array([[1.0, 0.0]], dtype=np.float32)
        y = np.array([[z]], dtype=np.float32) - H @ self.x  # innovation
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)

        # Update
        self.x = self.x + K @ y
        I = np.eye(2, dtype=np.float32)
        self.P = (I - K @ H) @ self.P

        # Return the filtered angle
        return float(self.x[0, 0])


# ============================================================
#  DRAWING THE ANGLES ON THE IMAGE
# ============================================================

def draw_finger_angles(image, angles, origin=(10, 30)):
    x, y = origin
    dy = 20

    cv2.putText(image, "Joint Flex Angles (deg):", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    y += dy

    # Reuse JOINT_ORDER so text matches command ordering
    show = JOINT_ORDER

    for key in show:
        if key in angles:
            txt = f"{key}: {angles[key]:5.1f}"
            cv2.putText(image, txt, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            y += dy


# ============================================================
#  CALIBRATION: FINGER LINK LENGTHS (FLAT HAND)
# ============================================================

def compute_link_lengths_from_landmarks(landmarks):
    """
    Compute per-finger link lengths (3D) given MediaPipe landmarks.
    Returns dict: { finger_name: [l1, l2, l3] }
    """
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
    finger_lengths = {}

    for finger, chain in FINGER_CHAINS.items():
        seg_lengths = []
        for a, b in zip(chain[:-1], chain[1:]):
            seg_lengths.append(np.linalg.norm(pts[a] - pts[b]))
        finger_lengths[finger] = seg_lengths  # 3 segments per finger

    return finger_lengths


def calibrate_finger_lengths(cap, detector, target_samples=50):
    """
    Calibration phase:
    - Shows the camera feed
    - User holds hand flat and presses 'c' to start capturing
    - Collects `target_samples` of finger link lengths and averages them
    Returns:
        avg_lengths: { finger: np.array([l1,l2,l3]) } in MediaPipe's normalized 3D units
    """
    print("\n=== CALIBRATION MODE ===")
    print("Hold your RIGHT hand flat, fingers extended, facing the camera.")
    print("Press 'c' to start capturing calibration samples.")
    print("Press 'q' to abort.\n")

    collecting = False
    samples = {finger: [] for finger in FINGER_CHAINS.keys()}
    frame_timestamp_ms = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Calibration: frame read error.")
            continue

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = rgb_frame_to_mp_image(rgb)
        result = detector.detect_for_video(mp_image, frame_timestamp_ms)
        frame_timestamp_ms += 33

        if not collecting:
            cv2.putText(frame, "CALIBRATION: Hold hand flat, press 'c' to start",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            cv2.putText(frame, "CALIBRATION: Capturing lengths...",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if result.hand_landmarks and result.handedness:
            chosen_idx = 0
            for i in range(len(result.handedness)):
                if result.handedness[i][0].category_name == "Right":
                    chosen_idx = i
                    break

            hand_landmarks = result.hand_landmarks[chosen_idx]
            draw_hand_landmarks_on_image(rgb, hand_landmarks)
            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            if collecting:
                finger_lengths = compute_link_lengths_from_landmarks(hand_landmarks)
                for finger, segs in finger_lengths.items():
                    samples[finger].append(segs)

                n = len(next(iter(samples.values())))
                cv2.putText(frame, f"Samples: {n}/{target_samples}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                if n >= target_samples:
                    print("Calibration: enough samples collected.")
                    break
        else:
            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        cv2.imshow("Calibration - Hold Hand Flat", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c') and not collecting:
            print("Calibration: started sampling...")
            collecting = True

        if key == ord('q') or key == 27:
            print("Calibration aborted by user.")
            return None

    # Compute averages
    avg_lengths = {}
    for finger, seg_list in samples.items():
        if len(seg_list) == 0:
            continue
        arr = np.array(seg_list)  # [N, 3]
        avg_lengths[finger] = np.mean(arr, axis=0)

    print("\n=== CALIBRATION COMPLETE ===")
    for finger, segs in avg_lengths.items():
        print(f"{finger}: {segs}")

    return avg_lengths


# ============================================================
#  IK-BASED JOINT ANGLES (USING FINGER LINK LENGTHS)
# ============================================================

def compute_hand_joint_angles_with_ik(landmarks, finger_link_lengths):
    """
    Combines:
      - Geometric joint angles (3-point method) for MCP and thumb joints
      - Simple 2-link IK for PIP/DIP of index/middle/ring/pinky
        using calibrated segment lengths and base->tip distance.

    Returns dict {joint_name: flex_deg}
    """
    # Start from geometric angles as baseline
    angles = compute_hand_joint_angles_geometric(landmarks)
    if finger_link_lengths is None:
        return angles

    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])

    # Fingers we will override PIP/DIP for (keep MCP & thumb as-is)
    for finger in ["index", "middle", "ring", "pinky"]:
        if finger not in finger_link_lengths:
            continue

        chain = FINGER_CHAINS[finger]
        base_idx = chain[0]
        tip_idx = chain[-1]

        B = pts[base_idx]
        T = pts[tip_idx]

        L1, L2, L3 = finger_link_lengths[finger]
        # Equivalent 2-link: proximal + (middle+distal)
        Lp = max(L1, 1e-6)
        Ld = max(L2 + L3, 1e-6)

        # 3D distance from base to tip
        d = np.linalg.norm(T - B)
        # Clamp d to valid IK range
        d = float(max(1e-6, min(d, Lp + Ld - 1e-6)))

        # 2-link planar IK (only flex magnitude – we ignore azimuth):
        # cos(theta2) = (d^2 - L1^2 - L2^2) / (2 L1 L2)
        cos_q2 = (d * d - Lp * Lp - Ld * Ld) / (2.0 * Lp * Ld)
        cos_q2 = max(-1.0, min(1.0, cos_q2))
        q2 = math.acos(cos_q2)  # rad, 0 = straight, >0 = flex
        q2_deg = math.degrees(q2)

        # Split PIP/DIP flexion from combined "elbow" flex
        pip_flex = q2_deg * 0.6
        dip_flex = q2_deg * 0.4

        # Clamp to 0..180
        pip_flex = max(0.0, min(180.0, pip_flex))
        dip_flex = max(0.0, min(180.0, dip_flex))

        if finger == "index":
            angles["index_pip"] = pip_flex
            angles["index_dip"] = dip_flex
        elif finger == "middle":
            angles["middle_pip"] = pip_flex
            angles["middle_dip"] = dip_flex
        elif finger == "ring":
            angles["ring_pip"] = pip_flex
            angles["ring_dip"] = dip_flex
        elif finger == "pinky":
            angles["pinky_pip"] = pip_flex
            angles["pinky_dip"] = dip_flex

    return angles


# ============================================================
#  MAIN PROGRAM
# ============================================================

def main():
    # hand joints dict holder
    hand_joints = {i: '0' for i in range(16)}

    # Auto-detect camera
    cam_index = find_working_camera()

    # Open camera
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("✗ Failed to open camera.")
        return

    # ArtusAPI
    artus = ArtusAPI(
        communication_method='UART',
        communication_channel_identifier="/dev/ttyUSB0",  # @TODO EDIT ME
        robot_type='artus_lite',                         # @TODO EDIT ME
        hand_type='right',
        reset_on_start=0,
        communication_frequency=40,
        stream=False
    )

    #Need to uncomment to connect the hand
    #artus.connect()

    # === HAND LANDMARKER (MEDIAPIPE TASKS API) ===
    detector = create_hand_landmarker()

    # === CALIBRATION STEP (FINGER LINK LENGTHS) ===
    finger_link_lengths = calibrate_finger_lengths(cap, detector, target_samples=50)
    # finger_link_lengths:
    # { "thumb": np.array([l1,l2,l3]), "index": ..., ... } in normalized 3D units

    # Kalman filters per joint name
    kalman_filters = {
        name: AngleKalmanFilter(process_var=5.0, measurement_var=150.0)
        for name in JOINTS.keys()
    }

    last_print = 0.0
    print_interval = 0.5
    prev_time = time.time()
    frame_timestamp_ms = 0

    # Hand tracking state (to avoid switching when new hands appear)
    tracked_wrist = None
    hand_lost_frames = 0
    max_hand_lost_frames = 10
    max_reacquire_distance = 0.30

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
        mp_image = rgb_frame_to_mp_image(rgb)
        result = detector.detect_for_video(mp_image, frame_timestamp_ms)
        frame_timestamp_ms += 33

        if result.hand_landmarks and result.handedness:
            num_hands = len(result.hand_landmarks)

            wrists = []
            for i in range(num_hands):
                lm = result.hand_landmarks[i][0]  # wrist
                wrists.append(np.array([lm.x, lm.y], dtype=np.float32))

            chosen_index = None

            if tracked_wrist is None or hand_lost_frames >= max_hand_lost_frames:
                right_indices = [
                    i for i in range(len(result.handedness))
                    if result.handedness[i][0].category_name == "Right"
                ]
                if right_indices:
                    chosen_index = right_indices[0]
                else:
                    chosen_index = 0

                tracked_wrist = wrists[chosen_index].copy()
                hand_lost_frames = 0
            else:
                dists = [np.linalg.norm(w - tracked_wrist) for w in wrists]
                min_i = int(np.argmin(dists))
                min_dist = dists[min_i]

                if min_dist < max_reacquire_distance:
                    chosen_index = min_i
                    tracked_wrist = wrists[min_i].copy()
                    hand_lost_frames = 0
                else:
                    hand_lost_frames += 1
                    continue

            hand_landmarks = result.hand_landmarks[chosen_index]
            handedness_label = result.handedness[chosen_index][0].category_name

            draw_hand_landmarks_on_image(rgb, hand_landmarks)
            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            # === IK-based joint angles (with calibrated lengths) ===
            raw_angles = compute_hand_joint_angles_with_ik(
                hand_landmarks,
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
                map_angle_for_artus(joint_name, smoothed_angles.get(joint_name, 0.0))
                for joint_name in JOINT_ORDER
            ]

            # angles_mapped is now a list of 16 ints, one per joint index
            joint_angles = angles_mapped

            # Fill hand_joints with these angles
            for i, angle in enumerate(joint_angles):
                joint = {
                    'index': i,
                    'target_angle': angle,
                    'velocity': 60,
                }
                hand_joints[i] = joint

            # Send angles to Artus Lite
            artus.set_joint_angles(hand_joints)

            # Console print (smoothed + mapped)
            if now - last_print > print_interval:
                print(f"\n{handedness_label} Hand Joint Flex Angles (IK + Kalman):")
                for name, val in smoothed_angles.items():
                    print(f"  {name:10s}: {val:5.1f}")

                print("Mapped joint angles (Artus order):")
                print("JOINT_ORDER:", JOINT_ORDER)
                print("angles_mapped:", joint_angles)

                last_print = now

            # # Draw smoothed angles on frame
            # draw_finger_angles(frame, smoothed_angles)
            # Build a dict of mapped angles keyed by joint name for drawing
            mapped_angle_dict = {
                joint_name: float(angle)
                for joint_name, angle in zip(JOINT_ORDER, joint_angles)
            }

            # Draw **mapped** joint angles on frame
            draw_finger_angles(frame, mapped_angle_dict)

        cv2.imshow("Hand Tracking with IK + Kalman", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
