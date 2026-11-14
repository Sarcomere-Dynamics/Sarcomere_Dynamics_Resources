"""Codes reported by the master's status registers (700-812) and the motor boards.

Mirrors the firmware's single source of truth, ``protocols/*.yaml`` in the
artus firmware workspace (``host.yaml``: master_fault, command_result,
motor_flags; ``can.yaml``: axis_state, procedure_result; ``slave_errors.yaml``:
error_report). Hand-copied until that folder generates this module -- change a
value there first, then here. Member names match the firmware's C identifiers
without their prefix.
"""

from __future__ import annotations

from enum import IntEnum, IntFlag

# ---------------------------------------------------------------------------
# Master status (host registers 700-704)
# ---------------------------------------------------------------------------

MASTER_FAULT_MOTOR_NONE = 0xFF
"""Fault record motor index meaning "no single motor"."""


class MasterFault(IntEnum):
    """Why the master entered ACTUATOR_ERROR (register 700, low byte)."""

    NONE = 0
    SLAVE_ERROR = 1
    LL_CAL_FAILED = 2
    STROKE_CAL_FAILED = 3
    BAD_ARGUMENT = 4
    ESTOP = 5
    COMM_LOST = 6


MASTER_FAULT_MEANING = {
    MasterFault.NONE: "No fault recorded.",
    MasterFault.SLAVE_ERROR: "A motor board reported an error; see the motor's error_report.",
    MasterFault.LL_CAL_FAILED: (
        "Low-level motor calibration failed or timed out; procedure_result says why "
        "(BUSY = never finished / no reply)."
    ),
    MasterFault.STROKE_CAL_FAILED: (
        "Stroke calibration (end stops / zeroing) failed on the motor: search timed out "
        "or overtravelled, a mode change or re-zero was never confirmed, or the motor "
        "board's own search found no end stop."
    ),
    MasterFault.BAD_ARGUMENT: "A command argument was out of range (e.g. CALIBRATE with an unknown joint).",
    MasterFault.ESTOP: "The host sent ESTOP.",
    MasterFault.COMM_LOST: "The motor stopped answering on CAN for over 1 s.",
}


class CommandResult(IntEnum):
    """What the master did with the last host command (register 704, low byte)."""

    NONE = 0
    ACCEPTED = 1
    REJECTED_STATE = 2
    REJECTED_ERROR = 3


COMMAND_RESULT_MEANING = {
    CommandResult.NONE: "No command handled since boot.",
    CommandResult.ACCEPTED: "Accepted: the command started its transition.",
    CommandResult.REJECTED_STATE: "Ignored: not valid in the current state, or not handled by this firmware.",
    CommandResult.REJECTED_ERROR: "Ignored: the hand is in ERROR. Send clear_errors() first.",
}


class MotorFlags(IntFlag):
    """Master-side per-motor flags (registers 790+)."""

    LL_FAILED = 0x0001
    STROKE_FAILED = 0x0002
    COMM_LOST = 0x0004
    NO_RESPONSE = 0x0008


MOTOR_FLAG_MEANING = {
    MotorFlags.LL_FAILED: "Low-level calibration failed or timed out.",
    MotorFlags.STROKE_FAILED: "A stroke-calibration step failed on this motor.",
    MotorFlags.COMM_LOST: "Stopped answering on CAN (latched until clear_errors()).",
    MotorFlags.NO_RESPONSE: "Never answered since the master booted (missing, unpowered, wrong CAN ID or not flashed).",
}

HOST_COMMAND_NAMES = {
    0x0B: "START",
    0x0D: "CALIBRATE",
    0x0F: "SHUT_DOWN",
    0x11: "UPLOAD",
    0x13: "RESETL",
    0x15: "SET_ZERO",
    0x17: "STOP_FEEDBACK_ACTS",
    0x18: "ESTOP",
    0x1A: "CLEAR_ERRORS",
    0x28: "REQUEST",
    0x30: "UPLOAD_CHUNKS",
    0x32: "FINISH_CHUNKS_COMMAND",
    0x35: "SOFT_RESET",
    0x38: "HARD_CLOSE",
    0x44: "PARAMS",
    0x46: "SDWIPE",
    0x66: "TARGETPOS",
    0x68: "UPDATE",
    0xC8: "SAVEGRASP",
    0xD2: "RETURNGRASP",
    0xE0: "EXECUTEGRASP",
}

# ---------------------------------------------------------------------------
# Motor board (registers 710+ / 760+)
# ---------------------------------------------------------------------------


class AxisState(IntEnum):
    """Motor board axis state (register 760+ high byte; 600+ per joint)."""

    MODE_UNDEF = 0
    MODE_IDLE = 1
    MODE_CALIBRATE_RESISTANCE = 4
    MODE_CALIBRATE_POSITION_DYN = 7
    MODE_CLOSE_LOOP = 8
    MODE_FIND_END_STOP = 11
    MODE_CALIBRATE_POSITION = 17
    MODE_ERROR = 18
    MODE_FREE = 19


class ProcedureResult(IntEnum):
    """Outcome of a motor board's last procedure (register 760+ low byte)."""

    SUCCESS = 0
    BUSY = 1
    ESTOP = 2
    DRV_CONFIG_UNVERIFIED = 3
    CALLI_ELEC_PHASE_NONLINEAR = 4
    CALLI_ELEC_PHASE_UNEQUAL = 5
    CALLI_POS_NO_MOTION = 6
    ENDPOINT_SEARCH_NO_ENDPOINT_FOUND = 7
    DRV_ERROR = 8


