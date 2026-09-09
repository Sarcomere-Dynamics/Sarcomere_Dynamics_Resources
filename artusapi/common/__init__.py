"""Common definitions shared across the ArtusAPI package.

Exposes the Modbus register map (:class:`ModbusMap`), actuator/command
enums, and the slave ID lookup helpers used to identify robot variants on
the bus.
"""

from .modbus_map import ActuatorState, CommandType, ModbusMap
from .slave_id_map import (
    SLAVE_ID_BY_ROBOT_HAND,
    SLAVE_ID_TO_ROBOT_HAND,
    expected_slave_id,
    normalize_robot_hand_key,
    robot_hand_from_slave_id,
)

__all__ = [
    "SLAVE_ID_BY_ROBOT_HAND",
    "SLAVE_ID_TO_ROBOT_HAND",
    "ActuatorState",
    "CommandType",
    "ModbusMap",
    "expected_slave_id",
    "normalize_robot_hand_key",
    "robot_hand_from_slave_id",
]
