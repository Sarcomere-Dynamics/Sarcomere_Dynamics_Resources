"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from __future__ import annotations

import logging
import os
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import serial.tools.list_ports
import yaml
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

from .common.ModbusMap import ModbusMap
from .common.SlaveIDMap import (
    SLAVE_ID_BY_ROBOT_HAND,
    expected_slave_id,
    robot_hand_from_slave_id,
)
from .communication.RS485_RTU.rs485_rtu import find_port_holders

CONFIG_ENV_VAR = "ARTUS_CONFIG"
PACKAGED_CONFIG_NAME = "robot_config.yaml"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOGGER_NAME = "ArtusAPI"

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_EXAMPLE_CONFIG = (
    _PACKAGE_DIR.parent / "examples" / "config" / "robot_config.yaml"
)


def packaged_config_source():
    """Returns the packaged default robot_config.yaml resource."""
    return files("ArtusAPI").joinpath(PACKAGED_CONFIG_NAME)


def resolve_config_file(config_file=None):
    """Resolves which YAML file ArtusConfig should load.

    An explicit *config_file* (the user's described path) is always used
    as-is. When omitted, search order is:
    1. ``ARTUS_CONFIG`` environment variable
    2. ``examples/config/robot_config.yaml`` in an editable/repo checkout
    3. ``robot_config.yaml`` in the current working directory
    4. The packaged default shipped with ArtusAPI (returned as None)

    Args:
        config_file: Filesystem path to the user's ``robot_config.yaml``.
            When given, it is used as-is and nothing else is searched.

    Returns:
        A filesystem path string, or None to mean "use the packaged default".
    """
    if config_file is not None:
        return str(config_file)

    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path:
        return env_path

    if _REPO_EXAMPLE_CONFIG.is_file():
        return str(_REPO_EXAMPLE_CONFIG)

    cwd_cfg = Path.cwd() / PACKAGED_CONFIG_NAME
    if cwd_cfg.is_file():
        return str(cwd_cfg)

    return None


def copy_default_config(dest):
    """Writes the packaged robot_config.yaml template to *dest*.

    Args:
        dest: File path, or a directory (writes ``robot_config.yaml`` inside it).

    Returns:
        The Path of the written file.
    """
    dest = Path(dest)
    if dest.exists() and dest.is_dir():
        dest = dest / PACKAGED_CONFIG_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        packaged_config_source().read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return dest


