"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

from typing import NoReturn


import os
import time
import logging
from tqdm import tqdm
import math

from ..common.ModbusMap import CommandType,ActuatorState
from ..communication.new_communication import NewCommunication
BYTES_CHUNK = 64


class FirmwareUpdaterNew:
    def __init__(self,
                 communication_handler:NewCommunication = None,
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
    
    def flashing_ack_checker(self):
        while True:
            ret = self._communication_handler._check_robot_state()

            if ret == ActuatorState.ACTUATOR_FLASHING_ACK.value:
                return True
            elif ret == ActuatorState.ACTUATOR_ERROR.value:
                return False
            else:
                time.sleep(0.1)
    
    def update_firmware_piecewise(self,file_size):
        """
        @info function to update brushless drivers through masterboard
        """
        byte_counter = 0
        page_counter = 0
        ret = None

        file = open(self.file_location,'rb')
        file_data = file.read()
        file.close()

        time.sleep(1)

        # wait for the initial communication/erase function
        if not self.flashing_ack_checker():
            return False

        pages_required = math.ceil(file_size/256)
        self.logger.info(f"Upload requires {pages_required} page writes")

        # over total number of bytes
        with tqdm(total=pages_required, unit="pages", unit_scale=True, desc="Uploading Actuator Firmware") as pbar:
            while page_counter < pages_required:
                # page loop
                page_byte_counter = 0
                while page_byte_counter < 256:
                    # fill byte data

                    concat_chunk = []
                    # take each pair and make it into a 16bit value
                    while len(concat_chunk) < 64: # 128 bytes
                        if byte_counter >= file_size:
                            concat_chunk.append(0xffff)
                        elif byte_counter+1 >= file_size:
                            concat_chunk.append(file_data[byte_counter] << 8 | 0xff) 
                        else:
                            concat_chunk.append(file_data[byte_counter] << 8 | file_data[byte_counter+1])
                        byte_counter += 2

                    concat_chunk.insert(0,self._command_handler.commands['firmware_update_command']) # this has to be the first element every time

                    self._communication_handler.send_data(concat_chunk,CommandType.FIRMWARE_COMMAND.value)
                    page_byte_counter += 128

                time.sleep(0.01)

                self.logger.info(f"Sent page {page_counter} of {pages_required}")

                # a full page has been uploaded
                if not self.flashing_ack_checker():
                    return False
                # while not self.flashing_ack_checker():
                #     time.sleep(0.1)

                self.logger.info(f"Page {page_counter} of {pages_required} uploaded - ACK received")

                time.sleep(0.01)

                # reset page_byte_counter
                page_byte_counter = 0
                page_counter += 1
                pbar.update(1)

        # send 0000 to end the firmware update process
        eof_list = [0x0,0x0]
        self._communication_handler.send_data(eof_list,CommandType.FIRMWARE_COMMAND.value)
        self.logger.info("Firmware Update is in progress..")




    # this function is only managing sending the actuatl binary data to the master
    # it is not managing starting the firmware update process on the master
    def update_firmware(self,file_size):
        byte_counter = 0
        page_counter = 0
        ret = None

        file = open(self.file_location,'rb')
        file_data = file.read()
        file.close()

        time.sleep(1)

        # wait for the initial communication/erase function
        if not self.flashing_ack_checker():
            return False

        pages_required = math.ceil(file_size/256)
        self.logger.info(f"Upload requires {pages_required} page writes")

        # over total number of bytes
        with tqdm(total=pages_required, unit="pages", unit_scale=True, desc="Uploading Actuator Firmware") as pbar:
            while page_counter < pages_required:

                    # fill byte data
                concat_chunk = []
                # take each pair and make it into a 16bit value
                while len(concat_chunk) < 64: # 128 bytes
                    if byte_counter >= file_size:
                        concat_chunk.append(0xffff)
                    elif byte_counter+1 >= file_size:
                        concat_chunk.append(file_data[byte_counter] << 8 | 0xff) 
                    else:
                        concat_chunk.append(file_data[byte_counter] << 8 | file_data[byte_counter+1])
                    byte_counter += 2

                concat_chunk.insert(0,self._command_handler.commands['firmware_update_command']) # this has to be the first element every time

                self._communication_handler.send_data(concat_chunk,CommandType.FIRMWARE_COMMAND.value)
                # page_byte_counter += 128

                time.sleep(0.01)

                self.logger.info(f"Sent page {page_counter} of {pages_required}")

                # a full page has been uploaded
                # if not self.flashing_ack_checker():
                #     return False
                # while not self.flashing_ack_checker():
                #     time.sleep(0.1)

                self.logger.info(f"Page {page_counter} of {pages_required} uploaded - ACK received")

                time.sleep(0.01)

                # reset page_byte_counter
                # page_byte_counter = 0
                page_counter += 0.5 # update by 0.5 pages becaause sending 128 bytes (1/2 page) instead of 256 bytes (full page)
                pbar.update(0.5)

                if page_counter % 50 == 0:
                    time.sleep(0.1)

        # send 0000 to end the firmware update process
        eof_list = [0x0,0x0]
        self._communication_handler.send_data(eof_list,CommandType.FIRMWARE_COMMAND.value)
        self.logger.info("Firmware Update is in progress..")
