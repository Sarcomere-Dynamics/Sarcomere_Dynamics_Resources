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

"""
RS485_RTU class for RS485 communication

This class's function is to simply send and receive data using the minimalmodbus library to send and receive data to the Artus Hand.

The only received data is the feedback data from the hand. This has to be polled. 
The sent data uses two modbus functions, write single register and write multiple registers.
"""
class RS485_RTU:
    def __init__(self, port='COM9', baudrate=115200, timeout=0.5, logger=None, slave_address=0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.logger = logger

        self.instrument = minimalmodbus.Instrument(self.port, self.slave_address)
        self.instrument.serial.baudrate = self.baudrate
        self.instrument.serial.timeout = self.timeout
        self.instrument.mode = minimalmodbus.MODE_RTU

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def open(self):
        try:
            self.instrument.open()
            self.logger.info(f"Opening {self.port} @ {self.baudrate} baudrate")
        except Exception as e:
            self.logger.error(e)
            self.logger.error(f"Error opening {self.port} @ {self.baudrate} baudrate")
            quit()
        
    def send(self, data:list,command:int):
        try:
            if command == 0x06:
                self.instrument.write_register(register_address=0,functioncode=0x06,data=data)
                self.logger.info(f"Sent command: {command} with data: {data}")
            elif command == 16:
                self.instrument.write_registers(register_address=data[0],values=data[1:])
                self.logger.info(f"Sent command: {command} with data: {data}")
            else:
                self.logger.error(f"Unknown command: {command}")
        except Exception as e:
                self.logger.error(e)

    def receive(self,data:list):
        ret_list = self.instrument.read_registers(register_address=data[0],number_of_registers=data[1])
        self.logger.info(f"Received data: {ret_list}")
        return ret_list # only returns the data from the registers specified

    def close(self):
        self.instrument.close()