def _load_yaml(config_file):
    """Reads and parses a robot config YAML from a path or the packaged default.

    Args:
        config_file: Filesystem path, or None to read the packaged template.

    Returns:
        The parsed YAML as a dict (or other YAML root type).
    """
    if config_file is None:
        with packaged_config_source().open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    with open(config_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _open_probe_client(port, baudrate):
    """Opens a short-timeout Modbus serial client for discovery probes.

    Args:
        port: Serial device path to open.
        baudrate: Serial baudrate to use for the probe.

    Returns:
        A connected ``ModbusSerialClient``, or None if the port could not
        be opened.
    """
    client = ModbusSerialClient(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=0.15,
        retries=0,
    )
    if not client.connect():
        return None
    return client


def _probe_slave(client, slave_id, status_reg) -> bool:
    """Attempts a single-register read against the given slave ID.

    Args:
        client: Connected ``ModbusSerialClient`` to probe with.
        slave_id: Modbus slave/device ID to probe.
        status_reg: Holding-register address to read.

    Returns:
        True if the read succeeded without error, False otherwise.
    """
    try:
        result = client.read_holding_registers(status_reg, count=1, device_id=slave_id)
        return not result.isError()
    except ModbusException:
        return False


def scan_port_for_robots(port, baudrate, logger, prefer_slave=None):
    """Probes every known ARTUS slave ID on a single serial port.

    Logs PASS/FAIL for the port open and for each robot identity tried.
    ``prefer_slave`` is probed first when it is a known ID so a configured
    hand is found before other identities on the same bus.

    Args:
        port: Serial device path to scan.
        baudrate: Serial baudrate to use for the probe.
        logger: Logger used for progress PASS/FAIL messages.
        prefer_slave: Optional slave ID to try first.

    Returns:
        ``(slave_id, robot_type, hand_type)`` for the first responding
        hand, or None if the port could not be opened or no known ID
        responded.
    """
    logger.info("Scanning port %s for ARTUS hands...", port)
    client = _open_probe_client(port, baudrate)
    if client is None:
        holders = find_port_holders(port)
        reason = "could not open"
        if holders:
            reason += f" (held by: {'; '.join(holders)})"
        logger.info("  %s: FAIL (%s)", port, reason)
        return None

    status_reg = ModbusMap().modbus_reg_map["feedback_register"]
    slave_ids = list(SLAVE_ID_BY_ROBOT_HAND.values())
    if prefer_slave in slave_ids:
        slave_ids = [prefer_slave] + [s for s in slave_ids if s != prefer_slave]

    try:
        for slave_id in slave_ids:
            identity = robot_hand_from_slave_id(slave_id)
            if identity:
                robot_type, hand_type = identity
                label = f"{robot_type}/{hand_type}"
            else:
                robot_type = hand_type = None
                label = f"slave {slave_id}"

            if _probe_slave(client, slave_id, status_reg):
                logger.info("  %s %s (id=%s): PASS", port, label, slave_id)
                return slave_id, robot_type, hand_type
            logger.info("  %s %s (id=%s): FAIL", port, label, slave_id)
        return None
    finally:
        client.close()


class ArtusConfig:
    """Loads robot_config.yaml and builds a configured ArtusAPI_V2 instance.

    The YAML config is converted into nested SimpleNamespace objects so
    fields are accessible via attribute access (e.g. config.robots.left_hand_robot).
    """

    def __init__(self, config_file=None, logger=None):
        """Loads and converts the given YAML config file.

        Args:
            config_file: Path to the user's ``robot_config.yaml``. When
                omitted, see :func:`resolve_config_file` -- the packaged
                default shipped with ArtusAPI is used if no other file is
                found.
            logger: Optional logger. When omitted, one is created from the
                YAML ``logging`` section (level and format).
        """
        self.config_file = resolve_config_file(config_file)
        self.config = self.load_and_convert_config(self.config_file)
        self.logger = self._setup_logger(logger)
        self.logger.info("Using robot config: %s", self._config_path_for_log())

    def _config_path_for_log(self):
        """Returns a display path for the YAML file that was loaded.

        Returns:
            An absolute filesystem path, or a packaged-default label when
            no file path was resolved.
        """
        if self.config_file is None:
            return f"packaged default ({PACKAGED_CONFIG_NAME})"
        return str(Path(self.config_file).expanduser().resolve())

    def load_and_convert_config(self, config_file):
        """Reads a YAML config file and converts it to nested SimpleNamespace objects.

        Args:
            config_file: Path to the YAML config file, or None for the
                packaged default.

        Returns:
            A SimpleNamespace (or nested structure of SimpleNamespace/list)
            representing the parsed YAML content.
        """
        return self.dict_to_namespace(_load_yaml(config_file))

    def dict_to_namespace(self, d):
        """Recursively converts a dict (and any nested dicts/lists) into SimpleNamespace objects.

        Args:
            d: A dict, list, or scalar value to convert.

        Returns:
            The equivalent structure with dicts replaced by SimpleNamespace
            objects; lists and scalars are recursed into or returned as-is.
        """
        if isinstance(d, dict):
            return SimpleNamespace(**{k: self.dict_to_namespace(v) for k, v in d.items()})
        if isinstance(d, list):
            return [self.dict_to_namespace(i) for i in d]
        return d

    def _setup_logger(self, logger=None):
        """Returns *logger* or builds one from the YAML ``logging`` section.

        Args:
            logger: Optional caller-supplied logger. Used as-is when given.

        Returns:
            The supplied logger, or a console logger named ``ArtusAPI``
            configured from ``config.logging.level`` / ``config.logging.format``.
        """
        if logger is not None:
            return logger

        logging_cfg = getattr(self.config, "logging", None)
        level_name = getattr(logging_cfg, "level", "INFO") if logging_cfg else "INFO"
        fmt = getattr(logging_cfg, "format", DEFAULT_LOG_FORMAT) if logging_cfg else DEFAULT_LOG_FORMAT
        level = getattr(logging, str(level_name).upper(), logging.INFO)

        configured = logging.getLogger(LOGGER_NAME)
        configured.setLevel(level)
        if not configured.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            handler.setFormatter(logging.Formatter(fmt))
            configured.addHandler(handler)
        return configured

    def get_connected_robot(self):
        """Returns the configuration of the single connected hand.

        Returns:
            The SimpleNamespace for the connected left or right hand.

        Raises:
            ValueError: If neither hand (or both hands) are connected.
        """
        left = self.config.robots.left_hand_robot
        right = self.config.robots.right_hand_robot
        if left.robot_connected and not right.robot_connected:
            return left
        if right.robot_connected and not left.robot_connected:
            return right
        raise ValueError(
            "No robot connected or multiple robots connected. "
            "Only one robot can be connected at a time."
        )

    def check_and_print_robot_config(self, hand_type):
        """Prints the configuration for the given hand if it is connected.

        Args:
            hand_type: Either 'left' or 'right'.

        Raises:
            ValueError: If hand_type is not 'left' or 'right'.
        """
        if hand_type == "left":
            robot_config = self.config.robots.left_hand_robot
        elif hand_type == "right":
            robot_config = self.config.robots.right_hand_robot
        else:
            raise ValueError("Invalid hand type. Choose 'left' or 'right'.")

        if robot_config.robot_connected:
            self.logger.info("%s Hand Robot Configuration:", hand_type.capitalize())
            for key, value in vars(robot_config).items():
                self.logger.info("%s: %s", key, value)
        else:
            self.logger.info("%s hand robot is not connected.", hand_type.capitalize())

    def find_single_robot_type(self) -> str:
        """Determines the robot_type of whichever single hand is marked connected.

        Returns:
            The robot_type string of the connected hand.

        Raises:
            ValueError: If neither hand (or both hands) are connected.
        """
        return self.get_connected_robot().robot_type

    def get_api(self, logger=None):
        """Builds a configured ArtusAPI_V2 instance for whichever hand is connected.

        Only one robot can be connected at a time. The API loads this
        configuration first, then runs automatic port/robot discovery
        before building robot-specific handlers.

        Args:
            logger: Optional logger passed through to the API instance and
                used for pre-flight messages. Defaults to ``self.logger``.

        Returns:
            A configured ArtusAPI_V2 instance for the connected hand.

        Raises:
            ValueError: If no robot is connected, or more than one is.
        """
        logger = logger or self.logger
        robot_cfg = self.get_connected_robot()
        logger.info("%s hand robot connected", robot_cfg.hand_type.capitalize())
        from .artus_api_new import ArtusAPI_V2
        return ArtusAPI_V2(config=self, logger=logger)

    def _preflight(self, robot_cfg, logger):
        """Discovers the serial port and robot identity before the API builds handlers.

        Corrects robot_cfg in place if a different port or slave ID responds.
        Skipped for Modbus TCP configs, where serial port selection and
        slave ID probing do not apply.

        Args:
            robot_cfg: SimpleNamespace of the connected robot's configuration.
            logger: Optional logger for pre-flight messages. Defaults to
                ``self.logger``.

        Returns:
            The (possibly corrected) robot_cfg.
        """
        if getattr(robot_cfg, "communication_method", "RS485_RTU") == "Modbus_TCP":
            return robot_cfg
        return self._validate_port_or_select(robot_cfg, logger)

    def _validate_port_or_select(self, robot_cfg, logger):
        """Automatically finds a responding ARTUS hand across available ports.

        Walks every serial port, and on each port every known robot
        identity (Modbus slave ID). The configured port is tried first,
        with its configured slave ID preferred. Progress is logged as
        PASS/FAIL for each port and each robot. No user prompt.

        Args:
            robot_cfg: SimpleNamespace of the connected robot's configuration.
            logger: Optional logger for progress messages. Defaults to
                ``self.logger``.

        Returns:
            robot_cfg with ``communication_channel_identifier``,
            ``robot_type``, and ``hand_type`` updated to the first
            responding hand.

        Raises:
            RuntimeError: If no serial ports are found, or if no ARTUS
                hand responds on any port.
        """
        logger = logger or self.logger
        available_ports = [p.device for p in serial.tools.list_ports.comports()]
        if not available_ports:
            raise RuntimeError("No serial ports found. Check USB connection.")

        configured_port = robot_cfg.communication_channel_identifier
        baudrate = getattr(robot_cfg, "baudrate", 115200)
        configured_slave = expected_slave_id(robot_cfg.robot_type, robot_cfg.hand_type)

        ports = []
        if configured_port in available_ports:
            ports.append(configured_port)
        ports.extend(p for p in available_ports if p != configured_port)

        logger.info(
            "Auto-detecting ARTUS hand. Configured: %s %s/%s (slave %s)",
            configured_port,
            robot_cfg.robot_type,
            robot_cfg.hand_type,
            configured_slave,
        )

        for port in ports:
            prefer = configured_slave if port == configured_port else None
            found = scan_port_for_robots(port, baudrate, logger, prefer_slave=prefer)
            if found is None:
                continue

            slave_id, robot_type, hand_type = found
            robot_cfg.communication_channel_identifier = port
            if (robot_type, hand_type) != (robot_cfg.robot_type, robot_cfg.hand_type):
                logger.warning(
                    "Found slave ID %s (%s/%s) on %s. "
                    "Update robot_config.yaml: robot_type: %s, hand_type: %s",
                    slave_id,
                    robot_type,
                    hand_type,
                    port,
                    robot_type,
                    hand_type,
                )
                robot_cfg.robot_type = robot_type
                robot_cfg.hand_type = hand_type
            else:
                logger.info("Using %s/%s on %s", robot_type, hand_type, port)
            return robot_cfg

        raise RuntimeError(
            "No ARTUS hand found on any serial port. Check power and USB connection."
        )

    def return_api(self, robot_cfg=None, logger=None):
        """Instantiates ArtusAPI_V2 from a robot configuration.

        Explicit robot fields are passed as overrides so the API skips
        automatic port discovery (the caller already chose a hand).

        Args:
            robot_cfg: SimpleNamespace of the connected robot's configuration.
            logger: Optional logger passed through to the API instance.

        Returns:
            A configured ArtusAPI_V2 instance, or None if robot_cfg is None.
        """
        if robot_cfg is None:
            return None
        from .artus_api_new import ArtusAPI_V2
        return ArtusAPI_V2(
            config=self,
            logger=logger or self.logger,
            robot_type=robot_cfg.robot_type,
            communication_method=robot_cfg.communication_method,
            communication_channel_identifier=robot_cfg.communication_channel_identifier,
            hand_type=robot_cfg.hand_type,
            communication_frequency=(
                robot_cfg.streaming_frequency
                if hasattr(robot_cfg, "streaming_frequency")
                else 20
            ),
            baudrate=getattr(robot_cfg, "baudrate", 115200),
        )

    def get_robot_calibrate(self, hand_type: str = None) -> bool:
        """Reads the calibrate flag from config.

        Args:
            hand_type: 'left' or 'right' to check a specific hand; if None,
                checks whichever hand is marked connected.

        Returns:
            True if the calibrate flag is set for the relevant hand, False
            if it is not set or no hand is connected (when hand_type is None).
        """
        if hand_type is None:
            if self.config.robots.left_hand_robot.robot_connected:
                return self.config.robots.left_hand_robot.calibrate
            if self.config.robots.right_hand_robot.robot_connected:
                return self.config.robots.right_hand_robot.calibrate
            return False
        if hand_type == "left":
            return self.config.robots.left_hand_robot.calibrate
        if hand_type == "right":
            return self.config.robots.right_hand_robot.calibrate

    def get_robot_wake_up(self, hand_type: str = None) -> bool:
        """Reads the start_robot (wake up) flag from config.

        Args:
            hand_type: 'left' or 'right' to check a specific hand; if None,
                checks whichever hand is marked connected.

        Returns:
            True if the start_robot flag is set for the relevant hand, False
            if it is not set or no hand is connected (when hand_type is None).

        Raises:
            ValueError: If hand_type is given but is not 'left' or 'right'.
        """
        if hand_type is None:
            if self.config.robots.left_hand_robot.robot_connected:
                return self.config.robots.left_hand_robot.start_robot
            if self.config.robots.right_hand_robot.robot_connected:
                return self.config.robots.right_hand_robot.start_robot
            return False
        if hand_type == "left":
            return self.config.robots.left_hand_robot.start_robot
        if hand_type == "right":
            return self.config.robots.right_hand_robot.start_robot
        raise ValueError("Invalid hand type. Choose 'left' or 'right'.")

    copy_default_config = staticmethod(copy_default_config)


if __name__ == "__main__":
    robot_config = ArtusConfig()

    robot_config.check_and_print_robot_config("left")
    robot_config.check_and_print_robot_config("right")
