"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

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
    """Uploads firmware binaries to an ARTUS hand over Modbus RTU/TCP.

    Streams a `.bin` file to the hand's master board in fixed-size
    chunks, polling the actuator state after each page (or half-page) is
    sent to confirm the firmware update flash acknowledged the write.

    Attributes:
        _communication_handler: Communication handler used to send
            firmware data and poll robot state.
        _command_handler: Command handler providing the firmware update
            opcode.
        file_location: Path to the firmware binary file to upload.
        logger: Logger used for progress/error messages.
    """

    def __init__(self,
                 communication_handler:NewCommunication = None,
                 command_handler = None,
                 file_location = None,
                 logger = None):
        """Initializes the firmware updater.

        Args:
            communication_handler: Communication handler used to send
                firmware data and poll robot state.
            command_handler: Command handler providing the firmware
                update opcode.
            file_location: Path to the firmware binary file to upload.
            logger: Logger to use; a module-level logger is created if
                not provided.
        """
        self._communication_handler = communication_handler
        self._command_handler = command_handler
        self.file_location = file_location
        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def get_bin_file_info(self):
        """Reads and logs the size of the configured firmware binary.

        Returns:
            The size of the file at ``self.file_location``, in bytes.
        """
        file_size = int(os.path.getsize(self.file_location))
        self.logger.info(f"Bin file size = {file_size} @ location {self.file_location}")
        return file_size

    def flashing_ack_checker(self):
        """Polls the robot state until the flash erase/write is acknowledged.

        Blocks, checking the actuator state every 5 seconds, until the
        hand reports ``ACTUATOR_FLASHING_ACK`` (success) or
        ``ACTUATOR_ERROR`` (failure). Logs and continues on transient
        state-check exceptions.

        Returns:
            True once ``ACTUATOR_FLASHING_ACK`` is observed, False if
            ``ACTUATOR_ERROR`` is observed.
        """
        while True:
            self.logger.info(f"entered flashing_ack_checker")
            try:
                ret = self._communication_handler._check_robot_state()
                self.logger.info(f"return from check_robot_state is: {ret}")
                if ret == ActuatorState.ACTUATOR_FLASHING_ACK.value:
                    return True
                elif ret == ActuatorState.ACTUATOR_ERROR.value:
                    self.logger.error(f"Error: {ret}")
                    return False
                elif ret == ActuatorState.ACTUATOR_FLASHING.value:
                    self.logger.info(f'Erasing Flash..')
            except Exception as e:
                self.logger.error(f"Error checking robot state: {e}")
                continue
            time.sleep(5)
    
    def update_firmware_piecewise(self,file_size):
        """Uploads firmware to brushless drivers through the masterboard, one page at a time.

        Reads the binary at ``self.file_location``, and for each 256-byte
        page waits for a flashing acknowledgment before sending the next
        page, updating a progress bar as pages complete. Sends a
        terminating ``[0x0, 0x0]`` chunk once all pages are uploaded.

        Args:
            file_size: Size of the firmware binary in bytes, used to
                compute the number of 256-byte pages required.

        Returns:
            False if the initial or any per-page flashing acknowledgment
            fails; otherwise returns None after the upload completes.
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
        """Uploads firmware binary data to the master board in half-page chunks.

        Only manages sending the actual binary data to the master; it
        does not start the firmware update process on the master. Reads
        the binary at ``self.file_location`` and streams it in 128-byte
        (half-page) chunks, waiting for the initial flashing
        acknowledgment before starting and pausing briefly every 50
        (half-)pages. Sends a terminating ``[0x0, 0x0]`` chunk once the
        upload completes.

        Args:
            file_size: Size of the firmware binary in bytes, used to
                compute the number of 256-byte pages required.

        Returns:
            False if the initial flashing acknowledgment fails;
            otherwise returns None after the upload completes.
        """
        byte_counter = 0
        page_counter = 0
        ret = None

        file = open(self.file_location,'rb')
        file_data = file.read()
        self.logger.info(f"file read complete")
        file.close()

        time.sleep(1)

        # wait for the initial communication/erase function
        if not self.flashing_ack_checker():
            self.logger.info(f"if NOT self.flashing_ack_checker()")
            return False

        self.logger.info(f"if self.flashing_ack_checker()")
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
