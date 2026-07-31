"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Lifetime cycle test + full-telemetry logging for the Scorpion hand.

Connection, wake/sleep, calibration, and pose commands are delegated to the
known-good general_example.handle_command() so this script shares one proven
control path with the standard CLI. What it adds on top:

  17 -> Lifetime cycle test: alternates the grasp_example / grasp_open poses
        lifetime_test_count times, logging all hand feedback to CSV throughout.
  18 -> Standalone full-telemetry logging (no motion commanded).

Both use HandTelemetryLogger, which records every feedback getter the API
exposes as raw values (no unit conversion). Everything else falls through to
handle_command() unchanged.
"""
# ------------------------------------------------------------------------------
# ---------------------------- Import Libraries --------------------------------
# ------------------------------------------------------------------------------
import time
import json
import csv
from datetime import datetime
# Add the desired path to the system path
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)
# this script's own directory, so the known-good general_example is importable
# as a sibling module regardless of the examples package name
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# import the configuration file
from examples.config.configuration import ArtusConfig

from ArtusAPI.common import ModbusMap

# Reuse the proven command dispatch + logger setup rather than keeping a second
# copy here — the divergent copy was a failure point during hand connection issues.
from general_example import handle_command, setup_logger

import logging

# ------------------------------------------------------------------------------
# ---------------------------- Life Cycle Testing ------------------------------
# ------------------------------------------------------------------------------

lifetime_test_count = 500 #100k
cycle_dwell_s = 2           # hold time at each pose

# ------------------------------------------------------------------------------
# ------------------------------ Telemetry Logging -----------------------------
# ------------------------------------------------------------------------------

TELEMETRY_INTERVAL_S = 0.5      # seconds between full telemetry samples
TELEMETRY_LOG_DIR = os.path.join(PROJECT_ROOT, 'logs', 'telemetry')
# roll over to a new file before hitting Excel's 1,048,576-row ceiling; a full
# 100k-cycle run at 2 Hz is ~1.2M rows, which would not open in one sheet
TELEMETRY_MAX_ROWS = 500000

# ------------------------------------------------------------------------------
# --------------------------- Motor Error Decoding -----------------------------
# ------------------------------------------------------------------------------
# error_e bitmask mirrored from the firmware's bldcmotor.h. The hand returns each
# joint's error_report as a decimal integer that is really a bitwise-OR of these
# flags, so a single reported number can mean several faults at once. Keep this in
# sync with bldcmotor.h if the firmware's enum changes.
MOTOR_ERROR_FLAGS = {
    0x1:        "INITIALIZING",
    0x2:        "SYSTEM_LEVEL",
    0x4:        "TIMING_ERROR",
    0x8:        "MISSING_ESTIMATE",
    0x10:       "BAD_CONFIG",
    0x20:       "DRV_FAULT",
    0x40:       "MISSING_INPUT",
    0x100:      "DC_BUS_OVER_VOLTAGE",
    0x200:      "DC_BUS_UNDER_VOLTAGE",
    0x400:      "DC_BUS_OVER_CURRENT",
    0x800:      "DC_BUS_OVER_REGEN_CURRENT",
    0x1000:     "CURRENT_LIMIT_VIOLATION",
    0x2000:     "MOTOR_OVER_TEMP",
    0x4000:     "INVERTER_OVER_TEMP",
    0x8000:     "VELOCITY_LIMIT_VIOLATION",
    0x10000:    "POSITION_LIMIT_VIOLATION",
    0x1000000:  "WATCHDOG_TIMER_EXPIRED",
    0x2000000:  "ESTOP_REQUESTED",
    0x4000000:  "SPINOUT_DETECTED",
    0x8000000:  "BRAKE_RESISTOR_DISARMED",
    0x10000000: "THERMISTOR_DISCONNECTED",
    0x40000000: "CALIBRATION_ERROR",
}


def decode_motor_error(code):
    """Decode a decimal motor error_report into (hex_str, [flag names]).

    Returns None if `code` isn't an integer value. A code of 0 gives ("0x0", []).
    Any bits not present in MOTOR_ERROR_FLAGS are reported as UNKNOWN(0x..) rather
    than dropped, so a firmware/header mismatch stays visible instead of silently
    decoding to fewer faults than were actually raised.
    """
    try:
        code = int(code)
    except (TypeError, ValueError):
        return None

    names = []
    covered = 0
    for bit, name in MOTOR_ERROR_FLAGS.items():
        if code & bit:
            names.append(name)
            covered |= bit
    leftover = code & ~covered
    if leftover:
        names.append(f"UNKNOWN({hex(leftover)})")
    return hex(code), names


def format_motor_error(code):
    """One-line 'hex: FLAG_A | FLAG_B' string, or '' for a zero/undecodable code."""
    decoded = decode_motor_error(code)
    if decoded is None:
        return ""
    hex_str, names = decoded
    return f"{hex_str}: {' | '.join(names)}" if names else ""


def print_error_report(report, logger):
    """Pretty-print a joint->error_report dict with plain-text flag names."""
    if not isinstance(report, dict):
        logger.error(f"error report unavailable: {report!r}")
        return
    active = False
    for joint, code in report.items():
        text = format_motor_error(code)
        if text:
            active = True
            print(f"  {joint}: {text}")
    if not active:
        print("  no active errors")

# ------------------------------------------------------------------------------
# -------------------------------- Main Menu -----------------------------------
# ------------------------------------------------------------------------------
def main_menu():
    return input(
    """
    ╔════════════════════════════════════════════════════════════════╗
    ║                          Artus API 2.0                           ║
    ╠════════════════════════════════════════════════════════════════╣
    ║ Command Options:                                                 ║
    ║                                                                  ║
    ║   1 -> Start connection to hand                                  ║
    ║   2 -> Disconnect from hand                                      ║
    ║   3 -> Wakeup hand                                               ║
    ║   4 -> Enter hand sleep mode                                     ║
    ║   5 -> Calibrate                                                 ║
    ║   6 -> Send command from data/hand_poses/grasp_example           ║
    ║   7 -> Get robot state                                           ║
    ║   8 -> Send command from data/hand_poses/grasp_open              ║
    ║   9 -> Get Feedback Position Data                                ║
    ║   10 -> Get Feedback Velocity Data                               ║
    ║   11 -> Get Feedback Torque Data                                 ║
    ║   12 -> Get Fingertip Forces                                     ║
    ║   13 -> Get Voltage                                              ║
    ║   14 -> Get Average Temperature                                  ║
    ║   15 -> Get Joint Temperatures                                   ║
    ║   16 -> Get Error Report                                         ║
    ║   17 -> Perform Lifetime Cycle Test (logs all feedback to CSV)   ║
    ║   18 -> Log All Feedback to CSV                                  ║
    ║                                                                  ║
    ╚════════════════════════════════════════════════════════════════╝
    >> Input Command Code (1-18): """
    )


class HandTelemetryLogger:
    """
    Polls every feedback getter the Artus API exposes and writes one wide CSV row
    per sample: timestamp + elapsed_s + test context, then robot status, voltage,
    average temperature, and per-joint position / velocity / force / temperature /
    error, plus per-finger fingertip forces when the hand has force sensors.
    """

    def __init__(self, artusapi, logger, interval_s=TELEMETRY_INTERVAL_S,
                 title='telemetry', max_rows_per_file=TELEMETRY_MAX_ROWS,
                 print_every=1):
        """
        Parameters:
        :artusapi: connected + awake Artus API instance
        :logger: logger for status messages
        :interval_s: seconds between samples
        :title: goes in the filename
        :max_rows_per_file: rows before rolling to the next part file
        :print_every: console-print every Nth sample (0 = silent)
        """
        self.artusapi = artusapi
        self.logger = logger
        self.interval_s = interval_s
        self.title = title
        self.max_rows_per_file = max_rows_per_file
        self.print_every = print_every

        robot = artusapi._robot_handler.robot
        # column order comes from the robot definition, which is also the order
        # every per-joint getter uses to key its dict — so the header stays stable
        # even if an individual sample comes back short or fails
        self.joint_names = list(robot.joint_names)

        # each entry: (column prefix, zero-arg getter returning a joint->value dict)
        self.joint_feedbacks = [
            ('position',    artusapi.get_joint_angles),
            ('velocity',    artusapi.get_joint_speeds),
            ('force',       artusapi.get_joint_forces),
            ('temperature', artusapi.get_joint_temperatures),
            ('error',       artusapi.get_error_report),
        ]

        # fingertip force sensors are optional; only add columns if present
        force_sensors = getattr(robot, 'force_sensors', None)
        self.force_sensors = list(force_sensors) if force_sensors else []

        self.columns = self._build_columns()

        self.samples = 0
        self.failures = 0
        self.paths = []
        self._rows_in_part = 0
        self._part = 1
        self._file = None
        self._writer = None
        self._start = None
        # last error code seen per joint, so a persistent fault is announced once
        # (on change) instead of every telemetry tick
        self._last_error = {}

    def _build_columns(self):
        cols = ['timestamp', 'elapsed_s', 'cycle', 'phase',
                'actuator_state', 'trajectory_return', 'voltage', 'avg_temperature']
        for prefix, _ in self.joint_feedbacks:
            cols += [f"{prefix}_{joint}" for joint in self.joint_names]
        for finger in self.force_sensors:
            cols += [f"fingertip_{finger}_{axis}" for axis in ('x', 'y', 'z')]
        cols += ['error_flags']   # consolidated plain-text decode of any active faults
        return cols

    # -- file handling ---------------------------------------------------------

    def open(self):
        if not self.joint_names:
            raise ValueError("No joints defined on this robot — nothing to log")
        os.makedirs(TELEMETRY_LOG_DIR, exist_ok=True)
        self._stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._start = time.monotonic()
        self._open_part()
        return self

    def _open_part(self):
        path = os.path.join(
            TELEMETRY_LOG_DIR, f"{self._stamp}_{self.title}_{self._part:03d}.csv"
        )
        self._file = open(path, 'w', newline='')
        self._writer = csv.writer(self._file)
        self._writer.writerow(self.columns)
        self._rows_in_part = 0
        self.paths.append(path)
        print(f"Logging telemetry to {path} every {self.interval_s} s "
              f"({len(self.columns)} columns)")

    def _rotate_if_needed(self):
        """Roll to the next part file. Called before a write, not after, so a run
        that ends exactly on the boundary doesn't leave an empty trailing file."""
        if self.max_rows_per_file and self._rows_in_part >= self.max_rows_per_file:
            self._file.close()
            self._part += 1
            self._open_part()

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
        print(f"{self.samples} samples ({self.failures} failed reads) written to "
              f"{len(self.paths)} file(s) in {TELEMETRY_LOG_DIR}")

    # -- sampling --------------------------------------------------------------

    def _safe(self, getter, *args):
        """Call a getter, returning None (and logging) on any error, so one dead
        feedback type blanks its own columns instead of killing the whole row."""
        try:
            return getter(*args)
        except Exception as e:
            self.failures += 1
            self.logger.error(f"{getattr(getter, '__name__', 'getter')} failed: {e}")
            return None

    def _collect(self):
        """Read every feedback type once; return a column->raw value dict.
        Missing columns are simply absent and render as blanks on write."""
        values = {}

        status = self._safe(self.artusapi.get_robot_status)
        if isinstance(status, tuple) and len(status) == 2:
            values['actuator_state'], values['trajectory_return'] = status

        voltage = self._safe(self.artusapi.get_voltage)
        if voltage is not None:
            values['voltage'] = voltage

        avg_temp = self._safe(self.artusapi.get_avg_temperature)
        if avg_temp is not None:
            values['avg_temperature'] = avg_temp

        for prefix, getter in self.joint_feedbacks:
            data = self._safe(getter)
            if isinstance(data, dict):
                for joint in self.joint_names:
                    if joint in data:
                        values[f"{prefix}_{joint}"] = data[joint]
                        if prefix == 'error':
                            self._note_error(joint, data[joint])

        if self.force_sensors:
            ft = self._safe(self.artusapi.get_fingertip_forces)
            if isinstance(ft, dict):
                for finger in self.force_sensors:
                    axes = ft.get(finger) or {}
                    for axis in ('x', 'y', 'z'):
                        if axis in axes:
                            values[f"fingertip_{finger}_{axis}"] = axes[axis]

        return values

    def _note_error(self, joint, code):
        """Log a joint's decoded error in plain text, but only when it changes,
        so a fault that persists across many ticks is announced once rather than
        spamming the console for the rest of the run."""
        try:
            code = int(code)
        except (TypeError, ValueError):
            return
        prev = self._last_error.get(joint, 0)
        if code == prev:
            return
        self._last_error[joint] = code
        if code:
            hex_str, names = decode_motor_error(code)
            text = " | ".join(names) if names else "no known flags"
            self.logger.error(f"{joint} error {hex_str}: {text}")
            print(f"  !! {joint} error {hex_str}: {text}")
        elif prev:
            self.logger.info(f"{joint} error cleared (was {hex(prev)})")
            print(f"  -- {joint} error cleared")

    def sample(self, cycle=0, phase=''):
        """Read all feedback once and write a row."""
        self._rotate_if_needed()

        values = self._collect()
        values['timestamp'] = datetime.now().isoformat(timespec='milliseconds')
        values['elapsed_s'] = round(time.monotonic() - self._start, 3)
        values['cycle'] = cycle
        values['phase'] = phase

        # consolidated plain-text error column: "joint=FLAG_A|FLAG_B; ..." across
        # any joints with an active fault this tick, so the CSV is self-describing
        # without having to decode the numeric error_ columns by hand afterward
        active = []
        for joint in self.joint_names:
            decoded = decode_motor_error(values.get(f"error_{joint}", 0))
            if decoded is not None and decoded[1]:
                active.append(f"{joint}=" + "|".join(decoded[1]))
        values['error_flags'] = "; ".join(active)

        # a row counts as a sample unless every device column came back empty
        device_cols = len(self.columns) - 4  # minus timestamp/elapsed/cycle/phase
        empty = sum(1 for c in self.columns[4:] if c not in values)
        if empty >= device_cols:
            pass  # nothing read this tick; failures already counted in _safe
        else:
            self.samples += 1

        # raw values written as-is; csv str()s them at full precision, no rounding
        self._writer.writerow([values.get(col, '') for col in self.columns])
        self._file.flush()
        self._rows_in_part += 1

        if self.print_every and self.samples and self.samples % self.print_every == 0:
            v = values.get('voltage', '')
            t = values.get('avg_temperature', '')
            st = values.get('actuator_state', '')
            print(f"[{phase:>5}] cycle {cycle}  {values['elapsed_s']:8.1f} s   "
                  f"V={v}  Tavg={t}  state={st}")

    def run(self, duration_s=None, cycle=0, phase=''):
        """
        Sample for duration_s seconds (None = until KeyboardInterrupt), then return.
        Wall time consumed equals duration_s, so this replaces a time.sleep() of the
        same length rather than adding to it.
        """
        seg_start = time.monotonic()
        end = None if duration_s is None else seg_start + duration_s
        k = 0

        while True:
            self.sample(cycle=cycle, phase=phase)
            k += 1

            next_t = seg_start + k * self.interval_s
            if end is not None and next_t >= end:
                remaining = end - time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)
                return

            # absolute scheduling so the period doesn't drift with read latency
            sleep_for = next_t - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)
            elif sleep_for < -self.interval_s:
                self.logger.warning(
                    f"telemetry is falling behind by {-sleep_for:.2f} s — "
                    f"reading all feedback takes longer than the {self.interval_s}s interval"
                )


