class ForceSensor:
    """Represents a single fingertip force sensor reading.

    Attributes:
        x: Force reading along the sensor's x-axis.
        y: Force reading along the sensor's y-axis.
        z: Force reading along the sensor's z-axis.
        temperature: Sensor temperature reading.
    """

    def __init__(self):
        """Initializes the force sensor with zeroed readings."""
        self.x = 0
        self.y = 0
        self.z = 0

        self.temperature = 0

    