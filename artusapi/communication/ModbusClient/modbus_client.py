# Sarcomere Dynamics Software License Notice
# ------------------------------------------
# This software is developed by Sarcomere Dynamics Inc.
# for use with the ARTUS family of robotic products.
#
# Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.
#
# Licensed under the Sarcomere Dynamics Software License.
# See the LICENSE file in the repository for full details.

import logging
import time

from pymodbus.exceptions import ConnectionException, ModbusIOException

from ...common.modbus_map import CommandType

MODBUS_MAX_NUM_RETRIES = 3
MODBUS_TX_RETRY_DELAY_SECONDS = 0.5
MODBUS_RX_RETRY_DELAY_SECONDS = 0.1


class ModbusClient:
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

    def __init__(
        self, timeout: float, logger: logging.Logger | None, slave_address: int
    ):
        """Initializes connection parameters without opening the port.

        Args:
            port: Serial device path to connect to.
            baudrate: Serial baud rate.
            timeout: Serial read timeout in seconds.
            logger: Logger to use; a module-level logger is created if None.
            slave_address: Modbus slave address of the target hand.
        """
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

    def open(self) -> None:
        if self.logger is not None:
            self.logger.error("Must be handled per-transport basis")

    def close(self) -> None:
        """Closes the serial connection, if one is open. Errors are suppressed."""
        client = getattr(self, "client", None)
        if client is None:
            return
        try:
            client.close()
            self.client = None
        except Exception as e:
            self.logger.error(f"Could not close connection: {e}")

    def send(
        self,
        data: list,
        command: int,
        max_retries: int = MODBUS_MAX_NUM_RETRIES,
        retry_delay: int = MODBUS_TX_RETRY_DELAY_SECONDS,
    ):
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
        if self.client is None:
            self.logger.error("Modbus client does not exist.")
            return

        if not self.is_connected():
            self.logger.error("Modbus client is not connected.")
            return

        for attempt in range(max_retries):
            try:
                match command:
                    case CommandType.SETUP_COMMANDS.value:
                        if len(data) != 1:
                            # Cast each data value into uint8_t before concat
                            d0 = int(data[0]) & 0xFF
                            d1 = int(data[1]) & 0xFF
                            if not (0 <= d0 <= 255 and 0 <= d1 <= 255):
                                self.logger.error(
                                    f"Values must be 8-bit (0-255). Got: {data[0]}, {data[1]}"
                                )
                                return False
                            value = (d1 << 8) | d0
                        else:
                            value = data[0]

                        result = self.client.write_register(
                            0, value, device_id=self.slave_address
                        )
                    case CommandType.TARGET_COMMAND.value:
                        result = self.client.write_registers(
                            data[0], data[1:], device_id=self.slave_address
                        )
                    case (
                        CommandType.FIRMWARE_COMMAND.value
                        | CommandType.CONFIG_COMMAND.value
                    ):
                        result = self.client.write_registers(
                            0, data, device_id=self.slave_address
                        )
                    case _:
                        self.logger.error(f"Unknown command: {command}")
                        return False

                if result.isError():
                    raise ModbusIOException(f"Modbus error response: {result}")

                return True

            except (ModbusIOException, ConnectionException) as e:
                self.logger.warning(
                    f"Modbus exception on attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to send after {max_retries} attempts")
                    raise  # Re-raise on final attempt

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                raise  # Don't retry unexpected errors

        return False

    def receive(
        self,
        data: list,
        max_retries: int = MODBUS_MAX_NUM_RETRIES,
        retry_delay: int = MODBUS_RX_RETRY_DELAY_SECONDS,
    ) -> list | None:
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
        if self.client is None:
            self.logger.error("Modbus client does not exist.")
            return

        if not self.is_connected():
            self.logger.error("Modbus client is not connected.")
            return

        for attempt in range(max_retries):
            try:
                result = self.client.read_holding_registers(
                    data[0], count=data[1], device_id=self.slave_address
                )
                if result.isError():
                    raise ModbusIOException(f"Modbus error response: {result}")

                registers = result.registers
                if len(registers) == 1:
                    return registers[0]
                else:
                    return registers

            except (ModbusIOException, ConnectionException) as e:
                self.logger.warning(
                    f"Modbus exception on receive attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to receive after {max_retries} attempts")
                    raise

            except Exception as e:
                self.logger.error(f"Unexpected error during receive: {e}")
                raise

        return None

    def send_receive(
        self,
        read_start: int,
        read_count: int,
        write_start: int,
        values: list,
        max_retries=MODBUS_MAX_NUM_RETRIES,
        retry_delay=MODBUS_RX_RETRY_DELAY_SECONDS,
    ):
        """Atomically writes registers then reads registers via Modbus FC 0x17.

        Uses pymodbus ``readwrite_registers`` (Read/Write Multiple Registers).
        Firmware applies the write first, then returns the read data.

        Args:
            read_start: Starting holding-register address to read.
            read_count: Number of registers to read.
            write_start: Starting holding-register address to write.
            values: List of uint16 register values to write.
            max_retries: Number of times to retry on exception.
            retry_delay: Delay in seconds between retries.

        Returns:
            A single int if one register was read, a list of ints if more
            than one was read, or None if ``max_retries`` is 0.

        Raises:
            ModbusIOException: If the final retry attempt still receives an
                error response.
            ConnectionException: If the final retry attempt still fails.
        """
        if self.client is None:
            self.logger.error("Modbus client does not exist.")
            return

        if not self.is_connected():
            self.logger.error("Modbus client is not connected.")
            return

        for attempt in range(max_retries):
            try:
                result = self.client.readwrite_registers(
                    read_address=read_start,
                    read_count=read_count,
                    write_address=write_start,
                    values=values,
                    device_id=self.slave_address,
                )
                if result.isError():
                    raise ModbusIOException(f"Modbus error response: {result}")

                registers = result.registers
                if len(registers) == 1:
                    return registers[0]
                return registers

            except (ModbusIOException, ConnectionException) as e:
                self.logger.warning(
                    f"Modbus exception on send_receive attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(
                        f"Failed to send_receive after {max_retries} attempts"
                    )
                    raise

            except Exception as e:
                self.logger.error(f"Unexpected error during send_receive: {e}")
                raise

        return None