def log_all_feedback(artusapi, logger, interval_s=TELEMETRY_INTERVAL_S, duration_s=None):
    """
    Standalone full-telemetry logging (menu option 18), no motion commanded.

    Parameters:
    :duration_s: total run time in seconds; None runs until Ctrl+C

    Returns:
    :paths: list of CSV files written
    """
    telem = HandTelemetryLogger(artusapi, logger, interval_s=interval_s, title='telemetry')
    telem.open()
    print("Ctrl+C to stop")
    try:
        telem.run(duration_s=duration_s, phase='idle')
    except KeyboardInterrupt:
        # caught here so Ctrl+C returns to the menu instead of exiting the script
        print()
        logger.info("Telemetry logging stopped by user")
    finally:
        telem.close()
    return telem.paths



# -------------------------------------------------------------------------------
# ----------------------------- Lifetime Cycle Test -----------------------------
# -------------------------------------------------------------------------------
def run_lifetime_cycle_test(artusapi, logger, hand_poses_path):
    """
    Alternate the grasp_example (close) and grasp_open poses lifetime_test_count
    times, logging all hand feedback to CSV throughout.

    Pose commands go through general_example.handle_command('6'/'8') — the exact
    same path as menu options 6 and 8 — so the cycle test can't drift from the
    known-good pose-send behaviour. Sampling replaces the dwell between poses:
    telem.run(cycle_dwell_s) consumes the same wall time a time.sleep() would,
    but records data while it waits.
    """
    telem = HandTelemetryLogger(
        artusapi, logger,
        interval_s=TELEMETRY_INTERVAL_S,
        title='lifetime_cycle',
        print_every=12,   # ~one console line per cycle
    )
    telem.open()
    x = 0
    try:
        for x in range(lifetime_test_count):
            logger.info(f"Cycle {x}: closing to grasp_example")
            handle_command(artusapi, '6', logger, hand_poses_path)
            telem.run(cycle_dwell_s, cycle=x, phase='close')

            logger.info(f"Cycle {x}: opening to grasp_open")
            handle_command(artusapi, '8', logger, hand_poses_path)
            telem.run(cycle_dwell_s, cycle=x, phase='open')
    except KeyboardInterrupt:
        print()
        logger.info(f"Lifetime cycle test stopped by user after {x} cycles")
    finally:
        telem.close()


