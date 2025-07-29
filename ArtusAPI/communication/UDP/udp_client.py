"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import socket
import time
import os
import subprocess
import platform
import shutil
import logging


class UDPCLient:

    def __init__(
        self,
        HEADER=64,  # Header size
        FORMAT="utf-8",  # Format of the message
        target_ssid="Artus3DTester",
        password=None,  # possibility to take in password
        port=3211,
        logger=None,
    ):

        self.HEADER = HEADER
        self.FORMAT = FORMAT
        self.target_ssid = target_ssid
        self.password = password

        self.device_ip = None
        self.device_port = 3210

        self.ip = None
        self.port = port
        self.socket = None

        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def _join_target_network(self):
        sys = platform.system()

        if sys == "Windows":
            # set profile location
            self.wifi_profile = os.getcwd() + self.target_ssid + ".xml"

            # prompt user if first time
            if not os.path.isfile(os.getcwd() + "\\Wi-Fi-" + self.target_ssid + ".xml"):
                # wait for connecting first time
                input("First time Connection, Please connect to Artus Hand and enter Y when done")

                time.sleep(1)

                # save profile
                save_profile_cmd = f"netsh wlan export profile {self.target_ssid} key=clear folder={os.getcwd()}"
                subprocess.run(save_profile_cmd, shell=True)

                time.sleep(1)

                if not os.path.isfile(os.getcwd() + "\\Wi-Fi-" + self.target_ssid + ".xml"):
                    # TODO logging
                    self.logger.warning(f"Unable to create wifi profile")

            else:
                # refresh wifi scan

                # connect to profile
                connect_command = f"netsh wlan connect ssid={self.target_ssid} name={self.target_ssid} interface=Wi-Fi"
                subprocess.run(connect_command, shell=True)

        elif sys == "Linux":
            # Linux uses the "nmcli" command to connect to Wi-Fi networks
            connect_command = f'nmcli dev wifi connect "{self.target_ssid}"'

            # input password
            if not self.password:
                self.password = input("type ssid password:")
            elif self.password:
                connect_command += f' password "{self.password}"'

            subprocess.run(connect_command, shell=True)

            # clear password
            # self.password = None

        else:
            # TODO logging
            self.logger.error("Unsupported operating system")

        # wait X seconds to connect
        for i in range(10):
            time.sleep(0.01)

    def _get_device_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.ip = [int(x) for x in s.getsockname()[0].split(".")]
        s.close()

        common = ".".join([str(x) for x in self.ip[:3]])

        procs = []
        for i in range(1, 255):
            # [1,254] inclusive, not including .0 and .255 which are reserved.
            proc = subprocess.Popen(f'echo "?" | nc -w1 -u {common}.{i} 3210', shell=True, stdout=subprocess.PIPE)
            procs.append((i, proc))

        handIp = None

        for i, proc in procs:
            ret = proc.stdout.read()
            if ret.startswith(b"Sarcomere Dynamics"):
                handIp = f"{common}.{i}"

        self.device_ip = handIp

    """ Start server and listen for connections """

    def open(self):
        try:
            # Refresh network interfaces on the OS to ensure up-to-date network info
            sys_platform = platform.system()

            if shutil.which("nc"):
                pass
            else:
                print('Command "nc" is not found.')
                print("Required for quickly finding device ip address.")
                print("Mission abort.")
                exit()

            if sys_platform == "Windows":
                os.system("ipconfig /release")
                os.system("ipconfig /renew")
            elif sys_platform == "Linux":
                os.system("nmcli networking off")
                time.sleep(1)
                os.system("nmcli networking on")
            elif sys_platform == "Darwin":
                os.system("sudo ifconfig en0 down")
                time.sleep(1)
                os.system("sudo ifconfig en0 up")
            time.sleep(2)

            # look for wifi
            self._join_target_network()

            # get IP addresses associated with local machine and device
            self._get_device_ip()

            # TCP tuple
            self.esp = (self.device_ip, self.device_port)

            print(self.esp)

            # create server socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setblocking(False)  # blocking timeout to connect
            self.socket.bind((self.ip, self.port))

            self.socket.sendto(b"?\n", (self.device_ip, self.device_port))
        except Exception as e:
            self.logger.error(f"No Network named {self.target_ssid}")
            print(e)

    def close(self):
        self.socket.close()
        system = platform.system()

        if system == "Windows":
            # Windows uses the "netsh" command to disconnect from Wi-Fi networks
            disconnect_command = f'netsh wlan disconnect interface="Wi-Fi" ssid="{self.target_ssid}"'
            subprocess.run(disconnect_command, shell=True)

        elif system == "Linux":
            # Linux uses the "nmcli" command to disconnect from Wi-Fi networks
            disconnect_command = f'nmcli con down id "{self.target_ssid}"'
            subprocess.run(disconnect_command, shell=True)

        else:
            # TODO logging
            self.logger.error("Unsupported operating system")
            return

        self.logger.info(f"Disconnected from {self.target_ssid}")
        time.sleep(2)  # Wait for a few seconds for the disconnect to take effect

        return

    def receive(self, size=65):
        try:
            byte_msg = self.socket.recv(size)  # receive bytes

            if len(byte_msg) == size:  # receive the first 65 bytes
                return byte_msg

            else:
                self.logger.warning(f"Incomplete data received - package size = {len(byte_msg)}")
                return None

        except TimeoutError:
            None
        except Exception as e:
            # TODO logging
            self.logger.warning(f"No data available to receive {e}")
            return None

    def send(self, data: bytearray):
        try:
            self.socket.sendto(data, (self.device_ip, self.device_port))
        except Exception as e:
            # TODO insert error logging
            self.logger.error(f"Unable to send data")
            None
