# ============================================================
#  ArtusMediaPipe class encapsulating MediaPipe hand tracking,
#  calibration, and Artus Lite joint mapping utilities
# ============================================================
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import math
import logging

class ArtusMediaPipe:
    def __init__(self,
                 max_num_hands=2,
                 model_complexity=1,
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5,
                 logger=None
                 ):

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self.logger.info("Initializing ArtusMediaPipe")
        # self.base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
        # options = vision.HandLandmarkerOptions(base_options=self.base_options,
        #                                     num_hands=1)
        # self.detector = vision.HandLandmarker.create_from_options(options)


        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        # Landmark index triplets for angle computation (geometric method)
        self.JOINTS = {
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

        self.JOINT_ORDER = [
            "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_dip",
            "index_mcp", "index_pip", "index_dip",
            "middle_mcp", "middle_pip", "middle_dip",
            "ring_mcp", "ring_pip", "ring_dip",
            "pinky_mcp", "pinky_pip", "pinky_dip",
        ]

        # Finger chains for link-length calibration (landmark indices)
        self.FINGER_CHAINS = {
            "thumb":  [1, 2, 3, 4],     # CMC -> MCP -> IP -> TIP
            "index":  [5, 6, 7, 8],     # MCP -> PIP -> DIP -> TIP
            "middle": [9, 10, 11, 12],
            "ring":   [13, 14, 15, 16],
            "pinky":  [17, 18, 19, 20],
        }

    def find_working_camera(self, max_tested=10):
        """
        Scans camera indices from 0 up to max_tested-1.
        Returns the first index that opens successfully and produces frames.
        """
        self.logger.info("Scanning for available camera...")
        for i in range(max_tested):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    cap.release()
                    self.logger.info(f"✓ Found working camera at index {i}")
                    return i
            cap.release()
        raise RuntimeError("✗ No working camera found.")

    def map_range(self, value, in_min, in_max, out_min, out_max, clamp=True):
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

    def map_angle_for_artus(self, joint_name, flex_deg):
        """
        Map flexion angle (0–180°, where 0 = extended, 180 = flexed) into
        Artus Lite joint command space with per-joint ROM:

            • thumb_cmc        →  -45°   to  +45°
            • finger MCPs     →  -17°   to  +17°
            • all other joints →   0°    to   90°

        Returns an integer command value.
        """

        flex = max(0.0, min(180.0, float(flex_deg)))

        if joint_name == "thumb_cmc":
            cmd = self.map_range(flex, 120, 140, -45, 45, True)
        elif joint_name in {"index_mcp", "middle_mcp", "ring_mcp", "pinky_mcp"}:
            cmd = self.map_range(flex, 9, 20, -17, 17, True)
        else:
            if flex >= 90.0:
                flex = 90.0
            cmd = flex
        return int(round(cmd))

    def angle_between_3d(self, p1, p2, p3):
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

    def geometric_to_flex(self, angle_deg):
        """
        Convert geometric angle to flexion angle:
        0° = fully extended, increases with flexion.
        """
        flex = 180.0 - angle_deg
        return max(0, min(180, flex))

    def compute_hand_joint_angles_geometric(self, landmarks):
        """
        Compute flexion angles for all joints from MediaPipe's 3D points,
        using the simple 3-point geometric method.
        """
        pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])

        angles = {}
        for name, (i1, i2, i3) in self.JOINTS.items():
            geometric = self.angle_between_3d(pts[i1], pts[i2], pts[i3])
            angles[name] = self.geometric_to_flex(geometric)
        return angles

    def draw_finger_angles(self, image, angles, origin=(10, 30)):
        x, y = origin
        dy = 20

        cv2.putText(image, "Joint Flex Angles (deg):", (x, y),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        y += dy

        show = self.JOINT_ORDER

        for key in show:
            if key in angles:
                txt = f"{key}: {angles[key]:5.1f}"
                cv2.putText(image, txt, (x, y),
                                 cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
                y += dy

    def compute_link_lengths_from_landmarks(self, landmarks):
        """
        Compute per-finger link lengths (3D) given MediaPipe landmarks.
        Returns dict: { finger_name: [l1, l2, l3] }
        """
        pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
        finger_lengths = {}

        for finger, chain in self.FINGER_CHAINS.items():
            seg_lengths = []
            for a, b in zip(chain[:-1], chain[1:]):
                seg_lengths.append(np.linalg.norm(pts[a] - pts[b]))
            finger_lengths[finger] = seg_lengths  # 3 segments per finger

        return finger_lengths

    def calibrate_finger_lengths(self, cap, target_samples=50):
        """
        Calibration phase:
        - Shows the camera feed
        - User holds hand flat and presses 'c' to start capturing
        - Collects `target_samples` of finger link lengths and averages them
        Returns:
            avg_lengths: { finger: np.array([l1,l2,l3]) } in MediaPipe's normalized 3D units
        """
        self.logger.info("\n=== CALIBRATION MODE ===")
        self.logger.info("Hold your RIGHT hand flat, fingers extended, facing the camera.")
        self.logger.info("Press 'c' to start capturing calibration samples.")
        self.logger.info("Press 'q' to abort.\n")

        collecting = False
        samples = {finger: [] for finger in self.FINGER_CHAINS.keys()}

        while True:
            ret, frame = cap.read()
            if not ret:
                self.logger.info("Calibration: frame read error.")
                continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(rgb)

            if not collecting:
                cv2.putText(frame, "CALIBRATION: Hold hand flat, press 'c' to start",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "CALIBRATION: Capturing lengths...",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            if result.multi_hand_landmarks and result.multi_handedness:
                # Prefer right hand
                chosen_idx = 0
                for i, handedness_info in enumerate(result.multi_handedness):
                    label = handedness_info.classification[0].label
                    if label == "Right":
                        chosen_idx = i
                        break

                hand_lms = result.multi_hand_landmarks[chosen_idx]
                self.mp_drawing.draw_landmarks(
                    frame, hand_lms,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2),
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1)
                )

                if collecting:
                    finger_lengths = self.compute_link_lengths_from_landmarks(hand_lms.landmark)
                    for finger, segs in finger_lengths.items():
                        samples[finger].append(segs)

                    n = len(next(iter(samples.values())))
                    cv2.putText(frame, f"Samples: {n}/{target_samples}",
                                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    if n >= target_samples:
                        self.logger.info("Calibration: enough samples collected.")
                        break

            cv2.imshow("Calibration - Hold Hand Flat", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('c') and not collecting:
                self.logger.info("Calibration: started sampling...")
                collecting = True

            if key == ord('q') or key == 27:
                self.logger.info("Calibration aborted by user.")
                return None

        avg_lengths = {}
        for finger, seg_list in samples.items():
            if len(seg_list) == 0:
                continue
            arr = np.array(seg_list)  # [N, 3]
            avg_lengths[finger] = np.mean(arr, axis=0)

        self.logger.info("\n=== CALIBRATION COMPLETE ===")
        for finger, segs in avg_lengths.items():
            self.logger.info(f"{finger}: {segs}")

        return avg_lengths

    def compute_hand_joint_angles_with_ik(self, landmarks, finger_link_lengths):
        """
        Combines:
          - Geometric joint angles (3-point method) for MCP and thumb joints
          - Simple 2-link IK for PIP/DIP of index/middle/ring/pinky
            using calibrated segment lengths and base->tip distance.

        Returns dict {joint_name: flex_deg}
        """
        angles = self.compute_hand_joint_angles_geometric(landmarks)
        if finger_link_lengths is None:
            return angles

        pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])

        # Fingers we will override PIP/DIP for (keep MCP & thumb as-is)
        for finger in ["index", "middle", "ring", "pinky"]:
            if finger not in finger_link_lengths:
                continue

            chain = self.FINGER_CHAINS[finger]
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


if __name__ == "__main__":
    artus_media_pipe = ArtusMediaPipe()
    artus_media_pipe.find_working_camera()