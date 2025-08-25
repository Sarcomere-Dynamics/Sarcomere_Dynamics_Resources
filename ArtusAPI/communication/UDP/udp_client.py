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
import sys


class UDPCLient:

    def __init__(
        self,
        HEADER=64,  # Header size
        FORMAT="utf-8",  # Format of the message
        target_ssid="Artus3DTester",
        password=None,  # possibility to take in password
        port=3211,
        logger=None,
        hand_side="RIGHT",
        hand_type="ARTUS LITE"
    ):

        self.HEADER = HEADER
        self.FORMAT = FORMAT
        self.target_ssid = target_ssid
        self.password = password
        self.hand_side = hand_side
        self.hand_type = hand_type
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

        connection = None

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
            # Check if already connected to the target network
            try:
                # Also check ethernet connections
                result = subprocess.run('nmcli -t -f device,state,type connection show --active', shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if 'ethernet' in line.lower() and 'activated' in line:
                            self.logger.info("Already connected via ethernet")
                            return 'ethernet'
                # Get current connection info
                result = subprocess.run('nmcli -t -f active,ssid dev wifi', shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.startswith('yes:') and self.target_ssid in line:
                            self.logger.info(f"Already connected to {self.target_ssid}")
                            return 'wifi'
                
            except Exception as e:
                self.logger.warning(f"Could not check current network status: {e}")
            # Linux uses the "nmcli" command to connect to Wi-Fi networks
            connect_command = f'nmcli dev wifi connect "{self.target_ssid}"'

            # input password
            if not self.password:
                self.password = input("type ssid password:")
            elif self.password:
                connect_command += f' password "{self.password}"'

            subprocess.run(connect_command, shell=True)

            time.sleep(1)

            # clear password
            # self.password = None

        else:
            # TODO logging
            self.logger.error("Unsupported operating system")

        # wait X seconds to connect
        time.sleep(0.1)

        return None

    def _get_device_ip(self):
        if self.connection == 'ethernet':
            # Get IP from ethernet interface
            result = subprocess.run("ip -4 addr show dev $(ip -o link show | awk -F': ' '/ether/ {print $2}' | head -n1) \
   | grep -oP '(?<=inet\s)\d+(\.\d+){3}'"
, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"Ethernet IP: {result.stdout}")
                ip = result.stdout.strip().split('\n')[0]  
                # # Extract IP from output like "1.0.0.0 via 192.168.1.1 dev eth0 src 192.168.1.100"
                # for part in result.stdout.split():
                #     if part.startswith('src'):
                #         ip_index = result.stdout.split().index(part) + 1
                #         if ip_index < len(result.stdout.split()):
                #             ip = result.stdout.split()[ip_index]
                #             break
                # else:
                #     raise Exception("Could not parse ethernet IP")
            else:
                raise Exception("Failed to get ethernet route")  
        else:
            # Get IP via wifi or default method
            ip = (
                (
                    [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
                    or [[(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]
                )
                + ["no IP found"]
            )[0]

        if ip == None:
            self.logger.error("cannot get local ip.")
            exit()

        self.ip = ip

        common = ".".join([str(x) for x in self.ip.split(".")[:3]])

        procs = []
        for i in range(1, 255):
            # [1,254] inclusive, not including .0 and .255 which are reserved.
            proc = subprocess.Popen(f'echo "?" | nc -w5 -u {common}.{i} 3210', shell=True, stdout=subprocess.PIPE)
            procs.append((i, proc))

        handIp = None

        for i, proc in procs:
            ret = proc.stdout.read()
            if ret.startswith(b"Sarcomere Dynamics"):
                if self.hand_side == "RIGHT" and ret.endswith(b"RIGHT"):
                    handIp = f"{common}.{i}"
                    break
                elif self.hand_side == "LEFT" and ret.endswith(b"LEFT"):
                    handIp = f"{common}.{i}"
                    break
                else:
                    self.logger.warning(f"Hand side {self.hand_side} not found in {ret.decode()}")
            elif ret != b"":
                self.logger.debug(f"{common}.{i} {ret.decode()}")

        self.device_ip = handIp

    """ Start server and listen for connections """

    def open(self):
        # Refresh network interfaces on the OS to ensure up-to-date network info
        sys_platform = platform.system()

        if shutil.which("nc"):
            pass
        else:
            self.logger.error('Command "nc" is not found. Required for quickly finding device ip address. Mission abort.')
            exit()

        # if sys_platform == "Windows":
        #     os.system("ipconfig /release")
        #     os.system("ipconfig /renew")
        # elif sys_platform == "Linux":
        #     os.system("nmcli networking off")
        #     time.sleep(1)
        #     os.system("nmcli networking on")
        # elif sys_platform == "Darwin":
        #     os.system("sudo ifconfig en0 down")
        #     time.sleep(1)
        #     os.system("sudo ifconfig en0 up")
        time.sleep(5)  # this is a must, anything [Errno 101] other wise

        # look for wifi
        self.connection = self._join_target_network()

        # get IP addresses associated with local machine and device
        self._get_device_ip()

        # create server socket
        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        # self.socket.setblocking(False)  # blocking timeout to connect
        self.socket.settimeout(10)  # blocking timeout to connect
        self.logger.debug("self ip: ", (self.ip, self.port))
        self.logger.debug("target ip", (self.device_ip, self.device_port))

        if not isinstance(self.ip, str) or self.ip.count(".") != 3:
            raise RuntimeError("cannot find computer ip.")

        if not isinstance(self.device_ip, str) or self.device_ip.count(".") != 3:
            raise RuntimeError("cannot find hand ip.")
            

        self.socket.bind((self.ip, self.port))

        self.socket.sendto(b"?\n", (self.device_ip, self.device_port))
        self.socket.recv(128)

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


if __name__ == "__main__":

    comms = UDPCLient(target_ssid="secret_ssid")

    comms.open()

    try:
        while True:

            bytesAddressPair = comms.socket.recvfrom(1024)

            message = bytesAddressPair[0]
            address = bytesAddressPair[1]

            clientMsg = "Message from Client:{}".format(message)
            clientIP = "Client IP Address:{}".format(address)

            print(clientIP, clientMsg)
    finally:
        comms.close()
