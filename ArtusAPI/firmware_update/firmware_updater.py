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
import platform
import subprocess
from tqdm import tqdm

BYTES_CHUNK = 32
UPLOAD_CHUNKS_COMMAND = 0x30
FINISH_CHUNKS_COMMAND = 0x32

class FirmwareUpdater:

    def __init__(self,
                 communication_handler = None,
                 command_handler = None,
                 file_location = None,
                 logger = None
                    ):
        
        self._communication_handler = communication_handler
        self._command_handler = command_handler
        self.file_location = file_location

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def get_bin_file_info(self):
        # get the file location and size for comparison later
        file_size = int(os.path.getsize(self.file_location))

        print(f'Bin file size = {file_size}')

        # open file and get data
        return file_size


    def update_firmware(self,file_size):
        
        time.sleep(0.02)
        
        # wait for ACK back before sending data
        self.wait_for_ack()

        # load File Data
        file = open(self.file_location,'rb')
        file_data = file.read()
        file.close()

        # number of 32B chunks needed
        chunks_required = int(file_size/BYTES_CHUNK) + 1
        print((f'Num of chunks to send: {chunks_required}'))

        # send actual binary data - note 32bytes because length of command is 34
        # init counter
        i = 0
        ret = False
        with tqdm(total=len(file_data), unit="B", unit_scale=True, desc="Uploading") as pbar:

            while i < len(file_data):
                
                # if not enough file data for 32B, fill with 0xFFs
                if i+BYTES_CHUNK > file_size:
                    chunk = list(file_data[i:])
                    while len(chunk) < BYTES_CHUNK: # Always make sure 32B of valid data
                        chunk.append(0xFF)
                
                else:
                    chunk = list(file_data[i:i+BYTES_CHUNK])
                
                
                # checksum last value
                csum = self.calc_check_sum(chunk)
                # set 33rd byte as checksum value
                chunk.append(csum)

                # print(f'{chunk} {len(chunk)}')

                # send data
                self._communication_handler.send_data(chunk,1)

                # sleep
                time.sleep(0.008)

                # print([hex(x) for x in chunk])
                    
                # wait for ack
                ret = self.wait_for_ack()
                # debug print
                # print(f'CHUNKS LEFT {chunks_required} {csum}')

                if ret:
                    chunks_required -= 1
                    i += BYTES_CHUNK
                    csum = 0
                    ret = 0
                pbar.update(BYTES_CHUNK)

                time.sleep(0.01)

        print(f'Firmware update in progress..')

    def calc_check_sum(self,data:list)->int:
        checksum = 0
        for i in data:
            checksum ^= i
        return checksum

    def wait_for_ack(self):
        while 1:
            tmp,rc_csum = self._communication_handler.receive_data()
            if tmp == 2:           
                if rc_csum[0] == 1:
                    return True
                else:
                    self.logger.warning(f'firmware flash checksum error')
                    return False
            elif tmp == 9:
                self.logger.error(f'firmware flash failed')
                return False
            time.sleep(0.02)


def test_firmware_updater():
    my_fp = "/home/ryan/Documents/Artus-3D-actuator-fw-F3/build/actuator_mx_build.bin"
    firmware_updater = FirmwareUpdater(communication_channel_identifier='ArtusLite000',communication_method='WiFi',file_location=my_fp)
    firmware_updater.update_firmware()

if __name__ == "__main__":
    test_firmware_updater()
