"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
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

# import the configuration file
from examples.config.configuration import ArtusConfig

# new version of ArtusAPI use local version
from ArtusAPI.artus_api_new import ArtusAPI_V2
from ArtusAPI.common import ModbusMap

# ------------------------------------------------------------------------------
# ---------------------------- Life Cycle Testing ------------------------------
# ------------------------------------------------------------------------------

lifetime_test_count = 500 #100k
cycle_dwell_s = 2            # hold time at each pose

# ------------------------------------------------------------------------------
# ------------------------------ Telemetry Logging -----------------------------
# ------------------------------------------------------------------------------

TELEMETRY_INTERVAL_S = 1.0      # seconds between full telemetry samples
TELEMETRY_LOG_DIR = os.path.join(PROJECT_ROOT, 'logs', 'telemetry')
# roll over to a new file before hitting Excel's 1,048,576-row ceiling; a full
# 100k-cycle run at 2 Hz is ~1.2M rows, which would not open in one sheet
TELEMETRY_MAX_ROWS = 500000

# ------------------------------------------------------------------------------
# -------------------------------- Main Menu -----------------------------------
# ------------------------------------------------------------------------------
def main_menu():
    return input(
    """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                          Artus API 2.0                           ║
    ╠══════════════════════════════════════════════════════════════════╣
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
    ╚══════════════════════════════════════════════════════════════════╝
    >> Input Command Code (1-18): """
    
    )

# ------------------------------------------------------------------------------
# -------------------------------- Logger Setup --------------------------------
# ------------------------------------------------------------------------------
import logging

