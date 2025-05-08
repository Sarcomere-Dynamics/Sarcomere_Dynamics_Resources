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


from .UART.uart import UART
from .WiFi.wifi_server import WiFiServer

STARTUP_ACK = 0xaa
NORMAL_ACK = 0x2

class Communication:
    """
    This communication class contains two communication methods:
        - UART
        - WiFi
    """
    def __init__(self,
                 communication_method='UART',
                 communication_channel_identifier='COM9',logger = None,baudrate = 921600,robot_type='artus_lite'):
        # initialize communication
        self.communication_method = communication_method
        self.communication_channel_identifier = communication_channel_identifier
        self.communicator = None
        self.baudrate = baudrate
        self.robot_type = robot_type
        # setup communication
        self._setup_communication()
        # params
        self.command_len = 33
        if robot_type == 'artus_lite':
            self.recv_len = 65
        elif robot_type == 'artus_lite_plus':
            self.recv_len = 77

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    
    ################# Communication: _Initialization ##################
    def _setup_communication(self):
        """
        Initialize communication based on the desired method; UART or WiFi
        """
        # setup communication based on the method
        if self.communication_method == 'UART':
            self.communicator = UART(port=self.communication_channel_identifier,baudrate=self.baudrate)
        elif self.communication_method == 'WiFi':
            self.communicator = WiFiServer(target_ssid=self.communication_channel_identifier)
        elif self.communication_method == 'None':
            pass
        else:
            raise ValueError("Unknown communication method")
    
    ################# Communication: Private Methods ##################
    def _list_to_byte_encode(self,package:list) -> bytearray:
        # data to send
        send_data = bytearray(self.command_len+1)

        # append command first
        send_data[0:1] = package[0].to_bytes(1,byteorder='little')

        for i in range(len(package)-1):
            try:
                send_data[i+1:i+2] = int(package[i+1]).to_bytes(1,byteorder='little',signed=True)
            except OverflowError as e:
                send_data[i+1:i+2] = int(package[i+1]).to_bytes(1,byteorder='little',signed=False)


        # set last value to '\n'
        send_data[-1:] = '\0'.encode('ascii')
        
        # print(send_data)
        # return byte array to send
        return send_data
    
    def _byte_to_list_decode(self,package:bytearray) -> tuple:
        recv_data = []
        i = 0

        if self.robot_type == 'artus_lite':
            # BYTE 0 : ACK
            # BYTE 1 - 16 : 8 BIT POSITION
            # BYTE 17 - 49 : 16 BIT POSITION
            # BYTE 50 - 65 : 8 BIT POSITION
            while i < 65:
                if 17 <= i <= 47: # 16 bit signed integer to int
                    recv_data.append(package[i].from_bytes(package[i:i+2], byteorder='big', signed=True))
                    i+=2
                else:   # 8 bit signed integer to int
                    recv_data.append(package[i].from_bytes(package[i:i+1],byteorder='little',signed=True))
                    i+=1

            
            if len(recv_data) != 49:
                raise ValueError(f"Artus Lite data length mismatch: {len(recv_data)}, expected 49")
        
        elif self.robot_type == 'artus_lite_plus':
            # BYTE 0 : ACK
            # BYTE 1 - 16 : 8 BIT POSITION
            # BYTE 17 - 76 : 4 byte force feedback (x,y,z)
            while i < 76:
                if 17 <= i <= 75:  # 4-byte signed integer to int (force feedback x, y, z)
                    recv_data.append(float(struct.unpack('<f', package[i:i+4])[0]))
                    i += 4
                else:  # 8-bit signed integer to int
                    recv_data.append(int.from_bytes(package[i:i+1], byteorder='little', signed=True))
                    i += 1

            if len(recv_data) != 32:
                raise ValueError(f"Artus Lite Plus data length mismatch: {len(recv_data)}, expected 32")
        

        # extract acknowledge value
        ack = recv_data[0]
        del recv_data[0] # delete 0th value from array

        # print(f'recv_data = {recv_data}')

        return ack,recv_data


    ################# Communication: Public Methods ##################
    def open_connection(self):
        """
        start the communication
        """
        try:
            self.communicator.open()
        except Exception as e:
            self.logger.error("unable to connect to Robot")
            print(e)

    def send_data(self, message:list,no_debug=0):
        """
        send message
        """
        try:
            # Test
            self.logger.info(f'data sent to hand {message}')
            if not no_debug:
                print(f'data sent to hand = {message}')
            byte_msg = self._list_to_byte_encode(message)
            self.communicator.send(byte_msg)
            return True
        except Exception as e:
            self.logger.warning("unable to send command")
            print(e)
            pass
        return False

    def receive_data(self) -> list:
        """
        receive message
        """
        byte_msg_recv = None
        try:    
            byte_msg_recv = self.communicator.receive(self.recv_len)
            if not byte_msg_recv:
                # self.logger.warning("No data received")
                return None,None
            ack,message_received = self._byte_to_list_decode(byte_msg_recv)
            if ack == 9:
                self.logger.warning("[E] error ack")
            # print(ack)
        except Exception as e:
            self.logger.warning("unable to receive message")
            print(e)
            return None
        return ack,message_received

    def close_connection(self):
        self.communicator.close()


    def wait_for_ack(self,timeout=144,visual=False,value=NORMAL_ACK):
        start_time = time.perf_counter()
        if visual:
            with tqdm(total=timeout, unit="s", desc="Waiting for ack") as pbar:
                while 1:
                    tmp,rc_csum = self.receive_data()
                    if value == NORMAL_ACK:
                        if tmp is not None:
                            self.logger.info(f'ack received in {time.perf_counter() - start_time} seconds')
                            return 1
                    elif tmp == value:
                        self.logger.info(f'ack received in {time.perf_counter() - start_time} seconds')
                        return 1
                    time.sleep(0.01)
                    if time.perf_counter() - start_time > timeout:
                        pbar.close()
                        self.logger.error('timeout error\r\ntimeout error\r\ntimeout error')
                        return 0
                    pbar.update(0.01)
        else:
            while 1:
                tmp,rc_csum = self.receive_data()
                if tmp is not None:
                    self.logger.info(f'ack received in {time.perf_counter() - start_time} seconds')
                    return 1
                if time.perf_counter() - start_time > timeout:
                    self.logger.error('timeout error\r\ntimeout error\r\ntimeout error')
                    return 0
                time.sleep(0.01)

##################################################################
############################## TESTS #############################
##################################################################
def test_wifi():
    communication = Communication(communication_method='WiFi', communication_channel_identifier='Artus3D')
    communication.open_connection()

def test_uart():
    communication = Communication(communication_method='UART', communication_channel_identifier='/dev/ttyUSB0')
    communication.open_connection()
    time.sleep(1)
    x = [0]*33
    x[0] = 210
    while True:
        communication.send_data(x)
        i=0
        while i < 6:

            # time.sleep(0.002)
            # print(communication.receive_data()[0])
            if communication.receive_data() is not None:
                i+=1
        time.sleep(0.5)

if __name__ == "__main__":
    # test_wifi()
    test_uart()



    