"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException, ConnectionException
import logging
import os
import time
from ...common.ModbusMap import CommandType


def find_port_holders(port):
    """Finds processes that currently have `port` open.

    Used to diagnose "could not exclusively lock port" errors by scanning
    `/proc` for file descriptors pointing at the given path. Linux only.

    Args:
        port: Filesystem path of the serial device to check (e.g.
            '/dev/ttyUSB0').

    Returns:
        A list of 'pid <pid> (<cmdline>)' strings, one per process holding
        the port open. Empty on non-Linux platforms or if nothing holds it.
    """
    holders = []
    try:
        target = os.path.realpath(port)
        for pid in os.listdir('/proc'):
            if not pid.isdigit() or int(pid) == os.getpid():
                continue
            fd_dir = f'/proc/{pid}/fd'
            try:
                for fd in os.listdir(fd_dir):
                    link = os.readlink(os.path.join(fd_dir, fd))
                    if link == target or link == f'{target} (deleted)':
                        with open(f'/proc/{pid}/cmdline') as f:
                            cmd = f.read().replace('\0', ' ').strip() or '?'
                        suffix = ' [stale fd, port re-enumerated]' if link.endswith('(deleted)') else ''
                        holders.append(f'pid {pid} ({cmd}){suffix}')
                        break
            except (PermissionError, FileNotFoundError, OSError):
                continue
    except Exception:
        pass
    return holders

class RS485_RTU:
    """Modbus RTU transport for RS485 communication with an ARTUS hand.

    Wraps a `pymodbus` `ModbusSerialClient` to send and receive data over
    RS485. The only data received is hand feedback, which must be polled;
    sends use the Modbus "write single register" and "write multiple
    registers" functions.

    Attributes:
        port: Serial device path (e.g. '/dev/ttyUSB0').
        baudrate: Serial baud rate.
        timeout: Serial read timeout in seconds.
        slave_address: Modbus slave address of the target hand.
        logger: Logger used for status and error messages.
        client: The underlying `pymodbus` `ModbusSerialClient` instance,
            created on the first call to `open`.
    """

    def __init__(self, port='COM9', baudrate=115200, timeout=0.1, logger=None, slave_address=1):
        """Initializes connection parameters without opening the port.

        Args:
            port: Serial device path to connect to.
            baudrate: Serial baud rate.
            timeout: Serial read timeout in seconds.
            logger: Logger to use; a module-level logger is created if None.
            slave_address: Modbus slave address of the target hand.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.slave_address = slave_address

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def open(self):
        """Opens the RS485 serial connection.

        Raises:
            ConnectionError: If the port could not be opened; the error
                message includes any processes found holding the port via
                `find_port_holders`.
        """
        try:
            # retries=0: retry behaviour is handled in send/receive below,
            # matching the previous minimalmodbus implementation
            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=self.timeout,
                retries=0,
            )
            if not self.client.connect():
                holders = find_port_holders(self.port)
                msg = f"Could not open {self.port} @ {self.baudrate} baudrate"
                if holders:
                    msg += f". Port is held by: {'; '.join(holders)}"
                raise ConnectionError(msg)

            self.logger.info(f"Opening {self.port} @ {self.baudrate} baudrate")
        except Exception as e:
            self.logger.error(e)
            self.logger.error(f"Error opening {self.port} @ {self.baudrate} baudrate")
            raise

    def send(self, data:list, command:int, max_retries=3, retry_delay=0.5):
        """Writes register values to the hand, retrying on Modbus errors.

        Data must be in 16-bit register format. Dispatches to
        `write_register`/`write_registers` depending on `command`.

        Args:
            data: Register values to write. For `SETUP_COMMANDS`, either a
                single value or a 2-element [low_byte, high_byte] pair
                packed into one register; for other command types, the
                first element is the starting register address followed by
                the values to write (except FIRMWARE_COMMAND/CONFIG_COMMAND,
                which write `data` starting at register 0).
            command: CommandType enum value selecting the write operation.
            max_retries: Number of times to retry on exception.
            retry_delay: Delay in seconds between retries.

        Returns:
            True if the write succeeded. False if an unknown command type
            was given, or if 8-bit value validation failed for
            SETUP_COMMANDS.

        Raises:
            ModbusIOException: If the final retry attempt still receives an
                error response.
            ConnectionException: If the final retry attempt still fails.
        """
        for attempt in range(max_retries):
            try:
                if command == CommandType.SETUP_COMMANDS.value:
                    if len(data) != 1:
                        # Cast each data value into uint8_t before concat
                        d0 = int(data[0]) & 0xFF
                        d1 = int(data[1]) & 0xFF
                        if not (0 <= d0 <= 255 and 0 <= d1 <= 255):
                            self.logger.error(f"Values must be 8-bit (0-255). Got: {data[0]}, {data[1]}")
                            return False
                        value = (d1 << 8) | d0
                    else:
                        value = data[0]

                    result = self.client.write_register(0, value, device_id=self.slave_address)
                elif command == CommandType.TARGET_COMMAND.value:
                    result = self.client.write_registers(data[0], data[1:], device_id=self.slave_address)
                elif command == CommandType.FIRMWARE_COMMAND.value:
                    result = self.client.write_registers(0, data, device_id=self.slave_address)
                elif command == CommandType.CONFIG_COMMAND.value:
                    result = self.client.write_registers(0, data, device_id=self.slave_address)
                else:
                    self.logger.error(f"Unknown command: {command}")
                    return False

                if result.isError():
                    raise ModbusIOException(f"Modbus error response: {result}")

                # Success - return True
                return True

            except (ModbusIOException, ConnectionException) as e:
                self.logger.warning(f"Modbus exception on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to send after {max_retries} attempts")
                    raise  # Re-raise on final attempt

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                raise  # Don't retry unexpected errors

        return False

    def receive(self, data:list, max_retries=3, retry_delay=0.1):
        """Reads holding registers from the hand, retrying on Modbus errors.

        Args:
            data: Two-element list `[start_register, count]` describing the
                registers to read.
            max_retries: Number of times to retry on exception.
            retry_delay: Delay in seconds between retries.

        Returns:
            A single int if one register was read, a list of ints if more
            than one was read, or None if `max_retries` is 0.

        Raises:
            ModbusIOException: If the final retry attempt still receives an
                error response.
            ConnectionException: If the final retry attempt still fails.
        """
        for attempt in range(max_retries):
            try:
                result = self.client.read_holding_registers(data[0], count=data[1], device_id=self.slave_address)
                if result.isError():
                    raise ModbusIOException(f"Modbus error response: {result}")

                registers = result.registers
                if len(registers) == 1:
                    return registers[0]
                else:
                    return registers

            except (ModbusIOException, ConnectionException) as e:
                self.logger.warning(f"Modbus exception on receive attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to receive after {max_retries} attempts")
                    raise

            except Exception as e:
                self.logger.error(f"Unexpected error during receive: {e}")
                raise

        return None

    def close(self):
        """Closes the serial connection, if one is open. Errors are suppressed."""
        client = getattr(self, "client", None)
        if client is None:
            return
        try:
            client.close()
        except Exception:
            pass
