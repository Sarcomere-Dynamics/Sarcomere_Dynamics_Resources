"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

"""Forwards a UR robot's TCP-exposed RS485 line to a local serial device via socat.

Wraps a `socat` subprocess that bridges a TCP socket on the robot
(port 54329, used to reach its onboard RS485 bus) to a local
pseudo-terminal device, so existing serial-based ArtusAPI code can talk
to the ARTUS hand as if it were connected locally.
"""

import os
import subprocess
import serial
import time


class ArtusAPIPortForwarder:
    """Bridges a UR robot's RS485-over-TCP port to a local serial device.

    On construction, starts a `socat` subprocess that creates a local
    pseudo-terminal linked to the robot's TCP port, allowing serial
    libraries (e.g. pyserial) to communicate with the ARTUS hand attached
    to the robot's RS485 bus.
    """

    def __init__(self,
                 robot_ip = "192.168.194.129", # robot ip address (change this to the robot's ip address)
                 local_device_name = "/tmp/ttyUR"): # temporary device name
        """Starts the socat bridge from the robot's TCP port to a local device.

        Args:
            robot_ip: IP address of the UR robot exposing the RS485 line
                over TCP.
            local_device_name: Path of the local pseudo-terminal device to
                create (e.g. via a symlink) for serial access.
        """
        self.robot_ip = robot_ip
        self.local_device_name = local_device_name
        self.socat_process = None
        self.ser = None
        self._run_socat()


    def _run_socat(self):
        """Launches the socat subprocess linking the local device to the robot.

        Runs `socat pty,link=<local_device_name>,raw,ignoreeof,waitslave
        tcp:<robot_ip>:54329` in the background and waits 2 seconds for
        the link to come up before returning.
        """
        socat_command = f"socat pty,link={self.local_device_name},raw,ignoreeof,waitslave tcp:{self.robot_ip}:54329"
        self.socat_process = subprocess.Popen(socat_command, shell=True)
        time.sleep(2)


    def get_local_device_name(self):
        """Returns the local pseudo-terminal device path for serial access.

        Returns:
            str: Path to the local device created by socat (e.g.
            "/tmp/ttyUR").
        """
        return self.local_device_name




def test_port_forwarder():
    """Manually exercises the port forwarder by sending/receiving serial data.

    Starts an ArtusAPIPortForwarder to ROBOT_IP, opens the resulting local
    device with pyserial, and loops forever writing a test message and
    printing whatever is read back. Intended to be run as a standalone
    script for manual verification, not as an automated test.
    """
    ROBOT_IP = "192.168.194.129"
    artusAPIPortForwarder = ArtusAPIPortForwarder(robot_ip=ROBOT_IP)

    local_device_name = artusAPIPortForwarder.get_local_device_name()
    print(f"Local device name: {local_device_name}")
    ser = serial.Serial(local_device_name, baudrate=921600, timeout=1)

    # Step 3: Send data
    data_to_send = b"Hello Robot\n"
    print(f"Sending: {data_to_send.decode()}")
    while True:
        ser.write(data_to_send)
        print("Data sent.")
        time.sleep(1)

        # Step 4: Receive data
        data_received = ser.readline()
        print(f"Received: {data_received}")
        time.sleep(1)



if __name__ == "__main__":
    test_port_forwarder()