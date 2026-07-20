"""Computes absolute fingertip poses from relative per-node glove joint data."""

import numpy as np

import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
print("PROJECT_ROOT: ", PROJECT_ROOT)

sys.path.append(PROJECT_ROOT)
from Isaac_Sim_Work.Hand_Simulation.ArtusLite_2025.logs.mapping import IndexFingerMapper


from scipy.spatial.transform import Rotation as R

import transforms3d.euler
import transforms3d.quaternions
import math

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
        """Initializes the transformer with the finger node chains to use.

        Args:
            chains: Mapping of finger name to the ordered list of node ids
                that form the kinematic chain for that finger, from the
                wrist/root outward to the fingertip. Defaults to
                DEFAULT_CHAINS when not provided.
        """
        self.chains = chains or self.DEFAULT_CHAINS
        
        self.mapper = IndexFingerMapper()
        # now map any glove read
        # p_test, q_test = mapper.map(p_gf, q_gf)
        # print("Robot predicts:", p_test, q_test)

        # self.R = [[-0.0809,  0.9893,  0.1218],
        # [-0.9956, -0.0743, -0.0573],
        # [-0.0476, -0.1259,  0.9909]]

        # self.t = [-0.0683,  0.0240, -0.2912]

        # self.q_R = self.rot_to_quat(self.R)

    # def rot_to_quat(self, R):
    #     # ensure R is a NumPy array
    #     R = np.asarray(R, dtype=float)
    #     # returns [qx, qy, qz, qw] from a 3×3 R
    #     t = R[0,0] + R[1,1] + R[2,2]
    #     if t > 0:
    #         S = np.sqrt(t+1.0)*2
    #         qw = 0.25*S
    #         qx = (R[2,1] - R[1,2]) / S
    #         qy = (R[0,2] - R[2,0]) / S
    #         qz = (R[1,0] - R[0,1]) / S
    #     # … handle other cases (see a standard matrix→quat snippet) …
    #     return np.array([qx, qy, qz, qw])



    @staticmethod
    def quat_mul(q: np.ndarray, r: np.ndarray) -> np.ndarray:
        """Multiplies two quaternions in [x, y, z, w] order.

        Args:
            q: Left-hand quaternion as [x, y, z, w].
            r: Right-hand quaternion as [x, y, z, w].

        Returns:
            The Hamilton product q * r as a [x, y, z, w] quaternion.
        """
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
        """Computes the conjugate of a quaternion in [x, y, z, w] order.

        Args:
            q: Quaternion as [x, y, z, w].

        Returns:
            The conjugate quaternion [-x, -y, -z, w].
        """
        return np.array([-q[0], -q[1], -q[2], q[3]])

    @classmethod
    def rotate_vec(cls, v: np.ndarray, q: np.ndarray) -> np.ndarray:
        """Rotates a 3D vector by a quaternion.

        Args:
            v: The vector to rotate, as (x, y, z).
            q: Rotation quaternion as [x, y, z, w].

        Returns:
            The rotated vector as an (x, y, z) numpy array.
        """
        v_q = np.array([v[0], v[1], v[2], 0.0])
        return cls.quat_mul(
            cls.quat_mul(q, v_q),
            cls.quat_conj(q)
        )[:3]

    def compose(self,
                p1: np.ndarray, q1: np.ndarray,
                p2: np.ndarray, q2: np.ndarray
               ) -> tuple[np.ndarray, np.ndarray]:
        """Composes a parent pose with a child pose expressed in its frame.

        Args:
            p1: Parent position as (x, y, z).
            q1: Parent orientation quaternion as [x, y, z, w].
            p2: Child position, relative to the parent frame, as (x, y, z).
            q2: Child orientation quaternion, relative to the parent frame,
                as [x, y, z, w].

        Returns:
            A tuple of (p_abs, q_abs): the child's position and orientation
            expressed in the parent's reference frame.
        """
        p_abs = p1 + self.rotate_vec(p2, q1)
        q_abs = self.quat_mul(q1, q2)
        return p_abs, q_abs

    def compute_absolute_poses(
        self,
        decoded: dict[int, tuple[tuple[float,float,float], tuple[float,float,float,float]]]
    ) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        """Chains per-node relative poses into an absolute pose per finger.

        Walks each finger's node chain (see self.chains), composing each
        node's relative position/rotation onto the accumulated parent pose,
        starting from a fixed base orientation used to match the Isaac Sim
        frame convention.

        Args:
            decoded: Mapping of node_id to ((x, y, z), (w, qx, qy, qz)),
                where the tuple holds that node's position and rotation
                relative to its parent node.

        Returns:
            A dict mapping finger name to a two-element list
            [pos_abs, quat_abs], where pos_abs is the fingertip position as
            an (x, y, z) numpy array and quat_abs is the orientation as a
            [w, x, y, z] numpy array.
        """
        result = {}
        for finger, node_ids in self.chains.items():
            p_abs = np.zeros(3)
            q_abs = np.array([0.0, 0.0, 0.0, 1.0])  # identity quat in [x,y,z,w]
            q_base = np.array([ 0.7412965, 0, 0, 0.6711777 ]) # rotate to match Isaac Sim
            # q_abs = self.quat_mul(q_base, q_abs)  # rotate to match Isaac Sim
            q_abs = np.array([ 0.7412965, 0, 0, 0.6711777 ])
            for nid in node_ids:
                p_rel = np.array(decoded[nid][0])
                w, x, y, z = decoded[nid][1]        # unpack your (w,x,y,z)
                q_rel = np.array([x, y, z, w])      # reorder to [x,y,z,w]
                p_abs, q_abs = self.compose(p_abs, q_abs, p_rel, q_rel)
            # reorder quat to [w, x, y, z]
            q_abs = np.array([q_abs[3], q_abs[0], q_abs[1], q_abs[2]])
            # print("Q_ABS Size", len(q_abs))
            result[finger] = [p_abs, q_abs]
            # chnage sign of y coordinate to match Isaac Sim
            # print(result[finger][0])
            # result[finger][0][1] = -result[finger][0][1]
            # add z height
            result[finger][0][2] = result[finger][0][2] + 0.2
            # swap x and y coordinates to match Isaac Sim
            # result[finger][0][0], result[finger][0][1] = result[finger][0][1], result[finger][0][0]
            # map the result
            # result[finger] = self.mapper.map(p_glove=p_abs,
            #                                  q_glove=q_abs)
        return result
    
    def _euler_to_quaternion(self, roll_degrees, pitch_degrees, yaw_degrees):
        """Converts Euler angles in degrees to a unit quaternion.

        Assumes ZYX rotation order.

        Args:
            roll_degrees: Roll angle in degrees.
            pitch_degrees: Pitch angle in degrees.
            yaw_degrees: Yaw angle in degrees.

        Returns:
            The equivalent orientation as a (w, x, y, z) quaternion.
        """
        # Convert degrees to radians
        roll_rad = math.radians(roll_degrees)
        pitch_rad = math.radians(pitch_degrees)
        yaw_rad = math.radians(yaw_degrees)

        # Get quaternion in (w, x, y, z) order
        quat = transforms3d.euler.euler2quat(roll_rad, pitch_rad, yaw_rad, axes='syzx')
        # if (pitch_degrees != 0):
        #     quat = transforms3d.euler.euler2quat(pitch_rad, roll_rad, yaw_rad, axes='szyx')
        # if (yaw_degrees != 0):
        #     quat = transforms3d.euler.euler2quat(yaw_rad, roll_rad, pitch_rad, axes='sxyz')
       
        # print(quat)

        # Normalize the quaternion (although euler2quat usually returns a normalized one)
        # quat = transforms3d.quaternions.qnorm(quat) 

        return quat
    




# # example usage
# def main():
#     # somewhere in your code, after parsing…
#     decoded = fingertip_data.receive_fingerTip_data()

#     transformer = FingerPoseTransformer()
#     absolute_poses = transformer.compute_absolute_poses(decoded)

#     # absolute_poses['thumb'] → (np.array([x,y,z]), np.array([qx,qy,qz,qw]))



# if __name__ == "__main__":
#     main()