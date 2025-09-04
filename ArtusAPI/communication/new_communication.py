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

class NewCommunication:
    def __init__(self, port='COM9', baudrate=115200,logger=None, slave_address=0,communication_method="RS485_RTU"
                        logger=None):
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

    def send_data(self, data:list):
        self.communicator.send(data)

    def receive_data(self):
        return self.communicator.receive()
    
    def close_connection(self):
        self.communicator.close()