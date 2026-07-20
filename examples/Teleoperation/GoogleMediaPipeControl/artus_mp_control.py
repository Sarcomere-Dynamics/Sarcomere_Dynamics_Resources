"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.

Uses MediaPipe Tasks API (HandLandmarker). Requires: pip install mediapipe (>= 0.10.31).
On first run, hand_landmarker.task is downloaded to this script's directory.
"""

"""Webcam-based teleoperation demo mapping MediaPipe hand landmarks to ARTUS joints.

Captures webcam frames, runs MediaPipe's HandLandmarker to extract 3D hand
landmarks, converts them to per-joint flexion angles (geometrically, with an
optional IK-assisted refinement based on calibrated finger link lengths),
smooths the angles with a per-joint Kalman filter, and streams the resulting
joint commands to an ARTUS Lite hand via the ArtusAPI_V2 API.
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
from examples.config.configuration import ArtusConfig

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)


# ============================================================
#  CAMERA AUTO-DETECTION
# ============================================================

def find_working_camera(max_tested=10):
    """Scans camera indices to find the first working webcam.

    Args:
        max_tested: Number of camera indices to try, starting from 0.

    Returns:
        int: Index of the first camera that opens and produces a frame.

    Raises:
        RuntimeError: If no working camera is found within max_tested indices.
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
    """Returns the local path to hand_landmarker.task, downloading it if missing.

    Returns:
        str: Absolute path to the hand_landmarker.task model file next to
        this script.

    Raises:
        RuntimeError: If the model file is not already present and the
            download from HAND_LANDMARKER_MODEL_URL fails.
    """
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
    """Creates a MediaPipe HandLandmarker configured for webcam video input.

    Returns:
        vision.HandLandmarker: Detector instance running in VIDEO mode,
        configured to track up to two hands.
    """
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
    """Converts a numpy RGB frame into a MediaPipe Image.

    Args:
        rgb: numpy array of shape (H, W, 3), dtype uint8, in RGB order.

    Returns:
        mp.Image: MediaPipe image wrapping the same pixel data.
    """
    rgb = np.ascontiguousarray(rgb)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


class MonotonicTimestampMS:
    """Generates strictly monotonically increasing timestamps in milliseconds.

    Uses a monotonic clock (perf_counter_ns) and clamps to +1ms if needed.
    This prevents MediaPipe Tasks VIDEO/LIVE_STREAM pipelines from throwing:
        "input timestamp must be monotonically increasing"
    """
    def __init__(self):
        """Initializes the timestamp generator with no prior timestamp."""
        self._last = -1

    def next(self) -> int:
        """Returns the next strictly increasing timestamp in milliseconds.

        Returns:
            int: Current monotonic time in milliseconds, guaranteed to be
            at least 1ms greater than the previously returned value.
        """
        ts = time.perf_counter_ns() // 1_000_000  # monotonic ms
        if ts <= self._last:
            ts = self._last + 1
        self._last = ts
        return int(ts)


def draw_hand_landmarks_on_image(rgb_image, hand_landmarks):
    """Draws hand landmarks and connections onto an RGB image in place.

    Args:
        rgb_image: numpy RGB image array to draw on; mutated in place.
        hand_landmarks: MediaPipe hand landmark list for a single hand.
    """
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
    "thumb_dip": (2, 3, 4),

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
    """Linearly maps a value from one numeric range to another.

    Args:
        value: Number to transform.
        in_min: Lower bound of the input range.
        in_max: Upper bound of the input range.
        out_min: Lower bound of the output range.
        out_max: Upper bound of the output range.
        clamp: If True, restrict the output to [out_min, out_max]
            (or [out_max, out_min] when out_min > out_max).

    Returns:
        float: The value rescaled into the output range.

    Raises:
        ValueError: If in_min equals in_max.
    """
    if in_max - in_min == 0:
        raise ValueError("Input range cannot be zero.")

    scaled = (value - in_min) / (in_max - in_min)
    mapped = out_min + scaled * (out_max - out_min)

    if clamp:
        if out_min < out_max:
            mapped = max(out_min, min(out_max, mapped))
        else:
            mapped = max(out_max, min(out_min, mapped))

    return mapped


def map_angle_for_artus(joint_name, flex_deg):
    """Maps a flexion angle into ARTUS Lite joint command space.

    Input is a flexion angle in degrees (0 = extended, 180 = flexed), which
    is rescaled per joint according to its range of motion:
        - thumb_cmc: -45 deg to +45 deg
        - finger MCPs (index/middle/ring/pinky): -17 deg to +17 deg
        - all other joints: 0 deg to 90 deg

    Args:
        joint_name: Name of the joint, matching a key in JOINT_ORDER.
        flex_deg: Flexion angle in degrees, clamped to [0, 180].

    Returns:
        int: Rounded ARTUS joint command value.
    """
    flex = max(0.0, min(180.0, float(flex_deg)))

    if joint_name == "thumb_cmc":
        cmd = map_range(flex, 120, 140, -45, 45, True)

    elif joint_name in {"index_mcp", "middle_mcp", "ring_mcp", "pinky_mcp"}:
        cmd = map_range(flex, 9, 20, -17, 17, True)

    else:
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
    """Computes the geometric angle at p2 formed by the segments p2-p1 and p2-p3.

    Args:
        p1: numpy array of shape (3,) for the first point.
        p2: numpy array of shape (3,) for the vertex point.
        p3: numpy array of shape (3,) for the third point.

    Returns:
        float: Angle at p2 in degrees, or 0.0 if either segment has
        near-zero length.
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
    """Converts a geometric joint angle into a flexion angle.

    Args:
        angle_deg: Geometric angle in degrees, as returned by
            angle_between_3d (180 deg = straight/extended).

    Returns:
        float: Flexion angle in degrees, clamped to [0, 180], where 0 is
        fully extended and higher values indicate more flexion.
    """
    flex = 180.0 - angle_deg
    return max(0, min(180, flex))


