"""Packet parity tests for the minimalmodbus -> pymodbus RTU migration (no hardware).

Two layers of verification:

1. Call-level: both RS485_RTU implementations hand the same function code,
   register address and payload values to their Modbus library for every
   CommandType and for reads.

2. Wire-level: the raw RTU frame minimalmodbus writes to the serial port is
   byte-identical to the frame pymodbus builds for the same operation
   (same slave, function code, address, values -> same bytes incl. CRC).
"""

import unittest
from unittest.mock import MagicMock, patch

from pymodbus.framer.rtu import FramerRTU
from pymodbus.pdu import DecodePDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    WriteMultipleRegistersRequest,
    WriteSingleRegisterRequest,
)

from ArtusAPI.common.ModbusMap import CommandType

try:
    import minimalmodbus  # noqa: F401  archived baseline, no longer a runtime dep
    HAS_MINIMALMODBUS = True
except ImportError:
    HAS_MINIMALMODBUS = False

needs_minimalmodbus = unittest.skipUnless(
    HAS_MINIMALMODBUS, "minimalmodbus not installed (baseline for parity tests)"
)

SLAVE_ID = 5

# (name, data list as produced by NewCommands, CommandType)
SEND_CASES = [
    ("setup_two_values", [0x0B, 0x03], CommandType.SETUP_COMMANDS.value),
    ("setup_single_value", [0x0F], CommandType.SETUP_COMMANDS.value),
    ("target_positions", [1, 0x1E3C, 0x2D00, 0x7F80], CommandType.TARGET_COMMAND.value),
    ("target_forces", [50, 0x0000, 0x3FA0, 0x0000, 0x4020], CommandType.TARGET_COMMAND.value),
    ("target_velocities", [150, 100, 200, 0x7FFF], CommandType.TARGET_COMMAND.value),
    ("firmware", [0x11, 0xFF], CommandType.FIRMWARE_COMMAND.value),
]

# (name, [start_register, count])
RECEIVE_CASES = [
    ("feedback_register", [200, 1]),
    ("feedback_positions", [201, 10]),
]


def expected_library_call(data, command):
    """The (kind, address, payload) every backend must pass to its Modbus library."""
    if command == CommandType.SETUP_COMMANDS.value:
        if len(data) != 1:
            value = ((int(data[1]) & 0xFF) << 8) | (int(data[0]) & 0xFF)
        else:
            value = data[0]
        return ("write_single", 0, value)
    if command == CommandType.TARGET_COMMAND.value:
        return ("write_multiple", data[0], list(data[1:]))
    if command == CommandType.FIRMWARE_COMMAND.value:
        return ("write_multiple", 0, list(data))
    raise ValueError(command)


def build_pymodbus_frame(kind, address, payload, count=None):
    """Raw RTU frame pymodbus would put on the wire for this operation."""
    framer = FramerRTU(DecodePDU(False))
    if kind == "write_single":
        pdu = WriteSingleRegisterRequest(
            address=address, registers=[payload], dev_id=SLAVE_ID, transaction_id=0
        )
    elif kind == "write_multiple":
        pdu = WriteMultipleRegistersRequest(
            address=address, registers=payload, dev_id=SLAVE_ID, transaction_id=0
        )
    elif kind == "read_holding":
        pdu = ReadHoldingRegistersRequest(
            address=address, count=count, dev_id=SLAVE_ID, transaction_id=0
        )
    else:
        raise ValueError(kind)
    return framer.buildFrame(pdu)


class MinimalmodbusCallCapture:
    """Run the archived minimalmodbus RS485_RTU against a mocked Instrument."""

    def __init__(self):
        """Builds the archived minimalmodbus RS485_RTU with its Instrument mocked out."""
        from ArtusAPI.communication.RS485_RTU.rs485_rtu_minimalmodbus import RS485_RTU

        self.instrument = MagicMock()
        with patch(
            "ArtusAPI.communication.RS485_RTU.rs485_rtu_minimalmodbus.minimalmodbus.Instrument",
            return_value=self.instrument,
        ):
            self.rtu = RS485_RTU(port="MOCK", baudrate=115200, slave_address=SLAVE_ID)
            self.rtu.open()

    def send(self, data, command):
        """Sends data through the RTU backend and captures the resulting library call.

        Args:
            data: Command payload as produced by NewCommands.
            command: CommandType value identifying the operation.

        Returns:
            A (kind, address, payload) tuple describing the minimalmodbus call made.
        """
        self.instrument.reset_mock()
        self.rtu.send(data, command, max_retries=1)
        if self.instrument.write_register.called:
            kwargs = self.instrument.write_register.call_args.kwargs
            return ("write_single", kwargs["registeraddress"], kwargs["value"])
        kwargs = self.instrument.write_registers.call_args.kwargs
        return ("write_multiple", kwargs["registeraddress"], list(kwargs["values"]))

    def receive(self, data, return_value):
        """Reads data through the RTU backend and captures the resulting library call.

        Args:
            data: [start_register, count] pair describing the read.
            return_value: Value(s) the mocked Instrument should return.

        Returns:
            A tuple of ((kind, address, count), decoded return value).
        """
        self.instrument.reset_mock()
        # minimalmodbus read_registers always returns a list
        self.instrument.read_registers.return_value = (
            return_value if isinstance(return_value, list) else [return_value]
        )
        ret = self.rtu.receive(data, max_retries=1)
        kwargs = self.instrument.read_registers.call_args.kwargs
        return ("read_holding", kwargs["registeraddress"], kwargs["number_of_registers"]), ret