PROCEDURE_RESULT_MEANING = {
    ProcedureResult.SUCCESS: "Last procedure succeeded.",
    ProcedureResult.BUSY: "Procedure running (or never finished).",
    ProcedureResult.ESTOP: "Stopped by ESTOP.",
    ProcedureResult.DRV_CONFIG_UNVERIFIED: "Gate driver configuration did not read back at boot.",
    ProcedureResult.CALLI_ELEC_PHASE_NONLINEAR: "Electrical calibration: current not linear with voltage (phase connection / current sense).",
    ProcedureResult.CALLI_ELEC_PHASE_UNEQUAL: "Electrical calibration: phase resistances differ by over 25% (winding / connection).",
    ProcedureResult.CALLI_POS_NO_MOTION: "Position calibration: no free motion or encoder not tracking (blocked motor / magnet / encoder).",
    ProcedureResult.ENDPOINT_SEARCH_NO_ENDPOINT_FOUND: "Motor board's end-stop search found no stop.",
    ProcedureResult.DRV_ERROR: "Gate driver raised a fault.",
}

DRV_FAULT = 0x00000020
"""error_report flag: bits 16-31 then carry gate-driver status, not flags."""


class SlaveError(IntFlag):
    """Motor board error_report flags (registers 710+; 500+ per joint)."""

    INITIALIZING = 0x00000001
    SYSTEM_LEVEL = 0x00000002
    TIMING_ERROR = 0x00000004
    MISSING_ESTIMATE = 0x00000008
    BAD_CONFIG = 0x00000010
    DRV_FAULT = 0x00000020
    MISSING_INPUT = 0x00000040
    DC_BUS_OVER_VOLTAGE = 0x00000100
    DC_BUS_UNDER_VOLTAGE = 0x00000200
    DC_BUS_OVER_CURRENT = 0x00000400
    DC_BUS_OVER_REGEN_CURRENT = 0x00000800
    CURRENT_LIMIT_VIOLATION = 0x00001000
    MOTOR_OVER_TEMP = 0x00002000
    INVERTER_OVER_TEMP = 0x00004000
    VELOCITY_LIMIT_VIOLATION = 0x00008000
    POSITION_LIMIT_VIOLATION = 0x00010000
    WATCHDOG_TIMER_EXPIRED = 0x01000000
    ESTOP_REQUESTED = 0x02000000
    SPINOUT_DETECTED = 0x04000000
    BRAKE_RESISTOR_DISARMED = 0x08000000
    THERMISTOR_DISCONNECTED = 0x10000000
    CALIBRATION_ERROR = 0x40000000


SLAVE_ERROR_MEANING = {
    SlaveError.MISSING_ESTIMATE: "Closed loop requested before the motor was calibrated.",
    SlaveError.DRV_FAULT: "Gate driver fault; bits 16-31 are its status registers.",
    SlaveError.DC_BUS_OVER_VOLTAGE: "Supply voltage above the limit.",
    SlaveError.DC_BUS_UNDER_VOLTAGE: "Supply voltage below the limit.",
    SlaveError.DC_BUS_OVER_CURRENT: "Estimated bus current above the limit (e.g. stalled motor).",
    SlaveError.DC_BUS_OVER_REGEN_CURRENT: "Too much current fed back into the supply (back-driven / braking).",
    SlaveError.CURRENT_LIMIT_VIOLATION: "Phase current above tolerance x motor maximum.",
    SlaveError.ESTOP_REQUESTED: "ESTOP received.",
    SlaveError.CALIBRATION_ERROR: "A calibration or gate-driver setup failed; see procedure_result.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def enum_name(enum_cls: type[IntEnum], value: int) -> str:
    """Name of ``value`` in ``enum_cls``, or ``UNKNOWN(<value>)``."""
    try:
        return enum_cls(value).name
    except ValueError:
        return f"UNKNOWN({value})"


def command_name(code: int) -> str:
    """Host command name for an opcode, or ``UNKNOWN(0x..)``."""
    return HOST_COMMAND_NAMES.get(code, f"UNKNOWN(0x{code:02X})")


def flag_names(flags: int) -> list[str]:
    """Names of the MotorFlags bits set in ``flags`` (unknown bits as hex)."""
    known = 0
    names = []
    for f in MotorFlags:
        known |= f.value
        if flags & f.value:
            names.append(f.name)
    if flags & ~known:
        names.append(f"0x{flags & ~known:04X}")
    return names


def decode_slave_error(word: int) -> dict:
    """Splits a motor board error_report into flag names and gate-driver status.

    With DRV_FAULT set, only bits 0-15 are flags and bits 16-31 are the gate
    driver's status registers (layout per chip, ``protocols/slave_errors.yaml``).

    Args:
        word: A raw motor error_report (registers 710+). Not a Dex joint word,
            which may also carry the master's calibration bits 17-22.

    Returns:
        ``{"flags": [names], "drv_fault_status": int | None}``.
    """
    if word & DRV_FAULT:
        flag_bits, drv_status = word & 0xFFFF, (word >> 16) & 0xFFFF
    else:
        flag_bits, drv_status = word, None
    known = 0
    names = []
    for f in SlaveError:
        known |= f.value
        if flag_bits & f.value:
            names.append(f.name)
    if flag_bits & ~known:
        names.append(f"0x{flag_bits & ~known:08X}")
    return {"flags": names, "drv_fault_status": drv_status}
