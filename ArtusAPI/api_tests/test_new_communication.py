"""Tests for NewCommunication with RS485_RTU mocked (no serial port)."""

import unittest
from unittest.mock import MagicMock, patch

from ArtusAPI.communication.new_communication import NewCommunication, ActuatorState
from ArtusAPI.common.ModbusMap import ModbusMap, TrajectoryReturn


class TestNewCommunicationMocked(unittest.TestCase):
    """Verifies NewCommunication delegates to a mocked RS485_RTU transport."""

    def _make_nc(self, mock_inst: MagicMock) -> NewCommunication:
        """Builds a NewCommunication with RS485_RTU patched to return the given mock.

        Args:
            mock_inst: Mock to substitute for the real RS485_RTU instance.

        Returns:
            A NewCommunication instance wired to the mock transport.
        """
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
        """Verifies open_connection/close_connection delegate to the underlying transport."""
        inst = MagicMock()
        nc = self._make_nc(inst)
        nc.open_connection()
        inst.open.assert_called_once()
        nc.close_connection()
        inst.close.assert_called_once()

    def test_send_data_delegates(self):
        """Verifies send_data delegates to the transport's send method."""
        inst = MagicMock()
        nc = self._make_nc(inst)
        nc.open_connection()
        nc.send_data([1, 2, 3], command_type=16)
        inst.send.assert_called_once()

    def test_receive_data_delegates(self):
        """Verifies receive_data delegates to the transport's receive method and returns its value."""
        inst = MagicMock()
        inst.receive.return_value = 0x0102
        nc = self._make_nc(inst)
        nc.open_connection()
        ret = nc.receive_data(amount_dat=1, start=ModbusMap().modbus_reg_map["feedback_register"])
        self.assertEqual(ret, 0x0102)
        inst.receive.assert_called_once()

    def test_check_robot_state_low_nibble(self):
        """Verifies _check_robot_state extracts the low nibble of the raw status word."""
        inst = MagicMock()
        inst.receive.return_value = 0x0506
        nc = self._make_nc(inst)
        nc.open_connection()
        low = nc._check_robot_state()
        self.assertEqual(low, 0x06)

    def test_unknown_method_raises(self):
        """Verifies constructing NewCommunication with an unsupported communication method raises ValueError."""
        with self.assertRaises(ValueError):
            NewCommunication(communication_method="NOT_A_METHOD")

    def test_wait_for_ready_decodes_trajectory_state(self):
        """Verifies wait_for_ready splits the status word into actuator state and trajectory return, logging the latter."""
        # low nibble 0x1 = ACTUATOR_IDLE, high nibble 0x2 = TRAJECTORY_COMPLETE
        inst = MagicMock()
        inst.receive.return_value = 0x21
        nc = self._make_nc(inst)
        nc.open_connection()
        with patch.object(nc.logger, "info") as log_info:
            result = nc.wait_for_ready(acceptable_state=ActuatorState.ACTUATOR_IDLE.value)
        self.assertEqual(result, ActuatorState.ACTUATOR_IDLE.value)
        logged = " ".join(str(c.args[0]) for c in log_info.call_args_list)
        self.assertIn(TrajectoryReturn.TRAJECTORY_COMPLETE.name, logged)


if __name__ == "__main__":
    unittest.main()
