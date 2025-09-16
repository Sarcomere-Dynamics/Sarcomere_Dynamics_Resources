"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import os
import time
import logging
from tqdm import tqdm

from ..communication.new_communication import CommandType
BYTES_CHUNK = 128


class FirmwareUpdaterNew:
    def __init__(self,
                 communication_handler = None,
                 command_handler = None,
                 file_location = None,
                 logger = None):
        self._communication_handler = communication_handler
        self._command_handler = command_handler
        self.file_location = file_location
        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def get_bin_file_info(self):
        file_size = int(os.path.getsize(self.file_location))
        self.logger.info(f"Bin file size = {file_size} @ location {self.file_location}")
        return file_size

    def send_firmware(self,file_size):
        i = 0
        ret = False
        with tqdm(total=len(file_data), unit="B", unit_scale=True, desc="Uploading Actuator Firmware") as pbar:
            while i < len(file_data):
                chunk = list(file_data[i:i+BYTES_CHUNK])
                self._communication_handler.send_data(chunk,CommandType.FIRMWARE_COMMAND.value)
                i += BYTES_CHUNK
                pbar.update(BYTES_CHUNK)
                time.sleep(0.01)
                if ret:
                    i += BYTES_CHUNK
                    ret = 0