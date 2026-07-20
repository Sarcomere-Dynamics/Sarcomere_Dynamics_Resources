"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Minimal single-client TCP server used to receive raw hand tracking data feeds."""

import socket
import time
import threading


import re

class TCPServer:
    """A minimal single-client TCP server for streaming raw text data.

    Binds to a host/port, accepts one client connection on a background
    thread, and exposes simple receive/send helpers for exchanging
    utf-8-encoded text with that client.
    """

    def __init__(self,
                 host='127.0.0.1',
                 port=65432):
        """Stores connection parameters; the socket is created in create().

        Args:
            host: Local address to bind the server to.
            port: Local TCP port to bind the server to.
        """
        self.host = host
        self.port = port
        self.socket = None

        self.conn = False

    def create(self):
        """Creates, binds, and listens on the server socket, then waits for a client.

        Spawns a background thread (_wait_for_connection) that blocks until
        a client connects, so this method returns immediately.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,2)
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        print('Waiting for a connection...')
        threading.Thread(target=self._wait_for_connection).start()
        
    def _wait_for_connection(self):
        """Blocks until a client connects, then stores the connection and address.

        Intended to run as a background thread target started by create().
        """
        self.conn, self.addr = self.socket.accept()
        print(f'Connected to {self.addr} on port {self.port}')

    def receive(self):
        """Reads one chunk of data from the connected client.

        Returns:
            The received data decoded as utf-8, or None if there is no
            active connection or the client sent no data (e.g. it
            disconnected).
        """
        if self.conn:
            data = self.conn.recv(4096) #  2500-3000 bytes per message
            # data = self.conn.recv(10000)
            if not data:
                return None
            # return data
            return data.decode('utf-8')

    def send(self, data):
        """Sends a utf-8-encoded string to the connected client.

        Args:
            data: The string to send. No-op if there is no active
                connection.
        """
        if self.conn:
            self.conn.sendall(bytes(data, 'utf-8'))

    def close(self):
        """Closes the client connection and the listening socket, if open."""
        if self.conn:
            self.conn.close()
            self.socket.close()




def test_receive_data():
    """Manually exercises TCPServer by printing received data and parsed thumb values."""
    tcp_server = TCPServer(port=65432)
    tcp_server.create()
    while True:
        data = tcp_server.receive()
        print(data)
   
        if data:
            try:
                data = _extract_between_orientation_and_end(data)
                # data = data.replace(")", "")
                data = data.split(",")
                # for element in data:
                #     element = element.replace("(", "")
                # print(data[6:9])
                # print(data)
                print("thumb: ", data[0:4])
                # print("index: ", data[4:7])
                # print("middle: ", data[7:10])
                # print("ring: ", data[10:13])
                # print("pinky: ", data[13:16])
            except:
                pass
        time.sleep(0.2)
        
def _extract_between_orientation_and_end(s):
    """Extracts the substring between the 'orientation:' and 'end' markers.

    Args:
        s: The raw string to search.

    Returns:
        The stripped substring found between 'orientation:' and 'end', or
        None if the pattern is not found.
    """
    pattern = r'orientation:(.*?)end'
    match = re.search(pattern, s, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None




def test_streaming_bandwidth():
    """Measures and prints the incoming message rate (Hz) over a 20-second window."""
    tcp_server = TCPServer(port=65432)
    tcp_server.create()

    count = 0

    start_time = time.perf_counter()
    while time.perf_counter() - start_time < 20:
        data = tcp_server.receive()
   
        # if data != None or data != "":
        if "boneId" in data:
            count += 1

    print("Bandwidth: ", count/20, " Hz")


def testing_multiple_port_data_receive():
    """Manually exercises two TCPServer instances receiving left/right hand data concurrently."""
    tcp_server_left = TCPServer()
    tcp_server_right = TCPServer(port=1234)
    tcp_server_left.create()
    tcp_server_right.create()

    while True:

        ########### Left Hand Data ####################
        data = tcp_server_left.receive()
        if data:
            try:
                data = _extract_between_orientation_and_end(data)
                # data = data.replace(")", "")
                data = data.split(",")
                # for element in data:
                #     element = element.replace("(", "")
                # print(data[6:9])
                # print(data)

                print("******* Left Hand Data *******")
                print("thumb: ", data[0:4])
                print("index: ", data[4:7])
                print("middle: ", data[7:10])
                print("ring: ", data[10:13])
                print("pinky: ", data[13:16])
            except:
                pass
        time.sleep(0.2)


        ########### RIght Hand Data #########################
        try:
            data = tcp_server_right.receive()
            print(data)
        except:
            pass
        if data:
            try:
                data = _extract_between_orientation_and_end(data)
                # data = data.replace(")", "")
                data = data.split(",")
                # for element in data:
                #     element = element.replace("(", "")
                # print(data[6:9])
                # print(data)
                print("******* Right Hand Data *******")
                print("thumb: ", data[0:4])
                print("index: ", data[4:7])
                print("middle: ", data[7:10])
                print("ring: ", data[10:13])
                print("pinky: ", data[13:16])
            except:
                pass
        time.sleep(0.2)


if __name__ == "__main__":
    test_receive_data()
    # test_streaming_bandwidth()
    # testing_multiple_port_data_receive()
