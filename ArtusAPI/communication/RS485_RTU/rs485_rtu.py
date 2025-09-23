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
from tqdm import tqdm
import logging

from ...common.ModbusMap import CommandType

"""
RS485_RTU class for RS485 communication

This class's function is to simply send and receive data using the minimalmodbus library to send and receive data to the Artus Hand.

The only received data is the feedback data from the hand. This has to be polled. 
The sent data uses two modbus functions, write single register and write multiple registers.
"""
class RS485_RTU:
    def __init__(self, port='COM9', baudrate=115200, timeout=0.5, logger=None, slave_address=1):
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
            self.instrument = minimalmodbus.Instrument(port=self.port, slaveaddress=self.slave_address,debug=False)
            self.instrument.serial.baudrate = self.baudrate
            self.instrument.serial.timeout = self.timeout
            self.instrument.address = self.slave_address
            self.instrument.mode = minimalmodbus.MODE_RTU
            self.logger.info(f"Opening {self.port} @ {self.baudrate} baudrate")
        except Exception as e:
            self.logger.error(e)
            self.logger.error(f"Error opening {self.port} @ {self.baudrate} baudrate")
            quit()
        
    def send(self, data:list,command:int):
        try:
            if command == CommandType.SETUP_COMMANDS.value:
                if len(data) != 1:
                    # Create 16-bit value from two 8-bit values
                    # Validate that both values are 8-bit (0-255)
                    if not (0 <= data[0] <= 255 and 0 <= data[1] <= 255):
                        self.logger.error(f"Values must be 8-bit (0-255). Got: {data[0]}, {data[1]}")
                        return
                    value = (data[0] << 8) | data[1]
                else:
                    value = data[0]
                self.instrument.write_register(registeraddress=0,functioncode=0x06,value=data)
                self.logger.info(f"Sent command: {command} with data: {data}")
            elif command == CommandType.TARGET_COMMAND.value:
                self.instrument.write_registers(registeraddress=data[0],values=data[1:])
                self.logger.info(f"Sent command: {command} with data: {data}")
            elif command == CommandType.FIRMWARE_COMMAND.value:
                self.instrument.write_registers(registeraddress=0,values=data) # reg addr doesn't matter for firmware commmands
                self.logger.info(f"Sent command: {command} with data: {data}")
            else:
                self.logger.error(f"Unknown command: {command}")
        except Exception as e:
                self.logger.error(e)

    def receive(self,data:list):
        ret_list = self.instrument.read_registers(registeraddress=data[0],number_of_registers=data[1])
        self.logger.info(f"Received data: {ret_list}")
        if len(ret_list) == 1:
            return ret_list[0]
        else:
            return ret_list # only returns the data from the registers specified

    def close(self):
        self.instrument.close()

