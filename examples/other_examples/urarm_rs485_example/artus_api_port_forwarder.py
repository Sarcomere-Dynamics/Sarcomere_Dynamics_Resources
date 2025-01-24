import os
import subprocess
import serial
import time


class ArtusAPIPortForwarder:

    def __init__(self,
                 robot_ip = "192.168.194.129", # robot ip address (change this to the robot's ip address)
                 local_device_name = "/tmp/ttyUR"): # temporary device name
        self.robot_ip = robot_ip
        self.local_device_name = local_device_name
        self.socat_process = None
        self.ser = None
        self._run_socat()


    def _run_socat(self):
        socat_command = f"socat pty,link={self.local_device_name},raw,ignoreeof,waitslave tcp:{self.robot_ip}:54329"
        self.socat_process = subprocess.Popen(socat_command, shell=True)
        time.sleep(2)


    def get_local_device_name(self):
        return self.local_device_name
    



def test_port_forwarder():
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