def setup_logger(level='ERROR',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    """
    Set up a logger for the ArtusAPI with proper formatting
    """
    logger = logging.getLogger('ArtusAPI_Example')
    logger.setLevel(level)
    
    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(format)
    console_handler.setFormatter(formatter)
    
    # Add handler to logger if not already added
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger


# -------------------------------------------------------------------------------
# ----------------------------- Telemetry CSV Logger ----------------------------
# -------------------------------------------------------------------------------
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

    def _build_columns(self):
        cols = ['timestamp', 'elapsed_s', 'cycle', 'phase',
                'actuator_state', 'trajectory_return', 'voltage', 'avg_temperature']
        for prefix, _ in self.joint_feedbacks:
            cols += [f"{prefix}_{joint}" for joint in self.joint_names]
        for finger in self.force_sensors:
            cols += [f"fingertip_{finger}_{axis}" for axis in ('x', 'y', 'z')]
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

        if self.force_sensors:
            ft = self._safe(self.artusapi.get_fingertip_forces)
            if isinstance(ft, dict):
                for finger in self.force_sensors:
                    axes = ft.get(finger) or {}
                    for axis in ('x', 'y', 'z'):
                        if axis in axes:
                            values[f"fingertip_{finger}_{axis}"] = axes[axis]

        return values

    def sample(self, cycle=0, phase=''):
        """Read all feedback once and write a row."""
        self._rotate_if_needed()

        values = self._collect()
        values['timestamp'] = datetime.now().isoformat(timespec='milliseconds')
        values['elapsed_s'] = round(time.monotonic() - self._start, 3)
        values['cycle'] = cycle
        values['phase'] = phase

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
# --------------------------------- Example -------------------------------------
# -------------------------------------------------------------------------------
def example():
    # Load the configuration file
    config = ArtusConfig()

    artusapi = None
    hand_poses_path = os.path.join(PROJECT_ROOT,'data','hand_poses')
    logger = setup_logger(level=config.config.logging.level,format=config.config.logging.format)
    # new api
    artusapi = config.get_api(logger=logger)

    # while True:
    #     artusapi.get_fingertip_forces()
    #     time.sleep(0.5)
    
    
    # Main loop (example)
    while True:
        try:
            user_input = main_menu()

            match user_input:
                case '1':
                    artusapi.connect()
                case '2':
                    artusapi.disconnect()
                case '3':
                    if isinstance(artusapi, ArtusAPI_V2):
                        control_type = int(input("Enter control type (1: torque, 2: velocity, 3: position): "))
                        if control_type not in [1,2,3]:
                            logger.warning("Invalid control type, defaulting to position control")
                            control_type = 3
                        artusapi.wake_up(control_type=control_type)
                    else:
                        artusapi.wake_up()
                case '4':
                    artusapi.sleep()
                case '5':
                    artusapi.calibrate()
                case '6':
                    with open(os.path.join(hand_poses_path ,'grasp_example.json'),'r') as file:
                        grasp_example_dict = json.load(file)
                    # logger.info(f"Setting joint angles to: {grasp_example_dict} and setting velocity and force to defaults")
                    # for key,value in grasp_example_dict.items():
                    #     grasp_example_dict[key]['target_velocity'] = artusapi._robot_handler.robot.default_velocity
                    #     grasp_example_dict[key]['target_force'] = artusapi._robot_handler.robot.default_force
                    artusapi.set_joint_angles(grasp_example_dict)
                case '7':
                    logger.info(artusapi.get_robot_status())
                case '8':
                    with open(os.path.join(hand_poses_path ,'grasp_open.json'),'r') as file:
                        grasp_dict = json.load(file)
                    # logger.info(f"Setting joint angles to: {grasp_dict} and setting velocity and force to defaults")
                    # for key,value in grasp_dict.items():
                    #     grasp_dict[key]['target_velocity'] = artusapi._robot_handler.robot.default_velocity
                    #     grasp_dict[key]['target_force'] = artusapi._robot_handler.robot.default_force
                    artusapi.set_joint_angles(grasp_dict)
                case '9':
                    artusapi.get_joint_angles()
                case '10':
                    artusapi.get_joint_speeds()
                case '11':
                    artusapi.get_joint_forces()
                case '12':
                    if artusapi._robot_handler.robot.force_sensors is not None:
                        artusapi.get_fingertip_forces()
                    else:
                        logger.error("Fingertip forces are not supported for this robot")
                case '13':
                    artusapi.get_voltage()
                case '14':
                    artusapi.get_avg_temperature()
                case '15':
                    artusapi.get_joint_temperatures()
                case '16':
                    artusapi.get_error_report()
                case'17': # loop between open and close 100k times, logging all feedback throughout.
                    # poses are read once here rather than per cycle — 100k reruns of
                    # json.load() buys nothing and the dicts are rebuilt below anyway
                    with open(os.path.join(hand_poses_path ,'grasp_example.json'),'r') as file:
                        grasp_example_dict = json.load(file)
                    with open(os.path.join(hand_poses_path ,'grasp_open.json'),'r') as file:
                        grasp_dict = json.load(file)
                    # for pose in (grasp_example_dict, grasp_dict):
                    #     for key,value in pose.items():
                    #         pose[key]['target_velocity'] = artusapi._robot_handler.robot.default_velocity
                    #         pose[key]['target_force'] = artusapi._robot_handler.robot.default_force

                    telem = HandTelemetryLogger(
                        artusapi, logger,
                        interval_s=TELEMETRY_INTERVAL_S,
                        title='lifetime_cycle',
                        print_every=12,   # ~one console line per cycle
                    )
                    telem.open()
                    try:
                        for x in range(lifetime_test_count):
                            logger.info(f"Cycle {x}: closing to grasp_example")
                            artusapi.set_joint_angles(grasp_example_dict)
                            # sampling replaces the dwell — same 3 s, now with data
                            telem.run(cycle_dwell_s, cycle=x, phase='close')

                            logger.info(f"Cycle {x}: opening to grasp_open")
                            artusapi.set_joint_angles(grasp_dict)
                            telem.run(cycle_dwell_s, cycle=x, phase='open')
                    except KeyboardInterrupt:
                        print()
                        logger.info(f"Lifetime cycle test stopped by user after {x} cycles")
                    finally:
                        telem.close()
                case '18':
                    duration_input = input(
                        "Log duration in seconds (blank = until Ctrl+C): "
                    ).strip()
                    log_all_feedback(
                        artusapi,
                        logger,
                        interval_s=TELEMETRY_INTERVAL_S,
                        duration_s=float(duration_input) if duration_input else None,
                    )
                case 'c':
                    artusapi.clear_errors()
                case 'r':
                    artusapi.reset()
                case 'f':
                    if input(f"DO NOT USE UNLESS SPECIFIED BY SARCOMERE DYNAMICS TEAM. Press `e` to continue") == 'e':
                        driver = int(input("Enter driver to flash: "))
                        if (driver > artusapi._robot_handler.robot.number_of_controllers or driver < 0):
                            logger.error(f"Invalid driver number, please try again")
                        else:
                            file_location_ = input(f'enter file location of driver: ')
                            artusapi.update_firmware(file_location=file_location_,drivers_to_flash=driver)
                            logger.info(f"Firmware flashed successfully")
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
# ----------------------------------------------------------------------------------
# ---------------------------------- Main ------------------------------------------
# ----------------------------------------------------------------------------------
if __name__ == '__main__':
    example()
    # import serial
    # x = serial.Serial(port='COM13',baudrate=250000, timeout= 1)
    
    # n = bytearray([0x33])*139
    
    # while True:
    #     x.write(n)
    #     time.sleep(1)