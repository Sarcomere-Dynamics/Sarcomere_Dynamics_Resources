"""Master status + per-motor diagnostics registers (700-812), no hardware.

Register values mirror the firmware unit tests (bldc_c_master
test_host_communication_modbus.cpp SendData_ReadFaultRecord /
SendData_ReadPerMotorDiagnostics).
"""

from __future__ import annotations

import logging
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from artusapi.artusapi import ArtusAPI
from artusapi.commands.command_handler import CommandHandler
from artusapi.common import protocol_codes as pc
from artusapi.common.modbus_map import ModbusMap
from artusapi.robot.artus_dex.artus_dex import ArtusDex


def make_api(robot, register_words: dict[int, list[int]]):
    """ArtusAPI wired to a fake bus: reads at an address return the given words."""
    api = ArtusAPI.__new__(ArtusAPI)
    api.logger = logging.getLogger("test_status_registers")
    api.robot_type = "artus_dex"
    api._robot_handler = MagicMock()
    api._robot_handler.robot = robot
    api._command_handler = CommandHandler(num_joints=robot.number_of_joints, logger=api.logger)
    comm = MagicMock()

    def receive_data(amount_dat, start):
        words = list(register_words.get(start, []))
        return (words + [0] * amount_dat)[:amount_dat]

    comm.receive_data.side_effect = receive_data
    api._communication_handler = comm
    return api, comm


class TestProtocolCodes(unittest.TestCase):
    def test_slave_error_without_drv_fault_is_all_flags(self):
        d = pc.decode_slave_error(0x02001000)
        self.assertEqual(d["flags"], ["CURRENT_LIMIT_VIOLATION", "ESTOP_REQUESTED"])
        self.assertIsNone(d["drv_fault_status"])

    def test_slave_error_with_drv_fault_splits_upper_bits(self):
        d = pc.decode_slave_error(0x00010020)
        self.assertEqual(d["flags"], ["DRV_FAULT"])
        self.assertEqual(d["drv_fault_status"], 0x0001)

    def test_flag_names_and_unknown_bits(self):
        self.assertEqual(pc.flag_names(0x0006), ["STROKE_FAILED", "COMM_LOST"])
        self.assertEqual(pc.flag_names(0x0100), ["0x0100"])

    def test_enum_name_unknown(self):
        self.assertEqual(pc.enum_name(pc.MasterFault, 99), "UNKNOWN(99)")
        self.assertEqual(pc.enum_name(pc.MasterFault, 3), "STROKE_CAL_FAILED")


class TestStatusRegisterMap(unittest.TestCase):
    def test_addresses(self):
        m = ModbusMap().modbus_reg_map
        self.assertEqual(m["feedback_fault_reg"], 700)
        self.assertEqual(m["feedback_motor_error_reg"], 710)
        self.assertEqual(m["feedback_motor_status_reg"], 760)
        self.assertEqual(m["feedback_motor_flags_reg"], 790)

    def test_counts_use_motor_count_not_joint_count(self):
        mm = ModbusMap()
        self.assertEqual(mm.feedback_register_count("feedback_fault_reg", 18), 5)
        self.assertEqual(mm.feedback_register_count("feedback_motor_error_reg", 18, 0, 23), 46)
        self.assertEqual(mm.feedback_register_count("feedback_motor_status_reg", 18, 0, 23), 23)
        self.assertEqual(mm.feedback_register_count("feedback_motor_flags_reg", 18, 0, 23), 23)

    def test_decoding_keeps_codes_unsigned(self):
        ch = CommandHandler(num_joints=18, logger=logging.getLogger("t"))
        # 0x8F01 would come back negative through the signed int16 path
        self.assertEqual(ch.get_decoded_feedback_data([0x8F01], "feedback_motor_flags_reg"), [0x8F01])
        self.assertEqual(ch.get_decoded_feedback_data([0x1208], "feedback_motor_status_reg"), [0x1208])
        self.assertEqual(
            ch.get_decoded_feedback_data([0x5678, 0x1234], "feedback_motor_error_reg"), [0x12345678]
        )


