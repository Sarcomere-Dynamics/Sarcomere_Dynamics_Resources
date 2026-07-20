"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException, ConnectionException
import logging
import time
from ...common.ModbusMap import CommandType


class ModbusTCP:
    """Modbus TCP transport for communicating with an ARTUS hand over Ethernet/WiFi.

    Wraps a `pymodbus` `ModbusTcpClient`, exposing the same open/send/receive/
    close interface as `RS485_RTU`, with connection retry logic in `send`
    and `receive`.

    Attributes:
        host: Hostname or IP address of the Modbus TCP server.
        port: TCP port of the Modbus TCP server.
        timeout: Socket timeout in seconds.
        slave_address: Modbus unit/device id of the target hand.
        logger: Logger used for status and error messages.
        client: The underlying `pymodbus` `ModbusTcpClient` instance,
            created on the first call to `open`.
    """

    def __init__(self, host='192.168.2.8', port=502, timeout=1.0, logger=None, slave_address=1):
        """Initializes connection parameters without connecting.

        Args:
            host: Hostname or IP address of the Modbus TCP server.
            port: TCP port of the Modbus TCP server.
            timeout: Socket timeout in seconds.
            logger: Logger to use; a module-level logger is created if None.
            slave_address: Modbus unit/device id of the target hand.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.slave_address = slave_address

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def is_connected(self) -> bool:
        """Checks whether the TCP client exists and reports itself connected.

        Returns:
            True if `client` has been created and is currently connected.
        """
        client = getattr(self, "client", None)
        return client is not None and bool(getattr(client, "connected", False))

    def open(self):
        """Opens (or reopens) the Modbus TCP connection.

        No-op if already connected. Closes and discards any stale client
        before creating a new `ModbusTcpClient` and connecting.

        Raises:
            ConnectionError: If the TCP connection could not be established.
        """
        if self.is_connected():
            return
        client = getattr(self, "client", None)
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
        try:
            # retries=0: retry policy is owned by send()/receive() loops, same as RS485_RTU
            self.client = ModbusTcpClient(host=self.host, port=self.port, timeout=self.timeout, retries=0)
            if not self.client.connect():
                raise ConnectionError(
                    f"Could not open Modbus TCP connection to {self.host}:{self.port}"
                )
            self.logger.info(f"Opened TCP connection to {self.host}:{self.port}")
        except Exception as e:
            self.logger.error(e)
            self.logger.error(f"Error opening TCP connection to {self.host}:{self.port}")
            raise

    def send(self, data: list, command: int, max_retries=3, retry_delay=0.5):
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
            max_retries: Number of attempts before giving up.
            retry_delay: Delay in seconds between retries.

        Returns:
            True if the write succeeded. False if an unknown command type
            was given, or if 8-bit value validation failed for
            SETUP_COMMANDS.

        Raises:
            ModbusIOException: If the final retry attempt still receives an
                error response.
            ConnectionException: If the final retry attempt still fails to
                connect.
        """
        for attempt in range(max_retries):
            try:
                if not self.is_connected():
                    self.open()
                if command == CommandType.SETUP_COMMANDS.value:
                    if len(data) != 1:
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

                return True

            except (ModbusIOException, ConnectionException, ConnectionError) as e:
                self.logger.warning(f"Modbus exception on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to send after {max_retries} attempts")
                    raise

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                raise

        return False

    def receive(self, data: list, max_retries=3, retry_delay=0.1):
        """Reads holding registers from the hand, retrying on Modbus errors.

        Args:
            data: Two-element list `[start_register, count]` describing the
                registers to read.
            max_retries: Number of attempts before giving up.
            retry_delay: Delay in seconds between retries.

        Returns:
            A single int if one register was read, a list of ints if more
            than one was read, or None if `max_retries` is 0.

        Raises:
            ModbusIOException: If the final retry attempt still receives an
                error response.
            ConnectionException: If the final retry attempt still fails to
                connect.
        """
        for attempt in range(max_retries):
            try:
                if not self.is_connected():
                    self.open()
                result = self.client.read_holding_registers(data[0], count=data[1], device_id=self.slave_address)
                if result.isError():
                    raise ModbusIOException(f"Modbus error response: {result}")

                registers = result.registers
                if len(registers) == 1:
                    return registers[0]
                return registers

            except (ModbusIOException, ConnectionException, ConnectionError) as e:
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
        """Closes the TCP connection, if one is open. Errors are suppressed."""
        client = getattr(self, "client", None)
        if client is None:
            return
        try:
            client.close()
        except Exception:
            pass
