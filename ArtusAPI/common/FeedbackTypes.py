from enum import Enum

class FeedbackTypes(Enum):
    POSITION = 0
    POSITION_TORQUE = 1
    TORQUE = 2
    TEMPERATURE = 3
    FORCE_SENSOR = 4