class PymodbusCallCapture:
    """Run the pymodbus RS485_RTU against a mocked ModbusSerialClient."""

    def __init__(self):
        """Builds the pymodbus-backed RS485_RTU with its ModbusSerialClient mocked out."""
        from ArtusAPI.communication.RS485_RTU.rs485_rtu import RS485_RTU

        self.client = MagicMock()
        self.client.connect.return_value = True
        ok = MagicMock()
        ok.isError.return_value = False
        self.client.write_register.return_value = ok
        self.client.write_registers.return_value = ok
        with patch(
            "ArtusAPI.communication.RS485_RTU.rs485_rtu.ModbusSerialClient",
            return_value=self.client,
        ):
            self.rtu = RS485_RTU(port="MOCK", baudrate=115200, slave_address=SLAVE_ID)
            self.rtu.open()

    def send(self, data, command):
        """Sends data through the RTU backend and captures the resulting library call.

        Args:
            data: Command payload as produced by NewCommands.
            command: CommandType value identifying the operation.

        Returns:
            A (kind, address, payload) tuple describing the pymodbus call made.
        """
        self.client.reset_mock()
        self.rtu.send(data, command, max_retries=1)
        if self.client.write_register.called:
            args, kwargs = self.client.write_register.call_args
            self.assert_slave(kwargs)
            return ("write_single", args[0], args[1])
        args, kwargs = self.client.write_registers.call_args
        self.assert_slave(kwargs)
        return ("write_multiple", args[0], list(args[1]))

    def receive(self, data, return_value):
        """Reads data through the RTU backend and captures the resulting library call.

        Args:
            data: [start_register, count] pair describing the read.
            return_value: Value(s) the mocked client should return.

        Returns:
            A tuple of ((kind, address, count), decoded return value).
        """
        self.client.reset_mock()
        result = MagicMock()
        result.isError.return_value = False
        result.registers = return_value if isinstance(return_value, list) else [return_value]
        self.client.read_holding_registers.return_value = result
        ret = self.rtu.receive(data, max_retries=1)
        args, kwargs = self.client.read_holding_registers.call_args
        self.assert_slave(kwargs)
        return ("read_holding", args[0], kwargs["count"]), ret

    @staticmethod
    def assert_slave(kwargs):
        """Asserts the call was addressed to the expected slave/device ID.

        Args:
            kwargs: Keyword arguments captured from the mocked client call.
        """
        assert kwargs.get("device_id") == SLAVE_ID, f"missing/wrong device_id: {kwargs}"


@needs_minimalmodbus
class TestCurrentImplCalls(unittest.TestCase):
    """Baseline: the archived minimalmodbus backend issues the expected library calls."""

    def setUp(self):
        """Creates a MinimalmodbusCallCapture for each test."""
        self.capture = MinimalmodbusCallCapture()

    def test_send_cases(self):
        """Verifies each SEND_CASES entry produces the expected minimalmodbus library call."""
        for name, data, command in SEND_CASES:
            with self.subTest(name=name):
                self.assertEqual(
                    self.capture.send(data, command),
                    expected_library_call(data, command),
                )

    def test_receive_single_register_returns_int(self):
        """Verifies reading a single register returns an int via minimalmodbus."""
        call, ret = self.capture.receive([200, 1], return_value=0x0506)
        self.assertEqual(call, ("read_holding", 200, 1))
        self.assertEqual(ret, 0x0506)

    def test_receive_multiple_registers_returns_list(self):
        """Verifies reading multiple registers returns a list via minimalmodbus."""
        call, ret = self.capture.receive([201, 10], return_value=list(range(10)))
        self.assertEqual(call, ("read_holding", 201, 10))
        self.assertEqual(ret, list(range(10)))


