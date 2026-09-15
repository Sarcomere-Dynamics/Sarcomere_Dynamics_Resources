"""Tests for ArtusAPI.configuration (no serial I/O)."""

import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from artusapi.configuration import (
    CONFIG_ENV_VAR,
    ArtusConfig,
    copy_default_config,
    packaged_config_source,
    resolve_config_file,
    scan_port_for_robots,
)

_SAMPLE_YAML = """
robots:
  left_hand_robot:
    robot_connected: true
    robot_type: artus_lite
    communication_method: RS485_RTU
    baudrate: 115200
    communication_channel_identifier: /dev/ttyUSB0
    hand_type: left
    start_robot: true
    reset_on_start: 0
    streaming_frequency: 20
    calibrate: true
  right_hand_robot:
    robot_connected: false
    robot_type: artus_lite
    communication_method: RS485_RTU
    baudrate: 115200
    communication_channel_identifier: /dev/ttyUSB1
    hand_type: right
    start_robot: false
    reset_on_start: 0
    streaming_frequency: 30
    calibrate: false
logging:
  level: INFO
  format: '%(message)s'
"""


class TestResolveConfigFile(unittest.TestCase):
    """Verifies config-file search order without touching serial ports."""

    def test_explicit_path_wins(self):
        """Verifies an explicit path is returned unchanged."""
        self.assertEqual(resolve_config_file("/tmp/custom.yaml"), "/tmp/custom.yaml")

    def test_env_var_used_when_no_explicit_path(self):
        """Verifies ARTUS_CONFIG is used when no path is passed."""
        with patch.dict(os.environ, {CONFIG_ENV_VAR: "/tmp/from-env.yaml"}):
            self.assertEqual(resolve_config_file(), "/tmp/from-env.yaml")

    def test_explicit_path_beats_env_var(self):
        """Verifies an explicit path takes priority over ARTUS_CONFIG."""
        with patch.dict(os.environ, {CONFIG_ENV_VAR: "/tmp/from-env.yaml"}):
            self.assertEqual(
                resolve_config_file("/tmp/explicit.yaml"), "/tmp/explicit.yaml"
            )


