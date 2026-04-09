"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import minimalmodbus
import serial
# import modbus_tk
# from modbus_tk.modbus_rtu import RtuMaster
# import modbus_tk.defines as cst
from tqdm import tqdm
import logging
import time
from ...common.ModbusMap import CommandType
import struct as _struct

"""
RS485_RTU class for RS485 communication

This class's function is to simply send and receive data using the minimalmodbus library to send and receive data to the Artus Hand.

The only received data is the feedback data from the hand. This has to be polled. 
The sent data uses two modbus functions, write single register and write multiple registers.
"""
class RS485_RTU:
    def __init__(self, port='COM9', baudrate=115200, timeout=0.1, logger=None, slave_address=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.logger = logger
        self.slave_address = slave_address

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def open(self):
        try:
            # minimalmodbus
            self.instrument = minimalmodbus.Instrument(port=self.port, slaveaddress=self.slave_address,debug=False)
            self.instrument.serial.baudrate = self.baudrate
            self.instrument.serial.timeout = self.timeout
            self.instrument.address = self.slave_address
            self.instrument.mode = minimalmodbus.MODE_RTU

            # mdobus tk
            # self.instrument = RtuMaster(
            # serial.Serial(port=self.port, baudrate=self.baudrate, bytesize=8, parity='N', stopbits=1, xonxoff=0))
            # self.instrument.set_timeout(self.timeout)
            # self.instrument.set_verbose(False)

            self.logger.info(f"Opening {self.port} @ {self.baudrate} baudrate")
        except Exception as e:
            self.logger.error(e)
            self.logger.error(f"Error opening {self.port} @ {self.baudrate} baudrate")
            quit()
    
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
                    
                    self.instrument.write_register(registeraddress=0, functioncode=0x06, value=value)
                elif command == CommandType.TARGET_COMMAND.value:
                    self.instrument.write_registers(registeraddress=data[0], values=data[1:])
                elif command == CommandType.FIRMWARE_COMMAND.value:
                    self.instrument.write_registers(registeraddress=0, values=data)
                else:
                    self.logger.error(f"Unknown command: {command}")
                    return False
                
                # Success - return True
                return True
                
            except (minimalmodbus.NoResponseError, minimalmodbus.InvalidResponseError,
                    minimalmodbus.ModbusException) as e:
                self.logger.warning(f"Modbus exception on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to send after {max_retries} attempts")
                    pass  # Re-raise on final attempt
                    
            except serial.SerialException as e:
                self.logger.error(f"Serial port error: {e}")
                raise  # Don't retry serial port errors
                
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
                ret_list = self.instrument.read_registers(registeraddress=data[0], number_of_registers=data[1])
                if len(ret_list) == 1:
                    return ret_list[0]
                else:
                    return ret_list
                    
            except (minimalmodbus.NoResponseError, minimalmodbus.InvalidResponseError,
                    minimalmodbus.ModbusException) as e:
                self.logger.warning(f"Modbus exception on receive attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to receive after {max_retries} attempts")
                    pass
                    
            except serial.SerialException as e:
                self.logger.error(f"Serial port error: {e}")
                raise
                
            except Exception as e:
                self.logger.error(f"Unexpected error during receive: {e}")
                raise
        
        return None

    def close(self):
        self.instrument.serial.close()
        
    def update_slave_address(self, new_slave_address):
        """Update the Modbus slave address on the live hand."""
        self.slave_address = new_slave_address
        if hasattr(self, 'instrument'):
            self.instrument.address = new_slave_address

    def _crc16(self, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _build_write_single_register_frame(self, slave_addr, register, value):
        """Build a raw Modbus RTU 'write single register' (FC 0x06) frame."""
        payload = _struct.pack('>BBHH', slave_addr, 0x06, register, value)
        crc = self._crc16(payload)
        return payload + _struct.pack('<H', crc)

    def _build_read_holding_registers_frame(self, slave_addr, start_register, count):
        """Build a raw Modbus RTU 'read holding registers' (FC 0x03) frame."""
        payload = _struct.pack('>BBHH', slave_addr, 0x03, start_register, count)
        crc = self._crc16(payload)
        return payload + _struct.pack('<H', crc)

    def raw_write_register(self, register: int, value: int, slave_override: int = None):
        """
        Write a single register using raw serial, bypassing minimalmodbus address validation. Returns the actual slave address from the response, or None if no response.
        """
        addr = slave_override if slave_override is not None else self.slave_address
        frame = self._build_write_single_register_frame(addr, register, value)

        ser = self.instrument.serial
        ser.reset_input_buffer()
        ser.write(frame)
        time.sleep(0.05)

        # FC 0x06 echo response is always 8 bytes
        resp = ser.read(8)
        if len(resp) < 8:
            self.logger.warning(f"raw_write_register: short response ({len(resp)} bytes")
            return None

        resp_slave = resp[0]
        self.logger.info(f"raw_write_register: sent as addr={addr}, hand replied as addr={resp_slave}")
        return resp_slave

    def raw_read_registers(self, start_register: int, count: int, slave_override: int = None):
        """
        Read holding registers using raw serial, bypassing minimalmodbus address validation. Returns (actual_slave_addr, [register_values]) or (None, None) on failure.
        """
        addr = slave_override if slave_override is not None else self.slave_address
        frame = self._build_read_holding_registers_frame(addr, start_register, count)

        ser = self.instrument.serial
        ser.reset_input_buffer()
        ser.write(frame)
        time.sleep(0.05)

        # Response: slave(1) + FC(1) + byte_count(1) + data(count*2) + CRC(2)
        expected_len = 3 + count * 2 + 2
        resp = ser.read(expected_len)
        if len(resp) < expected_len:
            self.logger.warning(f"raw_read_registers: short response ({len(resp)}/{expected_len} bytes)")
            return None, None

        resp_slave = resp[0]
        byte_count = resp[2]
        # Parse register values (big-endian unsigned 16-bit)
        values = []
        for i in range(count):
            offset = 3 + i * 2
            val = (resp[offset] << 8) | resp[offset + 1]
            values.append(val)

        return resp_slave, values

