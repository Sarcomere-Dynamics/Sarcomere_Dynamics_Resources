"""ArtusAPI_V2 tests with mocked communication (no hardware)."""

from __future__ import annotations

import struct
import unittest
from unittest.mock import MagicMock, patch

from ArtusAPI.api_tests.mocks import build_api, make_communication_mock, patched_artus_api_v2_constructor
from ArtusAPI.common.ModbusMap import ModbusMap
from ArtusAPI.common.SlaveIDMap import expected_slave_id
from ArtusAPI.communication.new_communication import ActuatorState, CommandType


class TestArtusAPIV2Mocked(unittest.TestCase):
    """Exercises ArtusAPI_V2 behavior with the communication layer mocked out."""

    def test_connect_opens_transport(self):
        """Verifies constructing the API opens the communication transport."""
        comm = MagicMock()
        api, comm = build_api(communication_mock=comm)
        comm.open_connection.assert_called()

    def test_disconnect_restores_signal(self):
        """Verifies disconnect() re-registers the original signal handler."""
        import ArtusAPI.artus_api_new as api_mod

        comm = MagicMock()
        with patched_artus_api_v2_constructor(comm):
            with patch.object(api_mod.signal, "signal") as sig_mock:
                api = api_mod.ArtusAPI_V2(
                    robot_type="artus_lite",
                    hand_type="left",
                    communication_method="RS485_RTU",
                    communication_channel_identifier="MOCK",
                )
                api.disconnect()
        self.assertTrue(sig_mock.called)

    def test_robot_type_hand_type_stored(self):
        """Verifies robot_type and hand_type constructor args are stored on the instance."""
        api, _ = build_api(robot_type="artus_talos", hand_type="right")
        self.assertEqual(api.robot_type, "artus_talos")
        self.assertEqual(api.hand_type, "right")

    def test_loads_config_file_before_building_handlers(self):
        """Verifies ArtusAPI_V2 reads robot_type/hand_type from the config file first."""
        import tempfile
        from pathlib import Path

        import ArtusAPI.artus_api_new as api_mod

        yaml_text = """
robots:
  left_hand_robot:
    robot_connected: true
    robot_type: artus_scorpion
    communication_method: RS485_RTU
    baudrate: 115200
    communication_channel_identifier: /dev/ttyUSB0
    hand_type: left
    start_robot: true
    reset_on_start: 0
    streaming_frequency: 20
    calibrate: false
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
        comm = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "robot_config.yaml"
            cfg_path.write_text(yaml_text, encoding="utf-8")
            with patched_artus_api_v2_constructor(comm):
                api = api_mod.ArtusAPI_V2(
                    config_file=str(cfg_path),
                    communication_channel_identifier="MOCK",
                )
        self.assertEqual(api.robot_type, "artus_scorpion")
        self.assertEqual(api.hand_type, "left")
        self.assertIsNotNone(api.config)
        self.assertIsNotNone(api.logger)
        self.assertFalse(api.get_robot_calibrate())
        self.assertTrue(api.get_robot_wake_up())
        self.assertFalse(api.get_robot_calibrate("right"))
        self.assertFalse(api.get_robot_wake_up("right"))

    def test_copy_default_config(self):
        """Verifies ArtusAPI_V2.copy_default_config writes the packaged YAML template."""
        import tempfile

        import ArtusAPI.artus_api_new as api_mod

        with tempfile.TemporaryDirectory() as tmp:
            dest = api_mod.ArtusAPI_V2.copy_default_config(tmp)
            self.assertTrue(dest.is_file())
            self.assertEqual(dest.name, "robot_config.yaml")
            self.assertGreater(dest.stat().st_size, 0)

    def test_set_control_type_valid(self):
        """Verifies set_control_type accepts a valid control type and updates state."""
        api, _ = build_api()
        self.assertTrue(api.set_control_type(3))
        self.assertEqual(api.control_type, 3)

    def test_set_control_type_invalid(self):
        """Verifies set_control_type rejects an unknown control type."""
        api, _ = build_api()
        self.assertFalse(api.set_control_type(99))

    def test_wake_up_sets_awake_when_ready(self):
        """Verifies wake_up() sets api.awake and sends the start command when the hand reports ready."""
        comm = MagicMock()
        comm.wait_for_ready.return_value = ActuatorState.ACTUATOR_IDLE.value
        api, comm = build_api(communication_mock=comm)
        api.wake_up(control_type=3)
        self.assertTrue(api.awake)
        comm.send_data.assert_called()

    def test_sleep_sends_command(self):
        """Verifies sleep() sends a command over the communication layer."""
        api, comm = build_api()
        api.sleep()
        comm.send_data.assert_called()

    def test_get_robot_status(self):
        """Verifies get_robot_status decodes the raw state byte into a state name and trajectory return value."""
        comm = MagicMock()
        comm._check_robot_state.return_value = 0x21
        api, comm = build_api(communication_mock=comm)
        st, tr = api.get_robot_status()
        self.assertEqual(st, ActuatorState(1).name)
        self.assertIsNotNone(tr)

    def test_new_communication_gets_slave_address_from_slave_id_map(self):
        """Verifies NewCommunication is constructed with the slave address resolved from SlaveIDMap."""
        import ArtusAPI.artus_api_new as api_mod

        comm = make_communication_mock()
        with patch.object(api_mod, "NewCommunication", autospec=True) as nc_cls:
            nc_cls.return_value = comm
            with patch.object(api_mod.time, "sleep"):
                with patch.object(api_mod.signal, "signal"):
                    api_mod.ArtusAPI_V2(
                        robot_type="artus_talos",
                        hand_type="right",
                        communication_method="RS485_RTU",
                        communication_channel_identifier="MOCK",
                    )
        nc_cls.assert_called_once()
        kwargs = nc_cls.call_args.kwargs
        self.assertEqual(
            kwargs["slave_address"],
            expected_slave_id("artus_talos", "right"),
        )

    def test_get_voltage(self):
        """Verifies get_voltage decodes a two-register IEEE 754 float feedback value."""
        comm = MagicMock()
        raw = struct.pack("<f", 12.5)
        w0, w1 = struct.unpack("<HH", raw)
        comm.receive_data.return_value = [w0, w1]
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        v = api.get_voltage()
        self.assertIsInstance(v, float)
        self.assertAlmostEqual(v, 12.5, places=4)

    def test_get_feedback_data_slave_id_path(self):
        """Verifies get_feedback_data returns the raw slave ID when reading the slave_id_reg register."""
        comm = MagicMock()
        comm.receive_data.return_value = 0x0003
        api, comm = build_api(robot_type="artus_lite_plus", hand_type="left", communication_mock=comm)
        api.awake = True
        reg = ModbusMap().modbus_reg_map["slave_id_reg"]
        sid = api.get_feedback_data(start_reg=reg)
        self.assertEqual(sid, 3)

    def test_helper_fill_dict_from_feedback(self):
        """Verifies helper_fill_dict_from_feedback_data maps feedback values to joint names in order."""
        api, _ = build_api()
        names = api._robot_handler.robot.joint_names
        data = list(range(len(names)))
        d = api.helper_fill_dict_from_feedback_data(data)
        for i, n in enumerate(names):
            self.assertEqual(d[n], data[i])

    def test_set_joint_angles_sends_position_command(self):
        """Verifies set_joint_angles sends a TARGET_COMMAND for a single joint target."""
        comm = MagicMock()
        api, comm = build_api()
        api.awake = True
        api.control_type = api.control_types["position"]
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            api.set_joint_angles({"thumb_spread": {"target_angle": 5}})
        comm.send_data.assert_called()
        args = comm.send_data.call_args[0]
        self.assertEqual(args[1], CommandType.TARGET_COMMAND.value)

    def test_set_joint_angles_by_list_delegates_to_set_joint_angles(self):
        """Verifies set_joint_angles_by_list builds an index-keyed target dict and delegates to set_joint_angles."""
        comm = MagicMock()
        api, comm = build_api()
        api.awake = True
        api.control_type = api.control_types["position"]
        api.last_time = 0.0
        with patch.object(api, "set_joint_angles", return_value=True) as m:
            api.set_joint_angles_by_list([0, 0], control_type=3)
        m.assert_called_once()
        call_kw = m.call_args[0][0]
        self.assertIn("0", call_kw)
        self.assertIn("target_angle", call_kw["0"])

    def test_set_home_position(self):
        """Verifies set_home_position sends a command over the communication layer."""
        comm = MagicMock()
        api, comm = build_api()
        api.awake = True
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            api.set_home_position()
        comm.send_data.assert_called()

    def test_get_joint_forces_returns_dict(self):
        """Verifies get_joint_forces returns one entry per joint."""
        comm = MagicMock()
        n = 16
        regs = [0] * (2 * n)
        comm.receive_data.return_value = regs
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        out = api.get_joint_forces()
        self.assertIsInstance(out, dict)
        self.assertEqual(len(out), n)

    def test_get_fingertip_forces_lite_plus(self):
        """Verifies get_fingertip_forces returns a dict for the artus_lite_plus hand."""
        comm = MagicMock()
        comm.receive_data.return_value = [0] * 30
        api, comm = build_api(robot_type="artus_lite_plus", hand_type="left", communication_mock=comm)
        api.awake = True
        out = api.get_fingertip_forces()
        self.assertIsInstance(out, dict)

    def test_get_avg_temperature(self):
        """Verifies get_avg_temperature returns the value read from the feedback register."""
        comm = MagicMock()
        comm.receive_data.return_value = [25]
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        t = api.get_avg_temperature()
        self.assertEqual(t, 25)

    def test_get_streamed_joint_angles_returns_none(self):
        """Verifies get_streamed_joint_angles returns None when no streaming data has been received."""
        api, _ = build_api()
        self.assertIsNone(api.get_streamed_joint_angles())

    def test_reset_with_joint_count(self):
        """Verifies reset() sends a command over the communication layer when given a joint count."""
        comm = MagicMock()
        comm.wait_for_ready.return_value = ActuatorState.ACTUATOR_IDLE.value
        api, comm = build_api(communication_mock=comm)
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            api.reset(joints=0)
        comm.send_data.assert_called()

    def test_calibrate(self):
        """Verifies calibrate() sends a command over the communication layer."""
        comm = MagicMock()
        comm.wait_for_ready.return_value = ActuatorState.ACTUATOR_READY.value
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        api.calibrate(joint=0)
        comm.send_data.assert_called()

    def test_get_hand_feedback_data_patched(self):
        """Verifies get_hand_feedback_data succeeds with get_feedback_data patched, for a lite hand."""
        api, _ = build_api(robot_type="artus_lite", hand_type="left")
        api.awake = True
        with patch.object(api, "get_feedback_data", return_value={}):
            self.assertTrue(api.get_hand_feedback_data())

    def test_get_config_writes_wifi_and_reads_ip(self):
        """Verifies get_config sends a trigger and payload write for each of SSID and password."""
        comm = MagicMock()
        comm.wait_for_ready.side_effect = [
            ActuatorState.ACTUATOR_CONFIG.value, ActuatorState.ACTUATOR_CONFIG_FINISH.value,
            ActuatorState.ACTUATOR_CONFIG.value, ActuatorState.ACTUATOR_CONFIG_FINISH.value,
        ]
        comm.receive_data.return_value = [(192 << 8) | 168, (1 << 8) | 50]
        api, comm = build_api(communication_mock=comm)

        api.get_config("SSID", "PASS")

        # 2 send_data calls per config value (trigger + payload) x 2 values
        self.assertEqual(comm.send_data.call_count, 4)
        payload_call_types = [c.args[1] for c in comm.send_data.call_args_list if len(c.args) > 1]
        self.assertTrue(all(t == CommandType.CONFIG_COMMAND.value for t in payload_call_types))
        self.assertEqual(len(payload_call_types), 2)

    def test_string_to_registers(self):
        """Verifies string_to_registers packs two chars per register and zero-pads odd-length strings."""
        api, _ = build_api()
        self.assertEqual(api.string_to_registers("AB"), [0x4142])
        # odd-length strings are zero-padded to fill the last register
        self.assertEqual(api.string_to_registers("A"), [0x4100])

    def test_get_hand_feedback_data_talos_with_force_patch(self):
        """Verifies get_hand_feedback_data succeeds for a talos hand with angles and fingertip forces patched."""
        api, _ = build_api(robot_type="artus_talos", hand_type="left")
        api.awake = True
        with patch.object(api, "get_feedback_data", return_value={}):
            with patch.object(api, "get_fingertip_forces", return_value={}):
                self.assertTrue(api.get_hand_feedback_data())

    def test_set_get_joint_angles_sends_fc17_request(self):
        """Verifies set_get_joint_angles issues one send_receive_data call with matching read/write args."""
        comm = MagicMock()
        n = 16
        comm.send_receive_data.return_value = [0] * 8  # position: 0.5 word/joint * 16 -> 8
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            out = api.set_get_joint_angles({"thumb_spread": {"target_angle": 5}})
        comm.send_receive_data.assert_called_once()
        read_start, read_count, write_start, values = comm.send_receive_data.call_args[0]
        self.assertEqual(read_start, ModbusMap().modbus_reg_map["feedback_position_start_reg"])
        self.assertEqual(read_count, 8)
        self.assertEqual(write_start, ModbusMap().modbus_reg_map["target_position_start_reg"])
        self.assertEqual(len(values), n // 2)
        self.assertIsInstance(out, dict)
        self.assertEqual(len(out), n)

    def test_set_get_joint_speeds_read_count(self):
        """Verifies set_get_joint_speeds requests one register per joint."""
        comm = MagicMock()
        comm.send_receive_data.return_value = [0] * 16  # velocity: 1 word/joint * 16
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            api.set_get_joint_speeds({"thumb_spread": {"target_velocity": 100}})
        _, read_count, _, _ = comm.send_receive_data.call_args[0]
        self.assertEqual(read_count, 16)

    def test_set_get_joint_forces_read_count(self):
        """Verifies set_get_joint_forces requests two registers per joint (float feedback)."""
        comm = MagicMock()
        comm.send_receive_data.return_value = [0] * 32  # force: 2 words/joint * 16
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            out = api.set_get_joint_forces({"thumb_spread": {"target_force": 1.5}})
        _, read_count, _, _ = comm.send_receive_data.call_args[0]
        self.assertEqual(read_count, 32)
        self.assertEqual(len(out), 16)

    def test_set_get_joint_angles_partial_dict_still_sends_full_command(self):
        """Verifies a single-joint update still packs/writes all joints (unset joints default to 0),
        matching the behavior of the existing write-only set_joint_angles path."""
        comm = MagicMock()
        comm.send_receive_data.return_value = [0] * 8
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            api.set_get_joint_angles({"thumb_spread": {"target_angle": 5}})
        _, _, _, values = comm.send_receive_data.call_args[0]
        # thumb_spread is joint index 0, packed high-byte in the first word alongside
        # thumb_flex (index 1, untouched -> defaults to 0, low byte of the same word).
        self.assertEqual(values[0] & 0xFF, 0)
        self.assertNotEqual(values[0] >> 8, 0)

    def test_set_get_joint_angles_no_valid_data_returns_false(self):
        """Verifies set_get_joint_angles returns False and does not touch the wire when the dict has no usable data."""
        comm = MagicMock()
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        self.assertFalse(api.set_get_joint_angles({}))
        comm.send_receive_data.assert_not_called()

    def test_set_get_joint_angles_not_awake_returns_none(self):
        """Verifies set_get_joint_angles short-circuits and does not touch the wire when the hand is not awake."""
        comm = MagicMock()
        api, comm = build_api(communication_mock=comm)
        with patch.object(api, "_check_awake", return_value=False):
            self.assertIsNone(api.set_get_joint_angles({"thumb_spread": {"target_angle": 5}}))
        comm.send_receive_data.assert_not_called()

    # --- unified feedback read path (get_feedback_data) ---

    def test_feedback_register_count_scalar_fields(self):
        """Verifies whole-hand scalar fields read a fixed count, not one sample per joint."""
        api, _ = build_api(robot_type="artus_lite", hand_type="left")
        self.assertEqual(api._feedback_register_count("feedback_voltage_start_reg"), 2)
        self.assertEqual(api._feedback_register_count("feedback_avg_temperature_start_reg"), 1)
        self.assertEqual(api._feedback_register_count("slave_id_reg"), 1)

    def test_feedback_register_count_per_joint_fields(self):
        """Verifies per-joint fields scale their read count by the multiplier and joint count."""
        api, _ = build_api(robot_type="artus_lite", hand_type="left")
        joints = api._robot_handler.robot.number_of_joints
        self.assertEqual(api._feedback_register_count("feedback_velocity_start_reg"), joints)
        self.assertEqual(api._feedback_register_count("feedback_force_start_reg"), joints * 2)

    def test_feedback_register_count_fingertip_uses_sensor_count(self):
        """Verifies fingertip forces size the read from the robot's sensor count, not a hardcoded 5."""
        api, _ = build_api(robot_type="artus_lite_plus", hand_type="left")
        sensors = len(api._robot_handler.robot.force_sensors)
        self.assertEqual(
            api._feedback_register_count(ModbusMap.FINGERTIP_FEEDBACK_KEY),
            sensors * ModbusMap.FINGERTIP_AXES * 2,
        )

    def test_get_avg_temperature_reads_one_register(self):
        """Verifies average temperature reads a single register and returns a scalar, not a per-joint dict."""
        comm = MagicMock()
        comm.receive_data.return_value = [37]
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        t = api.get_avg_temperature()
        self.assertEqual(t, 37)
        self.assertEqual(comm.receive_data.call_args.kwargs["amount_dat"], 1)

    def test_get_feedback_data_by_key_matches_getter(self):
        """Verifies get_feedback_data accepts a ModbusMap key name as well as a register address."""
        comm = MagicMock()
        comm.receive_data.return_value = [37]
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        by_key = api.get_feedback_data("feedback_avg_temperature_start_reg")
        by_addr = api.get_feedback_data(
            ModbusMap().modbus_reg_map["feedback_avg_temperature_start_reg"]
        )
        self.assertEqual(by_key, by_addr)

    def test_get_feedback_data_unknown_register_raises(self):
        """Verifies an unrecognized register address or key raises ValueError rather than KeyError."""
        api, _ = build_api()
        api.awake = True
        with self.assertRaises(ValueError):
            api.get_feedback_data(start_reg=9999)
        with self.assertRaises(ValueError):
            api.get_feedback_data(start_reg="not_a_register")

    def test_get_feedback_data_fingertip_returns_per_finger_dict(self):
        """Verifies the fingertip key returns a per-finger x/y/z dict through the generic path."""
        api, comm = build_api(robot_type="artus_lite_plus", hand_type="left")
        sensors = list(api._robot_handler.robot.force_sensors)
        words = []
        for i in range(len(sensors) * ModbusMap.FINGERTIP_AXES):
            words.extend(struct.unpack("<HH", struct.pack("<f", float(i))))
        comm.receive_data.return_value = words
        api.awake = True
        out = api.get_feedback_data(ModbusMap.FINGERTIP_FEEDBACK_KEY)
        self.assertEqual(set(out), set(sensors))
        self.assertEqual(out[sensors[0]], {"x": 0.0, "y": 1.0, "z": 2.0})

    def test_get_hand_feedback_data_covers_every_available_type(self):
        """Verifies get_hand_feedback_data issues one read per available feedback type."""
        api, comm = build_api(robot_type="artus_lite_plus", hand_type="left")
        api.awake = True
        with patch.object(api, "get_feedback_data") as gfd:
            self.assertTrue(api.get_hand_feedback_data())
        called = [c.args[0] for c in gfd.call_args_list]
        self.assertEqual(called, list(api._robot_handler.robot.available_feedback_types))

    def test_get_joint_angles_alias_delegates(self):
        """Verifies the deprecated get_joint_angles alias forwards to get_feedback_data."""
        api, _ = build_api()
        api.awake = True
        reg = ModbusMap().modbus_reg_map["feedback_velocity_start_reg"]
        with patch.object(api, "get_feedback_data", return_value={"ok": 1}) as gfd:
            self.assertEqual(api.get_joint_angles(reg), {"ok": 1})
        gfd.assert_called_once_with(reg)

    def test_get_joint_angles_alias_defaults_to_position(self):
        """Verifies the alias keeps the old default of reading feedback position."""
        api, _ = build_api()
        api.awake = True
        with patch.object(api, "get_feedback_data", return_value={}) as gfd:
            api.get_joint_angles()
        gfd.assert_called_once_with(
            ModbusMap().modbus_reg_map["feedback_position_start_reg"]
        )

    def test_get_joint_angles_alias_warns_once(self):
        """Verifies the deprecation notice is logged once per instance, not per call."""
        api, _ = build_api()
        api.awake = True
        with patch.object(api, "get_feedback_data", return_value={}):
            with patch.object(api.logger, "warning") as warn:
                api.get_joint_angles()
                api.get_joint_angles()
        warn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
