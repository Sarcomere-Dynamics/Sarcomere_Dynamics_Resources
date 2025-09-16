"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import logging
import time
import struct
from tqdm import tqdm

from .RS485_RTU.rs485_rtu import RS485_RTU
from ..common.ModbusMap import ModbusMap

from enum import Enum

class ActuatorState(Enum):
    ACTUATOR_INITIALIZING = 0
    ACTUATOR_IDLE = 1
    ACTUATOR_CALIBRATING_LL = 2  # calibrating the rotor position for foc
    ACTUATOR_CALIBRATED_LL = 3
    ACTUATOR_CALIBRATING_HL = 4  # calibrating the endstop position finding for homing
    ACTUATOR_CALIBRATING_STROKE = 5  # calibrating the stroke of the finger
    ACTUATOR_CALIBRATION_FAILED = 6
    ACTUATOR_READY = 7  # ready to receive commmands, setup control modes, etc.
    ACTUATOR_WAIT_ACK = 8  # wait for ack from actuator
    ACTUATOR_ERROR = 9

class CommandType(Enum):
    SETUP_COMMANDS = 6
    TARGET_COMMAND = 16

class NewCommunication:
    def __init__(self, port='COM9', baudrate=115200, logger=None, slave_address=0, communication_method="RS485_RTU"):
        self.port = port
        self.baudrate = baudrate
        self.logger = logger
        self.slave_address = slave_address
        self.communication_method = communication_method
        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self._setup_communication()

    
    def _setup_communication(self):
        if self.communication_method == "RS485_RTU":
            self.communicator = RS485_RTU(port=self.port, baudrate=self.baudrate, timeout=0.5, logger=self.logger, slave_address=self.slave_address)
        else:
            raise ValueError("Unknown communication method")

    def open_connection(self):
        self.communicator.open()

    def send_data(self, data:list,command_type:int=CommandType.SETUP_COMMANDS.value):
        self.communicator.send(data,command_type)

    def receive_data(self,amount_dat:int=1,start:int=ModbusMap().modbus_reg_map['feedback_register']): # default is receive robot state
        return self.communicator.receive([amount_dat,start])
    
    def close_connection(self):
        self.communicator.close()

    def wait_for_ready(self,timeout=30,vis=False):
        start_time = time.perf_counter()
        def _check_robot_state(self):
            """Helper function to check robot state and return status"""
            ret = self.receive_data()
            if isinstance(ret, int) and ret <= 0xFFFF:  # Check if ret is a 16-bit value
                high_byte = (ret >> 8) & 0xFF  # Extract upper 8 bits
                low_byte = ret & 0xFF          # Extract lower 8 bits
                if low_byte == ActuatorState.ACTUATOR_READY.value:
                    self.logger.info("Robot ready")
                    return True
                elif low_byte == ActuatorState.ACTUATOR_CALIBRATION_FAILED.value or low_byte == ActuatorState.ACTUATOR_ERROR.value:
                    self.logger.error("Calibration failed or error")
                    return False
            else:
                raise ValueError("Received data is not a 16-bit value")
            return None  # Continue waiting

        if vis:
            with tqdm(total=timeout,unit="s",desc="Waiting for Robot Ready") as progresbar:
                while 1:
                    result = self._check_robot_state()
                    if result is not None:
                        return result
                    time.sleep(0.05)
        else:
            while 1:
                result = self._check_robot_state()
                if result is not None:
                    return result
                time.sleep(0.05)