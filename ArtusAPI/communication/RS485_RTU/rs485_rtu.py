"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

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
    """
    Return a list of 'pid <pid> (<cmdline>)' strings for every process that has
    `port` open. Used to diagnose 'could not exclusively lock port' errors.
    Linux only (/proc scan); returns [] on other platforms or if nothing holds it.
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

"""
RS485_RTU class for RS485 communication

This class's function is to simply send and receive data using the pymodbus library to send and receive data to the Artus Hand.

The only received data is the feedback data from the hand. This has to be polled.
The sent data uses two modbus functions, write single register and write multiple registers.
"""
class RS485_RTU:
    def __init__(self, port='COM9', baudrate=115200, timeout=0.1, logger=None, slave_address=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.slave_address = slave_address

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def open(self):
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
        """
        Data needs to be in 16b format
        max_retries: Number of times to retry on exception
        retry_delay: Delay in seconds between retries
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
        """
        Receive data with retry logic
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
        client = getattr(self, "client", None)
        if client is None:
            return
        try:
            client.close()
        except Exception:
            pass