def compute_hand_joint_angles_geometric(landmarks):
    """Computes flexion angles for all joints using the 3-point geometric method.

    Args:
        landmarks: MediaPipe hand landmark list (21 points) with x, y, z
            attributes per point.

    Returns:
        dict: Mapping of joint name (from JOINTS) to flexion angle in
        degrees.
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
    """Constant-velocity Kalman filter for a single joint angle.

    State x = [angle, angular_velocity]^T.
    """

    def __init__(self, process_var=20.0, measurement_var=50.0):
        """Initializes the filter state and noise covariances.

        Args:
            process_var: Process noise variance; scales the state
                transition noise covariance Q.
            measurement_var: Measurement noise variance R for the angle
                observation.
        """
        self.x = np.array([[0.0],
                           [0.0]], dtype=np.float32)
        self.P = np.eye(2, dtype=np.float32) * 1000.0

        self.Q_base = np.array([[0.25, 0.5],
                                [0.5,  1.0]], dtype=np.float32) * process_var
        self.R = np.array([[measurement_var]], dtype=np.float32)

        self.initialized = False

    def predict(self, dt):
        """Propagates the state estimate forward by one time step.

        Args:
            dt: Time elapsed since the previous update, in seconds.
        """
        A = np.array([[1.0, dt],
                      [0.0, 1.0]], dtype=np.float32)

        self.x = A @ self.x
        self.P = A @ self.P @ A.T + self.Q_base

    def update(self, z, dt):
        """Updates the filter with a new angle measurement.

        On the first call the filter is initialized directly from the
        measurement instead of running a predict/correct cycle.

        Args:
            z: Measured joint angle.
            dt: Time elapsed since the previous update, in seconds.

        Returns:
            float: Filtered (smoothed) angle estimate.
        """
        z = float(z)

        if not self.initialized:
            self.x[0, 0] = z
            self.x[1, 0] = 0.0
            self.P = np.eye(2, dtype=np.float32) * 10.0
            self.initialized = True
            return z

        self.predict(dt)

        H = np.array([[1.0, 0.0]], dtype=np.float32)
        y = np.array([[z]], dtype=np.float32) - H @ self.x
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)

        self.x = self.x + K @ y
        I = np.eye(2, dtype=np.float32)
        self.P = (I - K @ H) @ self.P

        return float(self.x[0, 0])


# ============================================================
#  DRAWING THE ANGLES ON THE IMAGE
# ============================================================

def draw_finger_angles(image, angles, origin=(10, 30)):
    """Overlays joint flexion angles as text on an image, in place.

    Args:
        image: BGR image (numpy array) to draw on; mutated in place.
        angles: Mapping of joint name to angle in degrees. Only keys
            present in JOINT_ORDER are drawn, in that order.
        origin: (x, y) pixel coordinates for the first line of text.
    """
    x, y = origin
    dy = 20

    cv2.putText(image, "Joint Flex Angles (deg):", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    y += dy

    for key in JOINT_ORDER:
        if key in angles:
            txt = f"{key}: {angles[key]:5.1f}"
            cv2.putText(image, txt, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            y += dy


# ============================================================
#  CALIBRATION: FINGER LINK LENGTHS (FLAT HAND)
# ============================================================

def compute_link_lengths_from_landmarks(landmarks):
    """Computes per-segment lengths for each finger chain from hand landmarks.

    Args:
        landmarks: MediaPipe hand landmark list (21 points) with x, y, z
            attributes per point.

    Returns:
        dict: Mapping of finger name (from FINGER_CHAINS) to a list of
        Euclidean segment lengths between consecutive landmarks in that
        finger's chain.
    """
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
    finger_lengths = {}

    for finger, chain in FINGER_CHAINS.items():
        seg_lengths = []
        for a, b in zip(chain[:-1], chain[1:]):
            seg_lengths.append(np.linalg.norm(pts[a] - pts[b]))
        finger_lengths[finger] = seg_lengths

    return finger_lengths


def calibrate_finger_lengths(cap, detector, target_samples=50):
    """Interactively calibrates finger link lengths from a flat right hand.

    Displays the webcam feed and waits for the user to press 'c' to begin
    sampling, then collects finger segment lengths (via
    compute_link_lengths_from_landmarks) over successive frames until
    target_samples are gathered, and averages them. Press 'q' or Esc to
    abort.

    Args:
        cap: Opened cv2.VideoCapture instance to read frames from.
        detector: MediaPipe HandLandmarker (VIDEO mode) used for detection.
        target_samples: Number of samples to collect before finishing.

    Returns:
        dict | None: Mapping of finger name to a numpy array of averaged
        segment lengths, or None if the user aborted calibration.
    """
    print("\n=== CALIBRATION MODE ===")
    print("Hold your RIGHT hand flat, fingers extended, facing the camera.")
    print("Press 'c' to start capturing calibration samples.")
    print("Press 'q' to abort.\n")

    collecting = False
    samples = {finger: [] for finger in FINGER_CHAINS.keys()}

    ts = MonotonicTimestampMS()

    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            print("Calibration: frame read error.")
            continue

        frame_bgr = cv2.flip(frame_bgr, 1)

        # Run mediapipe on RGB
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = rgb_frame_to_mp_image(rgb)
        result = detector.detect_for_video(mp_image, ts.next())

        # Draw landmarks on RGB if available, then convert back to BGR for display
        if result.hand_landmarks and result.handedness:
            chosen_idx = 0
            for i in range(len(result.handedness)):
                if result.handedness[i][0].category_name == "Right":
                    chosen_idx = i
                    break

            hand_landmarks = result.hand_landmarks[chosen_idx]
            draw_hand_landmarks_on_image(rgb, hand_landmarks)

            if collecting:
                finger_lengths = compute_link_lengths_from_landmarks(hand_landmarks)
                for finger, segs in finger_lengths.items():
                    samples[finger].append(segs)

        # Convert annotated RGB -> BGR ONCE (after any landmark drawing)
        display = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        # Compute sample count (safe even before collecting)
        n = len(next(iter(samples.values()))) if samples else 0

        # ---- UI overlays (draw LAST so nothing overwrites them) ----
        if not collecting:
            cv2.putText(
                display,
                "CALIBRATION: Hold hand flat, press 'c' to start",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )
        else:
            cv2.putText(
                display,
                "CALIBRATION: Capturing lengths...",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
            cv2.putText(
                display,
                f"Samples: {n}/{target_samples}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        cv2.imshow("Calibration - Hold Hand Flat", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c') and not collecting:
            print("Calibration: started sampling...")
            collecting = True

        if key == ord('q') or key == 27:
            print("Calibration aborted by user.")
            return None

        if collecting and n >= target_samples:
            print("Calibration: enough samples collected.")
            break

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
    """Computes joint flexion angles refined with a 2-link IK approximation.

    Starts from the geometric angle estimate (compute_hand_joint_angles_geometric)
    and, when calibrated finger link lengths are available, refines the PIP
    and DIP flexion angles for index/middle/ring/pinky fingers using a
    2-link planar IK solve based on wrist-to-fingertip distance.

    Args:
        landmarks: MediaPipe hand landmark list (21 points) with x, y, z
            attributes per point.
        finger_link_lengths: Mapping of finger name to segment lengths as
            returned by calibrate_finger_lengths, or None to skip the IK
            refinement and return the plain geometric angles.

    Returns:
        dict: Mapping of joint name to flexion angle in degrees, with PIP
        and DIP entries for index/middle/ring/pinky replaced by the
        IK-refined values when finger_link_lengths is provided.
    """
    angles = compute_hand_joint_angles_geometric(landmarks)
    if finger_link_lengths is None:
        return angles

    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])

    for finger in ["index", "middle", "ring", "pinky"]:
        if finger not in finger_link_lengths:
            continue

        chain = FINGER_CHAINS[finger]
        base_idx = chain[0]
        tip_idx = chain[-1]

        B = pts[base_idx]
        T = pts[tip_idx]

        L1, L2, L3 = finger_link_lengths[finger]
        Lp = max(L1, 1e-6)
        Ld = max(L2 + L3, 1e-6)

        d = np.linalg.norm(T - B)
        d = float(max(1e-6, min(d, Lp + Ld - 1e-6)))

        cos_q2 = (d * d - Lp * Lp - Ld * Ld) / (2.0 * Lp * Ld)
        cos_q2 = max(-1.0, min(1.0, cos_q2))
        q2 = math.acos(cos_q2)
        q2_deg = math.degrees(q2)

        pip_flex = q2_deg * 0.6
        dip_flex = q2_deg * 0.4

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
    """Runs the live webcam-to-ARTUS teleoperation loop.

    Finds a working camera, connects to the ARTUS Lite hand, runs a
    one-time finger-length calibration, then continuously tracks a hand,
    computes IK-refined and Kalman-smoothed joint angles, maps them to
    ARTUS command space, and streams them to the hand while displaying an
    annotated video window. Exits when 'q' or Esc is pressed.
    """
    cam_index = find_working_camera()

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print("✗ Failed to open camera.")
        return

    config = ArtusConfig()
    artus = config.get_api()

    # ArtusAPI_V2 connects automatically on construction; wake the hand
    # before sending joint commands.
    artus.wake_up()

    # Real ARTUS joint names, in the same order as JOINT_ORDER above, used
    # to build the name-keyed dict ArtusAPI_V2.set_joint_angles expects.
    joint_names = artus._robot_handler.robot.joint_names

    detector = create_hand_landmarker()

    finger_link_lengths = calibrate_finger_lengths(cap, detector, target_samples=50)

    kalman_filters = {
        name: AngleKalmanFilter(process_var=5.0, measurement_var=150.0)
        for name in JOINTS.keys()
    }

    last_print = 0.0
    print_interval = 0.5
    prev_time = time.time()

    # Strictly monotonic timestamps for MediaPipe Tasks VIDEO mode
    ts = MonotonicTimestampMS()

    tracked_wrist = None
    hand_lost_frames = 0
    max_hand_lost_frames = 10
    max_reacquire_distance = 0.30

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame read error.")
            continue

        now = time.time()
        dt = now - prev_time
        prev_time = now
        dt = max(1e-3, min(dt, 0.1))

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = rgb_frame_to_mp_image(rgb)

        result = detector.detect_for_video(mp_image, ts.next())

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

            raw_angles = compute_hand_joint_angles_with_ik(
                hand_landmarks,
                finger_link_lengths
            )

            smoothed_angles = {}
            for name, val in raw_angles.items():
                smoothed = kalman_filters[name].update(val, dt)
                smoothed_angles[name] = smoothed

            angles_mapped = [
                map_angle_for_artus(joint_name, smoothed_angles.get(joint_name, 0.0))
                for joint_name in JOINT_ORDER
            ]

            joint_angles = angles_mapped

            hand_joints = {
                joint_names[i]: {
                    'target_angle': angle,
                    'target_velocity': artus._robot_handler.robot.default_velocity,
                }
                for i, angle in enumerate(joint_angles)
            }

            artus.set_joint_angles(hand_joints)

            if now - last_print > print_interval:
                print(f"\n{handedness_label} Hand Joint Flex Angles (IK + Kalman):")
                for name, val in smoothed_angles.items():
                    print(f"  {name:10s}: {val:5.1f}")

                print("Mapped joint angles (Artus order):")
                print("JOINT_ORDER:", JOINT_ORDER)
                print("angles_mapped:", joint_angles)

                last_print = now

            mapped_angle_dict = {
                joint_name: float(angle)
                for joint_name, angle in zip(JOINT_ORDER, joint_angles)
            }

            draw_finger_angles(frame, mapped_angle_dict)

        cv2.imshow("Hand Tracking with IK + Kalman", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()