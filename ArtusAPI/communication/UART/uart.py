"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import serial
import logging
import time
from tqdm import tqdm


class UART:
    def __init__(self,
                 port='COM9',
                 baudrate=921600, #115200, 
                 timeout=0.5,
                 logger = None):
        
        # automatically connect to the first available port
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.esp32 = serial.Serial(baudrate=self.baudrate, timeout= self.timeout)

        # required delays for sending message
        self.timer_send = 0.003
        self.timer_recv = self.timer_send*4
        self.maximum_freq = 700 # hz

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def open(self):
        try:
            self.esp32.port=self.port
            self.esp32.close()
            self.esp32.open()
            self.logger.info(f"Opening {self.port} @ {self.baudrate} baudrate")
            self.esp32.flush()
            msg_bytes = self.esp32.read_all()
        except Exception as e:
            self.logger.error(e)
            self.logger.error(f'Error opening port {self.port} ......... QUITTING ........')
            for i in range(25):
                time.sleep(0.1)
            quit()

    def send(self, data:bytearray):
        # print(data)
        try:
            self.esp32.write(data)
            self.esp32.flush()

            # required delay
            t = time.perf_counter()
            while time.perf_counter() - t < self.timer_send:
                pass
        except Exception as e:
            self.logger.error(f'Unable to send command through {self.port}')
            self.logger.error(e)

    def receive(self,size=65):

        # required delay
        # t = time.perf_counter()
        # while time.perf_counter() - t < self.timer_recv:
        #     pass
        try:
            x = time.perf_counter()
            # # print(f'time start: {x}')
            # while self.esp32.in_waiting < size:
            #     if time.perf_counter() - x > 0.001:
            #         break
            # print(f'elapsed time: {time.perf_counter() - x}')
            # time.sleep(0.03)
            # check data
            if self.esp32.in_waiting >= size: # get data if greater or equal to 65
                msg_bytes = self.esp32.read(size)
                # print(msg_bytes)
                return msg_bytes
            elif self.esp32.in_waiting > 0:
                # msg_bytes = self.esp32.read_all()
                # self.logger.warning(f"Incomplete data received - package size = {(self.esp32.in_waiting)}")
                return None
            else: # non blocking
                # self.logger.warning(f"No data available to receive")
                return None
        except Exception as e:
            self.logger.warning(f"No data available to receive {e}")
            self.logger.error(e)            

    def close(self):
        self.esp32.close()


def test_serial_receive():
    esp32_communication = UART()
    esp32_communication.start()
    while True:
        msg = esp32_communication.receive()
        if msg != "":
            print(msg)

def test_serial_send():
    esp32_communication = UART()
    esp32_communication.start()
    while True:
        esp32_communication.send("hello\n")
        time.sleep(1)


if __name__ == "__main__":
    test_serial_receive()
    # test_serial_send()