class TestStatusGetters(unittest.TestCase):
    def setUp(self):
        self.dex = ArtusDex()
        self.assertEqual(len(self.dex.motor_names), 23)

    def test_fault_report_decodes_record(self):
        # STROKE_CAL_FAILED in CALIBRATING_STROKE on motor 0 (thumb_d3_1),
        # NO_ENDPOINT_FOUND, error 0x40000020, last command CALIBRATE accepted
        words = [(3 << 8) | 3, (0 << 8) | 7, 0x0020, 0x4000, (0x0D << 8) | 1]
        api, comm = make_api(self.dex, {700: words})
        f = api.get_fault_report()
        comm.receive_data.assert_called_with(amount_dat=5, start=700)
        self.assertEqual(f["reason"], "STROKE_CAL_FAILED")
        self.assertEqual(f["state"], "ACTUATOR_CALIBRATING_STROKE")
        self.assertEqual(f["motor_index"], 0)
        self.assertEqual(f["motor_name"], "thumb_d3_1")
        self.assertEqual(f["procedure_result"], "ENDPOINT_SEARCH_NO_ENDPOINT_FOUND")
        self.assertEqual(f["error_report"], 0x40000020)
        self.assertEqual(f["errors"], ["DRV_FAULT"])          # DRV_FAULT: upper bits are status
        self.assertEqual(f["drv_fault_status"], 0x4000)
        self.assertEqual(f["last_command"], "CALIBRATE")
        self.assertEqual(f["last_command_result"], "ACCEPTED")

    def test_fault_report_no_motor(self):
        words = [(7 << 8) | 5, (0xFF << 8) | 0, 0, 0, (0x18 << 8) | 1]
        api, _ = make_api(self.dex, {700: words})
        f = api.get_fault_report()
        self.assertEqual(f["reason"], "ESTOP")
        self.assertIsNone(f["motor_index"])
        self.assertIsNone(f["motor_name"])

    def test_last_command_result(self):
        api, _ = make_api(self.dex, {700: [0, 0, 0, 0, (0x0D << 8) | 2]})
        r = api.get_last_command_result()
        self.assertEqual(r["command"], "CALIBRATE")
        self.assertEqual(r["result"], "REJECTED_STATE")

    def test_motor_registers_keyed_by_motor_name(self):
        err = [0] * 46
        err[2 * 22], err[2 * 22 + 1] = 0x5678, 0x1234          # pinky_ext
        status = [0] * 23
        status[22] = (18 << 8) | 8                              # MODE_ERROR, DRV_ERROR
        flags = [0] * 23
        flags[0] = 0x0002                                       # thumb_d3_1 STROKE_FAILED
        api, comm = make_api(self.dex, {710: err, 760: status, 790: flags})

        e = api.get_motor_error_report()
        comm.receive_data.assert_called_with(amount_dat=46, start=710)
        self.assertEqual(e["pinky_ext"], 0x12345678)
        self.assertEqual(e["thumb_d3_1"], 0)

        s = api.get_motor_status()
        self.assertEqual(s["pinky_ext"], {"axis_state": "MODE_ERROR", "procedure_result": "DRV_ERROR"})

        fl = api.get_motor_flags()
        self.assertEqual(fl["thumb_d3_1"], ["STROKE_FAILED"])
        self.assertEqual(fl["index_d2"], [])

        diag = api.get_motor_diagnostics()
        self.assertEqual(set(diag), {"thumb_d3_1", "pinky_ext"})
        self.assertEqual(diag["thumb_d3_1"]["flags"], ["STROKE_FAILED"])
        self.assertEqual(diag["pinky_ext"]["error_report"], "0x12345678")
        self.assertEqual(len(api.get_motor_diagnostics(only_problems=False)), 23)

    def test_read_by_address(self):
        api, _ = make_api(self.dex, {790: [0x0008] + [0] * 22})
        self.assertEqual(api.get_feedback_data(790)["thumb_d3_1"], ["NO_RESPONSE"])

    def test_robot_without_motor_map_returns_none(self):
        robot = SimpleNamespace(number_of_joints=6, motor_names=None, force_sensors=None,
                                joint_names=[f"j{i}" for i in range(6)])
        api, comm = make_api(robot, {})
        self.assertIsNone(api.get_motor_flags())
        comm.receive_data.assert_not_called()


if __name__ == "__main__":
    unittest.main()
