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
    def test_connect_opens_transport(self):
        comm = MagicMock()
        api, comm = build_api(communication_mock=comm)
        comm.open_connection.assert_called()

    def test_disconnect_restores_signal(self):
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
        api, _ = build_api(robot_type="artus_talos", hand_type="right")
        self.assertEqual(api.robot_type, "artus_talos")
        self.assertEqual(api.hand_type, "right")

    def test_set_control_type_valid(self):
        api, _ = build_api()
        self.assertTrue(api.set_control_type(3))
        self.assertEqual(api.control_type, 3)

    def test_set_control_type_invalid(self):
        api, _ = build_api()
        self.assertFalse(api.set_control_type(99))

    def test_wake_up_sets_awake_when_ready(self):
        comm = MagicMock()
        comm.wait_for_ready.return_value = ActuatorState.ACTUATOR_IDLE.value
        api, comm = build_api(communication_mock=comm)
        api.wake_up(control_type=3)
        self.assertTrue(api.awake)
        comm.send_data.assert_called()

    def test_sleep_sends_command(self):
        api, comm = build_api()
        api.sleep()
        comm.send_data.assert_called()

    def test_get_robot_status(self):
        comm = MagicMock()
        comm._check_robot_state.return_value = 0x21
        api, comm = build_api(communication_mock=comm)
        st, tr = api.get_robot_status()
        self.assertEqual(st, ActuatorState(1).name)
        self.assertIsNotNone(tr)

    def test_new_communication_gets_slave_address_from_slave_id_map(self):
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
        comm = MagicMock()
        comm.receive_data.return_value = 0x0003
        api, comm = build_api(robot_type="artus_lite_plus", hand_type="left", communication_mock=comm)
        api.awake = True
        reg = ModbusMap().modbus_reg_map["slave_id_reg"]
        sid = api.get_joint_angles(start_reg=reg)
        self.assertEqual(sid, 3)

    def test_helper_fill_dict_from_feedback(self):
        api, _ = build_api()
        names = api._robot_handler.robot.joint_names
        data = list(range(len(names)))
        d = api.helper_fill_dict_from_feedback_data(data)
        for i, n in enumerate(names):
            self.assertEqual(d[n], data[i])

    def test_set_joint_angles_sends_position_command(self):
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
        comm = MagicMock()
        api, comm = build_api()
        api.awake = True
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            api.set_home_position()
        comm.send_data.assert_called()

    def test_get_joint_forces_returns_dict(self):
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
        comm = MagicMock()
        comm.receive_data.return_value = [0] * 30
        api, comm = build_api(robot_type="artus_lite_plus", hand_type="left", communication_mock=comm)
        api.awake = True
        out = api.get_fingertip_forces()
        self.assertIsInstance(out, dict)

    def test_get_avg_temperature(self):
        comm = MagicMock()
        comm.receive_data.return_value = [25]
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        t = api.get_avg_temperature()
        self.assertEqual(t, 25)

    def test_get_streamed_joint_angles_returns_none(self):
        api, _ = build_api()
        self.assertIsNone(api.get_streamed_joint_angles())

    def test_reset_with_joint_count(self):
        comm = MagicMock()
        comm.wait_for_ready.return_value = ActuatorState.ACTUATOR_IDLE.value
        api, comm = build_api(communication_mock=comm)
        api.last_time = 0.0
        with patch("ArtusAPI.artus_api_new.time.perf_counter", return_value=10.0):
            api.reset(joints=0)
        comm.send_data.assert_called()

    def test_calibrate(self):
        comm = MagicMock()
        comm.wait_for_ready.return_value = ActuatorState.ACTUATOR_READY.value
        api, comm = build_api(communication_mock=comm)
        api.awake = True
        api.calibrate(joint=0)
        comm.send_data.assert_called()

    def test_get_hand_feedback_data_patched(self):
        api, _ = build_api(robot_type="artus_lite", hand_type="left")
        api.awake = True
        with patch.object(api, "get_joint_angles", return_value={}):
            self.assertTrue(api.get_hand_feedback_data())

    def test_get_hand_feedback_data_talos_with_force_patch(self):
        api, _ = build_api(robot_type="artus_talos", hand_type="left")
        api.awake = True
        with patch.object(api, "get_joint_angles", return_value={}):
            with patch.object(api, "get_fingertip_forces", return_value={}):
                self.assertTrue(api.get_hand_feedback_data())


if __name__ == "__main__":
    unittest.main()
