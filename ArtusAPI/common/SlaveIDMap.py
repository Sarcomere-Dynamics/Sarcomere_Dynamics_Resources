"""
Maps logical robot variant (robot_type + hand) to the uint8 value exposed in the
``slave_id_reg`` Modbus register. Firmware must report the same values.

``artus_scorpion`` uses a single identity; left/right hand_type both normalize to
the same key for expected ID and resync returns ('artus_scorpion', 'left').
"""

from __future__ import annotations

SLAVE_ID_BY_ROBOT_HAND: dict[tuple[str, str], int] = {
    ("artus_lite", "left"): 1,
    ("artus_lite", "right"): 2,
    ("artus_lite_plus", "left"): 3,
    ("artus_lite_plus", "right"): 4,
    ("artus_talos", "left"): 5,
    ("artus_talos", "right"): 6,
    ("artus_scorpion", "left"): 7,
    ("artus_dex", "left"): 8,
    ("artus_dex", "right"): 9,
}

SLAVE_ID_TO_ROBOT_HAND: dict[int, tuple[str, str]] = {
    v: k for k, v in SLAVE_ID_BY_ROBOT_HAND.items()
}


def normalize_robot_hand_key(robot_type: str, hand_type: str) -> tuple[str, str]:
    if robot_type == "artus_scorpion":
        return (robot_type, "left")
    return (robot_type, hand_type)


def expected_slave_id(robot_type: str, hand_type: str) -> int:
    key = normalize_robot_hand_key(robot_type, hand_type)
    return SLAVE_ID_BY_ROBOT_HAND[key]


def robot_hand_from_slave_id(slave_id: int) -> tuple[str, str] | None:
    return SLAVE_ID_TO_ROBOT_HAND.get(int(slave_id) & 0xFF)
