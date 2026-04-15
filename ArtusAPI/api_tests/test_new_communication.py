"""Tests for NewCommunication with RS485_RTU mocked (no serial port)."""

import unittest
from unittest.mock import MagicMock, patch

from ArtusAPI.communication.new_communication import NewCommunication, ActuatorState
from ArtusAPI.common.ModbusMap import ModbusMap


class TestNewCommunicationMocked(unittest.TestCase):
    def _make_nc(self, mock_inst: MagicMock) -> NewCommunication:
        with patch(
            "ArtusAPI.communication.new_communication.RS485_RTU",
            return_value=mock_inst,
        ):
            nc = NewCommunication(
                port="MOCK",
                baudrate=115200,
                communication_method="RS485_RTU",
            )
        return nc

    def test_open_close(self):
        inst = MagicMock()
        nc = self._make_nc(inst)
        nc.open_connection()
        inst.open.assert_called_once()
        nc.close_connection()
        inst.close.assert_called_once()

    def test_send_data_delegates(self):
        inst = MagicMock()
        nc = self._make_nc(inst)
        nc.open_connection()
        nc.send_data([1, 2, 3], command_type=16)
        inst.send.assert_called_once()

    def test_receive_data_delegates(self):
        inst = MagicMock()
        inst.receive.return_value = 0x0102
        nc = self._make_nc(inst)
        nc.open_connection()
        ret = nc.receive_data(amount_dat=1, start=ModbusMap().modbus_reg_map["feedback_register"])
        self.assertEqual(ret, 0x0102)
        inst.receive.assert_called_once()

    def test_check_robot_state_low_nibble(self):
        inst = MagicMock()
        inst.receive.return_value = 0x0506
        nc = self._make_nc(inst)
        nc.open_connection()
        low = nc._check_robot_state()
        self.assertEqual(low, 0x06)

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            NewCommunication(communication_method="NOT_A_METHOD")


if __name__ == "__main__":
    unittest.main()
