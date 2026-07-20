"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

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

class RS485_RTU:
    """ARCHIVED minimalmodbus-based RS485 transport for the ARTUS hand.

    Replaced by the pymodbus-based `rs485_rtu.RS485_RTU`. Kept only as the
    baseline for `api_tests/test_rtu_packet_parity.py`, which verifies the
    pymodbus backend produces identical Modbus packets. Requires
    `minimalmodbus` to be installed (no longer a runtime dependency); the
    parity tests skip if it is missing.

    The only data received is hand feedback, which must be polled; sends
    use the Modbus "write single register" and "write multiple registers"
    functions.

    Attributes:
        port: Serial device path (e.g. '/dev/ttyUSB0').
        baudrate: Serial baud rate.
        timeout: Serial read timeout in seconds.
        slave_address: Modbus slave address of the target hand.
        logger: Logger used for status and error messages.
        instrument: The underlying `minimalmodbus.Instrument`, created on
            the first call to `open`.
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
        self.logger = logger
        self.slave_address = slave_address

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def open(self):
        """Opens the RS485 serial connection via minimalmodbus.

        On failure, logs the error and terminates the process via `quit()`.
        """
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
        """Writes register values to the hand, retrying on Modbus errors.

        Data must be in 16-bit register format. Dispatches to
        `write_register`/`write_registers` depending on `command`.

        Args:
            data: Register values to write. For `SETUP_COMMANDS`, either a
                single value or a 2-element [low_byte, high_byte] pair
                packed into one register; for other command types, the
                first element is the starting register address followed by
                the values to write (except FIRMWARE_COMMAND, which writes
                `data` starting at register 0).
            command: CommandType enum value selecting the write operation.
            max_retries: Number of times to retry on exception.
            retry_delay: Delay in seconds between retries.

        Returns:
            True if the write succeeded. False if an unknown command type
            was given, or if 8-bit value validation failed for
            SETUP_COMMANDS.

        Raises:
            minimalmodbus.NoResponseError: If the final retry attempt still
                gets no response.
            minimalmodbus.InvalidResponseError: If the final retry attempt
                still gets an invalid response.
            minimalmodbus.ModbusException: If the final retry attempt still
                fails with a Modbus-level error.
            serial.SerialException: If the serial port itself fails; not
                retried.
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
                    raise  # Re-raise on final attempt
                    
            except serial.SerialException as e:
                self.logger.error(f"Serial port error: {e}")
                raise  # Don't retry serial port errors
                
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
            A single value if one register was read, or a list of values if
            more than one was read; None if `max_retries` is 0.

        Raises:
            minimalmodbus.NoResponseError: If the final retry attempt still
                gets no response.
            minimalmodbus.InvalidResponseError: If the final retry attempt
                still gets an invalid response.
            minimalmodbus.ModbusException: If the final retry attempt still
                fails with a Modbus-level error.
            serial.SerialException: If the serial port itself fails; not
                retried.
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
                    raise
                    
            except serial.SerialException as e:
                self.logger.error(f"Serial port error: {e}")
                raise
                
            except Exception as e:
                self.logger.error(f"Unexpected error during receive: {e}")
                raise
        
        return None

    def close(self):
        """Closes the underlying serial connection."""
        self.instrument.serial.close()

