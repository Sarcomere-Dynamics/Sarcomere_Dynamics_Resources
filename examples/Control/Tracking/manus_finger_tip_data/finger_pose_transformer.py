import numpy as np

class FingerPoseTransformer:
    """
    Compute absolute fingertip poses from relative joint data.

    - Input: a dict mapping node_id -> (pos_tuple, quat_tuple)
      where pos_tuple is (x,y,z) and quat_tuple is (w,qx,qy,qz).
    - Output: a dict mapping finger names ('thumb', 'index', etc.)
      to their absolute (position: np.ndarray, quaternion: np.ndarray in [x,y,z,w]).
    """
    # DEFAULT_CHAINS = {
    #     'thumb':  [1,  2,  3],
    #     'index':  [6,  7,  8],
    #     'middle': [11, 12, 13],
    #     'ring':   [16, 17, 18],
    #     'pinky':  [21, 22, 23],
    # }
    
    DEFAULT_CHAINS = {
        'thumb':  [0, 1,  2,  3, 4],
        'index':  [5, 6,  7,  8, 9],
        'middle': [10, 11, 12, 13, 14],
        'ring':   [15, 16, 17, 18, 19],
        'pinky':  [20, 21, 22, 23, 24],
    }



    def __init__(self, chains: dict[str, list[int]] = None):
        self.chains = chains or self.DEFAULT_CHAINS

        self.R = [[-0.0809,  0.9893,  0.1218],
        [-0.9956, -0.0743, -0.0573],
        [-0.0476, -0.1259,  0.9909]]

        self.t = [-0.0683,  0.0240, -0.2912]

        self.q_R = self.rot_to_quat(self.R)

    def rot_to_quat(self, R):
        # ensure R is a NumPy array
        R = np.asarray(R, dtype=float)
        # returns [qx, qy, qz, qw] from a 3×3 R
        t = R[0,0] + R[1,1] + R[2,2]
        if t > 0:
            S = np.sqrt(t+1.0)*2
            qw = 0.25*S
            qx = (R[2,1] - R[1,2]) / S
            qy = (R[0,2] - R[2,0]) / S
            qz = (R[1,0] - R[0,1]) / S
        # … handle other cases (see a standard matrix→quat snippet) …
        return np.array([qx, qy, qz, qw])

        
# e.g. q_R ≈ [-0.0253, 0.0625, -0.7325, 0.6774]  (in [x,y,z,w])



    @staticmethod
    def quat_mul(q: np.ndarray, r: np.ndarray) -> np.ndarray:
        x1, y1, z1, w1 = q
        x2, y2, z2, w2 = r
        return np.array([
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2,
            w1*w2 - x1*x2 - y1*y2 - z1*z2
        ])

    @staticmethod
    def quat_conj(q: np.ndarray) -> np.ndarray:
        return np.array([-q[0], -q[1], -q[2], q[3]])

    @classmethod
    def rotate_vec(cls, v: np.ndarray, q: np.ndarray) -> np.ndarray:
        v_q = np.array([v[0], v[1], v[2], 0.0])
        return cls.quat_mul(
            cls.quat_mul(q, v_q),
            cls.quat_conj(q)
        )[:3]

    def compose(self,
                p1: np.ndarray, q1: np.ndarray,
                p2: np.ndarray, q2: np.ndarray
               ) -> tuple[np.ndarray, np.ndarray]:
        p_abs = p1 + self.rotate_vec(p2, q1)
        q_abs = self.quat_mul(q1, q2)
        return p_abs, q_abs

    def compute_absolute_poses(
        self,
        decoded: dict[int, tuple[tuple[float,float,float], tuple[float,float,float,float]]]
    ) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        """
        decoded: { node_id: ((x,y,z), (w,qx,qy,qz)), … }
        returns: { finger_name: (pos_abs, quat_abs in [x,y,z,w]), … }
        """
        result = {}
        for finger, node_ids in self.chains.items():
            p_abs = np.zeros(3)
            q_abs = np.array([0.0, 0.0, 0.0, 1.0])  # identity quat in [x,y,z,w]
            # q_abs = np.array([0.0, 0.707, 0.0, 0.707])  # identity quat in [x,y,z,w]
            # q_abs = self.quat_mul(q_abs,[-0.707, 0, 0.0, 0.707])  # rotate to match Isaac Sim
            for nid in node_ids:
                p_rel = np.array(decoded[nid][0])
                w, x, y, z = decoded[nid][1]        # unpack your (w,x,y,z)
                q_rel = np.array([x, y, z, w])      # reorder to [x,y,z,w]
                p_abs, q_abs = self.compose(p_abs, q_abs, p_rel, q_rel)
            result[finger] = [p_abs, q_abs]
            # chnage sign of y coordinate to match Isaac Sim
            # print(result[finger][0])
            # result[finger][0][1] = -result[finger][0][1]
            # add z height
            result[finger][0][2] = result[finger][0][2] + 0.4
            # swap x and y coordinates to match Isaac Sim
            result[finger][0][0], result[finger][0][1] = result[finger][0][1], result[finger][0][0]
        return result




# # example usage
# def main():
#     # somewhere in your code, after parsing…
#     decoded = fingertip_data.receive_fingerTip_data()

#     transformer = FingerPoseTransformer()
#     absolute_poses = transformer.compute_absolute_poses(decoded)

#     # absolute_poses['thumb'] → (np.array([x,y,z]), np.array([qx,qy,qz,qw]))



# if __name__ == "__main__":
#     main()