class TestPymodbusImplCalls(unittest.TestCase):
    """The new pymodbus backend issues the same library calls."""

    def setUp(self):
        """Creates a PymodbusCallCapture for each test."""
        self.capture = PymodbusCallCapture()

    def test_send_cases(self):
        """Verifies each SEND_CASES entry produces the expected pymodbus library call."""
        for name, data, command in SEND_CASES:
            with self.subTest(name=name):
                self.assertEqual(
                    self.capture.send(data, command),
                    expected_library_call(data, command),
                )

    def test_receive_single_register_returns_int(self):
        """Verifies reading a single register returns an int via pymodbus."""
        call, ret = self.capture.receive([200, 1], return_value=0x0506)
        self.assertEqual(call, ("read_holding", 200, 1))
        self.assertEqual(ret, 0x0506)

    def test_receive_multiple_registers_returns_list(self):
        """Verifies reading multiple registers returns a list via pymodbus."""
        call, ret = self.capture.receive([201, 10], return_value=list(range(10)))
        self.assertEqual(call, ("read_holding", 201, 10))
        self.assertEqual(ret, list(range(10)))

    def test_config_command(self):
        """Verifies CONFIG_COMMAND, added after the minimalmodbus migration, issues a write_multiple call."""
        # CONFIG_COMMAND has no minimalmodbus-era baseline (added after the
        # migration, for onboard WiFi config writes) - not part of SEND_CASES.
        call = self.capture.send([2, 0x4142, 0x4300], CommandType.CONFIG_COMMAND.value)
        self.assertEqual(call, ("write_multiple", 0, [2, 0x4142, 0x4300]))


@needs_minimalmodbus
class TestCallParity(unittest.TestCase):
    """Both backends produce identical (kind, address, payload) for every case."""

    def test_send_parity(self):
        """Verifies both backends produce identical send calls for every SEND_CASES entry."""
        old = MinimalmodbusCallCapture()
        new = PymodbusCallCapture()
        for name, data, command in SEND_CASES:
            with self.subTest(name=name):
                self.assertEqual(old.send(data, command), new.send(data, command))

    def test_receive_parity(self):
        """Verifies both backends produce identical receive calls for every RECEIVE_CASES entry."""
        old = MinimalmodbusCallCapture()
        new = PymodbusCallCapture()
        for name, data in RECEIVE_CASES:
            ret_val = list(range(data[1])) if data[1] > 1 else 0x0102
            with self.subTest(name=name):
                self.assertEqual(
                    old.receive(data, ret_val), new.receive(data, ret_val)
                )


@needs_minimalmodbus
class TestWireFrameParity(unittest.TestCase):
    """The bytes minimalmodbus writes to the serial port match pymodbus framing.

    minimalmodbus runs against a mocked serial port: we capture the request
    frame it writes, let the (empty) response raise NoResponseError, and
    compare the captured bytes against the frame pymodbus builds for the
    same operation. CRC included.
    """

    def _capture_minimalmodbus_frame(self, run):
        """Runs an operation against the real minimalmodbus framing code and captures the raw bytes written.

        Args:
            run: Callable invoked with the constructed RS485_RTU instance to
                trigger the send/receive operation being captured.

        Returns:
            The raw RTU frame bytes minimalmodbus wrote to the mocked serial port.
        """
        import minimalmodbus

        from ArtusAPI.communication.RS485_RTU.rs485_rtu_minimalmodbus import RS485_RTU

        written = []
        mock_serial = MagicMock()
        mock_serial.write.side_effect = lambda b: written.append(bytes(b))
        mock_serial.read.return_value = b""
        # minimalmodbus caches serial objects per port name; clear it so each
        # capture gets the fresh mock instead of a previous test's port.
        getattr(minimalmodbus, "_serialports", {}).clear()
        # A real Instrument built around a mocked serial port: the genuine
        # minimalmodbus framing code runs, but bytes land in `written` and the
        # empty response raises NoResponseError after the request is sent.
        with patch("minimalmodbus.serial.Serial", return_value=mock_serial):
            rtu = RS485_RTU(port="MOCK", baudrate=115200, slave_address=SLAVE_ID)
            rtu.open()
        with self.assertRaises(minimalmodbus.ModbusException):
            run(rtu)
        self.assertTrue(written, "no frame captured")
        return written[0]

    def test_send_frames_match(self):
        """Verifies minimalmodbus's on-wire send frame matches the frame pymodbus builds, for every SEND_CASES entry."""
        for name, data, command in SEND_CASES:
            with self.subTest(name=name):
                frame = self._capture_minimalmodbus_frame(
                    lambda rtu: rtu.send(data, command, max_retries=1)
                )
                kind, address, payload = expected_library_call(data, command)
                self.assertEqual(frame, build_pymodbus_frame(kind, address, payload))

    def test_read_frames_match(self):
        """Verifies minimalmodbus's on-wire read frame matches the frame pymodbus builds, for every RECEIVE_CASES entry."""
        for name, data in RECEIVE_CASES:
            with self.subTest(name=name):
                frame = self._capture_minimalmodbus_frame(
                    lambda rtu: rtu.receive(data, max_retries=1)
                )
                self.assertEqual(
                    frame,
                    build_pymodbus_frame("read_holding", data[0], None, count=data[1]),
                )


if __name__ == "__main__":
    unittest.main()
