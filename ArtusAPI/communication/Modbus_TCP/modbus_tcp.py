"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException, ConnectionException
import logging
import time
from ...common.ModbusMap import CommandType


class ModbusTCP:
    def __init__(self, host='192.168.2.8', port=502, timeout=1.0, logger=None, slave_address=1):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.slave_address = slave_address

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def is_connected(self) -> bool:
        client = getattr(self, "client", None)
        return client is not None and bool(getattr(client, "connected", False))

    def open(self):
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
        """
        Data needs to be in 16b format.
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
        client = getattr(self, "client", None)
        if client is None:
            return
        try:
            client.close()
        except Exception:
            pass
