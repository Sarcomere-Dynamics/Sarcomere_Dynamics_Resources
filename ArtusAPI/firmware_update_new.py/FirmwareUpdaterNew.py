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

from ..common.ModbusMap import CommandType
BYTES_CHUNK = 200


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

    # this function is only managing sending the actuatl binary data to the master
    # it is not managing starting the firmware update process on the master
    def update_firmware(self,file_size):
        i = 0
        ret = False

        file = open(self.file_location,'rb')
        file_data = file.read()
        file.close()

        chunks_required = int(file_size/BYTES_CHUNK) + 1
        self.logger.info(f"Binary File will be sent in {BYTES_CHUNK} byte packages for a total of {chunks_required} chunks")
        
        with tqdm(total=file_size, unit="B", unit_scale=True, desc="Uploading Actuator Firmware") as pbar:
            while i < file_size:
                if i+BYTES_CHUNK > file_size:
                    chunk = list(file_data[i:])
                    while len(chunk) < BYTES_CHUNK:
                        chunk.append(0xFF)
                else:
                    chunk = list(file_data[i:i+BYTES_CHUNK])

                # take each pair and make it into a 16bit value
                for pc in range(0, len(chunk), 2):
                    if pc + 1 < len(chunk):
                        chunk[pc] = chunk[pc] << 8 | chunk[pc + 1]
                    else:
                        chunk[pc] = chunk[pc] << 8 | 0x00

                chunk.insert(0,self._command_handler.commands['firmware_update_command']) # this has to be the first element every time

                self._communication_handler.send_data(chunk,CommandType.FIRMWARE_COMMAND.value)
                i += BYTES_CHUNK
                pbar.update(BYTES_CHUNK)

        # send eof is when firmware update commmand is not the  first element in the list
        eof_list = [0x0,0x0]
        self._communication_handler.send_data(eof_list,CommandType.FIRMWARE_COMMAND.value)

        self.logger.info("Firmware Update is in progress..")
