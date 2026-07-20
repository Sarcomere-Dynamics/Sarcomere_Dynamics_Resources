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

    def test_get_joint_angles_slave_id_path(self):
        """Verifies get_joint_angles returns the raw slave ID when reading the slave_id_reg register."""
        comm = MagicMock()
        comm.receive_data.return_value = 0x0003
        api, comm = build_api(robot_type="artus_lite_plus", hand_type="left", communication_mock=comm)
        api.awake = True
        reg = ModbusMap().modbus_reg_map["slave_id_reg"]
        sid = api.get_joint_angles(start_reg=reg)
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
        """Verifies get_hand_feedback_data succeeds with get_joint_angles patched, for a lite hand."""
        api, _ = build_api(robot_type="artus_lite", hand_type="left")
        api.awake = True
        with patch.object(api, "get_joint_angles", return_value={}):
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
        with patch.object(api, "get_joint_angles", return_value={}):
            with patch.object(api, "get_fingertip_forces", return_value={}):
                self.assertTrue(api.get_hand_feedback_data())


if __name__ == "__main__":
    unittest.main()
