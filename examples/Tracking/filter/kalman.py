
import numpy as np
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