class TestArtusConfigLoading(unittest.TestCase):
    """Verifies YAML loading and connected-hand helpers."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cfg_path = Path(self._tmpdir.name) / "robot_config.yaml"
        self.cfg_path.write_text(_SAMPLE_YAML, encoding="utf-8")
        self.config = ArtusConfig(str(self.cfg_path))

    def test_loads_nested_namespace(self):
        """Verifies YAML keys are reachable via attribute access."""
        self.assertEqual(
            self.config.config.robots.left_hand_robot.robot_type, "artus_lite"
        )
        self.assertEqual(self.config.config.logging.level, "INFO")

    def test_stores_resolved_path(self):
        """Verifies ArtusConfig records the file it loaded."""
        self.assertEqual(self.config.config_file, str(self.cfg_path))

    def test_find_single_robot_type_left(self):
        """Verifies find_single_robot_type returns the connected left hand."""
        self.assertEqual(self.config.find_single_robot_type(), "artus_lite")

    def test_find_single_robot_type_none_connected(self):
        """Verifies find_single_robot_type raises when no hand is connected."""
        self.config.config.robots.left_hand_robot.robot_connected = False
        with self.assertRaises(ValueError):
            self.config.find_single_robot_type()

    def test_get_robot_calibrate_default_hand(self):
        """Verifies get_robot_calibrate reads the connected hand when hand_type is omitted."""
        self.assertTrue(self.config.get_robot_calibrate())

    def test_get_robot_calibrate_by_hand(self):
        """Verifies get_robot_calibrate respects an explicit hand_type."""
        self.assertTrue(self.config.get_robot_calibrate("left"))
        self.assertFalse(self.config.get_robot_calibrate("right"))

    def test_get_robot_wake_up(self):
        """Verifies get_robot_wake_up reads start_robot for the connected hand."""
        self.assertTrue(self.config.get_robot_wake_up())
        self.assertFalse(self.config.get_robot_wake_up("right"))

    def test_get_robot_wake_up_invalid_hand(self):
        """Verifies get_robot_wake_up rejects an unknown hand_type."""
        with self.assertRaises(ValueError):
            self.config.get_robot_wake_up("both")

    def test_check_and_print_invalid_hand(self):
        """Verifies check_and_print_robot_config rejects an unknown hand_type."""
        with self.assertRaises(ValueError):
            self.config.check_and_print_robot_config("middle")

    def test_logger_created_from_yaml(self):
        """Verifies ArtusConfig builds a logger from the YAML logging section."""
        self.assertIsNotNone(self.config.logger)
        self.assertEqual(self.config.logger.level, logging.INFO)

    def test_explicit_logger_used(self):
        """Verifies a caller-supplied logger is stored instead of creating one."""
        custom = logging.getLogger("artus_config_test_custom")
        cfg = ArtusConfig(str(self.cfg_path), logger=custom)
        self.assertIs(cfg.logger, custom)

    def test_logs_yaml_path(self):
        """Verifies ArtusConfig logs the filesystem path of the YAML it loaded."""
        custom = logging.getLogger("artus_config_test_yaml_path")
        custom.setLevel(logging.INFO)
        with self.assertLogs(custom, level="INFO") as cm:
            ArtusConfig(str(self.cfg_path), logger=custom)
        resolved = str(self.cfg_path.resolve())
        self.assertTrue(
            any(
                "Using robot config:" in line and resolved in line for line in cm.output
            ),
            msg=cm.output,
        )

    def test_get_connected_robot_left(self):
        """Verifies get_connected_robot returns the connected left-hand block."""
        robot_cfg = self.config.get_connected_robot()
        self.assertEqual(robot_cfg.hand_type, "left")
        self.assertEqual(robot_cfg.robot_type, "artus_lite")


class TestAutoPortSelect(unittest.TestCase):
    """Verifies automatic port/robot discovery without real serial I/O."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.cfg_path = Path(self._tmpdir.name) / "robot_config.yaml"
        self.cfg_path.write_text(_SAMPLE_YAML, encoding="utf-8")
        self.logger = logging.getLogger("artus_config_test_scan")
        self.logger.handlers.clear()
        self.config = ArtusConfig(str(self.cfg_path), logger=self.logger)

    def test_no_ports_raises(self):
        """Verifies _validate_port_or_select raises when no serial ports exist."""
        robot_cfg = self.config.get_connected_robot()
        with (
            patch(
                "ArtusAPI.configuration.serial.tools.list_ports.comports",
                return_value=[],
            ),
            self.assertRaises(RuntimeError),
        ):
            self.config._validate_port_or_select(robot_cfg, self.logger)

    def test_scans_each_port_then_each_robot(self):
        """Verifies discovery walks ports, then slave IDs, and records the first PASS."""
        port_a = MagicMock(device="/dev/ttyUSB0")
        port_b = MagicMock(device="/dev/ttyUSB1")

        class FakeResult:
            def __init__(self, error):
                self._error = error

            def isError(self):
                return self._error

        class FakeClient:
            def __init__(self, port, **kwargs):
                self.port = port

            def connect(self):
                return True

            def close(self):
                pass

            def read_holding_registers(self, *args, device_id=None, **kwargs):
                if self.port == "/dev/ttyUSB1" and device_id == 5:
                    return FakeResult(False)
                return FakeResult(True)

        robot_cfg = self.config.get_connected_robot()
        with patch("ArtusAPI.configuration.ModbusSerialClient", FakeClient):
            with patch(
                "ArtusAPI.configuration.serial.tools.list_ports.comports",
                return_value=[port_a, port_b],
            ):
                result = self.config._validate_port_or_select(robot_cfg, self.logger)

        self.assertEqual(result.communication_channel_identifier, "/dev/ttyUSB1")
        self.assertEqual(result.robot_type, "artus_talos")
        self.assertEqual(result.hand_type, "left")

    def test_scan_port_logs_fail_when_unopenable(self):
        """Verifies scan_port_for_robots returns None and logs FAIL if the port will not open."""

        class ClosedClient:
            def __init__(self, port, **kwargs):
                pass

            def connect(self):
                return False

        with patch("ArtusAPI.configuration.ModbusSerialClient", ClosedClient):
            with patch("ArtusAPI.configuration.find_port_holders", return_value=[]):
                found = scan_port_for_robots("/dev/ttyUSB9", 115200, self.logger)

        self.assertIsNone(found)

    def test_configured_identity_preferred_on_its_port(self):
        """Verifies the configured slave ID is probed first and accepted on PASS."""

        class FakeResult:
            def __init__(self, error):
                self._error = error

            def isError(self):
                return self._error

        class FakeClient:
            def __init__(self, port, **kwargs):
                self.port = port

            def connect(self):
                return True

            def close(self):
                pass

            def read_holding_registers(self, *args, device_id=None, **kwargs):
                return FakeResult(device_id != 1)

        port = MagicMock(device="/dev/ttyUSB0")
        robot_cfg = self.config.get_connected_robot()
        with patch("ArtusAPI.configuration.ModbusSerialClient", FakeClient):
            with patch(
                "ArtusAPI.configuration.serial.tools.list_ports.comports",
                return_value=[port],
            ):
                result = self.config._validate_port_or_select(robot_cfg, self.logger)

        self.assertEqual(result.communication_channel_identifier, "/dev/ttyUSB0")
        self.assertEqual(result.robot_type, "artus_lite")
        self.assertEqual(result.hand_type, "left")


class TestPackagedConfig(unittest.TestCase):
    """Verifies the default YAML shipped inside the ArtusAPI package."""

    def test_packaged_yaml_is_readable(self):
        """Verifies the packaged robot_config.yaml parses as a robots config."""
        text = packaged_config_source().read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        self.assertIn("robots", parsed)
        self.assertIn("left_hand_robot", parsed["robots"])
        self.assertIn("right_hand_robot", parsed["robots"])

    def test_copy_default_config_writes_file(self):
        """Verifies copy_default_config writes the packaged template to disk."""
        with tempfile.TemporaryDirectory() as tmp:
            dest = copy_default_config(tmp)
            self.assertTrue(dest.is_file())
            self.assertEqual(dest.name, "robot_config.yaml")
            copied = ArtusConfig(str(dest))
            self.assertTrue(hasattr(copied.config, "robots"))


if __name__ == "__main__":
    unittest.main()