# -------------------------------------------------------------------------------
# --------------------------------- Example -------------------------------------
# -------------------------------------------------------------------------------
def example():
    """Interactive menu loop.

    Options 17 (lifetime cycle test) and 18 (standalone telemetry) are handled
    here; everything else is delegated to general_example.handle_command(), the
    same dispatch the standard CLI uses.
    """
    # Load the configuration file
    config = ArtusConfig()

    artusapi = None
    hand_poses_path = os.path.join(PROJECT_ROOT, 'data', 'hand_poses')
    logger = setup_logger(level=config.config.logging.level, format=config.config.logging.format)
    # new api
    artusapi = config.get_api(logger=logger)

    # Main loop (example)
    while True:
        try:
            user_input = main_menu()

            if user_input == '17':
                run_lifetime_cycle_test(artusapi, logger, hand_poses_path)
            elif user_input == '18':
                duration_input = input(
                    "Log duration in seconds (blank = until Ctrl+C): "
                ).strip()
                log_all_feedback(
                    artusapi,
                    logger,
                    interval_s=TELEMETRY_INTERVAL_S,
                    duration_s=float(duration_input) if duration_input else None,
                )
            elif user_input == '16':
                # decode the error report into plain text instead of the raw
                # decimal bitmask handle_command() would otherwise just log
                print_error_report(artusapi.get_error_report(), logger)
            else:
                handle_command(artusapi, user_input, logger, hand_poses_path)
        except Exception as e:
            logger.error(f"Error: {e}")
            pass


# ----------------------------------------------------------------------------------
# ---------------------------------- Main ------------------------------------------
# ----------------------------------------------------------------------------------
if __name__ == '__main__':
    example()
