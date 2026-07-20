"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2026, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import logging
import time
import struct
from tqdm import tqdm

from .RS485_RTU.rs485_rtu import RS485_RTU
from .Modbus_TCP.modbus_tcp import ModbusTCP
from ..common.ModbusMap import ModbusMap,ActuatorState,CommandType,TrajectoryReturn

class NewCommunication:
    """Transport-agnostic wrapper used by ArtusAPI_V2 to talk to an ARTUS hand.

    Selects and owns a concrete communicator (RS485_RTU or ModbusTCP) based on
    `communication_method` and exposes a uniform send/receive/state-polling
    interface on top of it.

    Attributes:
        port: Serial device path (RS485_RTU) or `host`/`host:tcp_port`
            string (Modbus_TCP).
        baudrate: Serial baud rate, used only for RS485_RTU.
        logger: Logger instance used for status and error messages.
        slave_address: Modbus slave/unit address of the target hand.
        communication_method: Either "RS485_RTU" or "Modbus_TCP".
        communicator: The underlying transport instance (RS485_RTU or
            ModbusTCP) created by `_setup_communication`.
        ntrips: Running count of state-polling round trips performed by
            `wait_for_ready`.
    """

    def __init__(self, port='COM9', baudrate=115200, logger=None, slave_address=1, communication_method="RS485_RTU"):
        """Initializes the communication wrapper and constructs the transport.

        Args:
            port: Serial device for RS485_RTU (e.g. '/dev/ttyUSB0'), or
                'host' / 'host:tcp_port' for Modbus_TCP (e.g.
                '192.168.2.8:502').
            baudrate: Serial baud rate, used only for RS485_RTU.
            logger: Logger to use; a module-level logger is created if None.
            slave_address: Modbus slave/unit address of the target hand.
            communication_method: Transport to construct, either
                "RS485_RTU" or "Modbus_TCP".
        """
        self.port = port
        self.baudrate = baudrate
        self.logger = logger
        self.slave_address = slave_address
        self.communication_method = communication_method
        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        self._setup_communication()

        self.ntrips = 0

    
    def _setup_communication(self):
        """Instantiates the concrete communicator for `communication_method`.

        Raises:
            ValueError: If `communication_method` is not "RS485_RTU" or
                "Modbus_TCP".
        """
        if self.communication_method == "RS485_RTU":
            self.communicator = RS485_RTU(port=self.port, baudrate=self.baudrate, timeout=0.2, logger=self.logger, slave_address=self.slave_address)
        elif self.communication_method == "Modbus_TCP":
            host, _, tcp_port = str(self.port).partition(':')
            # 0.5s: first connect after idle needs firmware-side ARP resolution; 0.2s flakes
            self.communicator = ModbusTCP(host=host, port=int(tcp_port) if tcp_port else 502,
                                          timeout=0.5, logger=self.logger, slave_address=self.slave_address)
        else:
            raise ValueError(f"Unknown communication method: {self.communication_method}")

    def open_connection(self):
        """Opens the underlying transport connection."""
        self.communicator.open()

    def send_data(self, data:list,command_type:int=CommandType.SETUP_COMMANDS.value):
        """Sends a list of 16-bit register values to the hand.

        Args:
            data: Register values to write. Interpretation depends on
                `command_type` (see `CommandType` in ModbusMap).
            command_type: CommandType enum value selecting which Modbus
                write operation the underlying transport should perform.
        """
        # if len(data) > 1 and len(data)%2 != 0:
        #     self.logger.error(f"Data length should be even")
        self.communicator.send(data,command_type)

    def receive_data(self,amount_dat:int=1,start:int=ModbusMap().modbus_reg_map['feedback_register']): # default is receive robot state
        """Reads holding registers from the hand.

        Args:
            amount_dat: Number of consecutive registers to read.
            start: Starting register address. Defaults to the feedback
                register used to report robot state.

        Returns:
            A single int if one register was read, otherwise a list of ints.
        """
        #self.logger.info(f"data received is {self.communicator.receive([start,amount_dat])}")
        return self.communicator.receive([start,amount_dat])

    def close_connection(self):
        """Closes the underlying transport connection."""
        self.communicator.close()

    def _check_robot_state(self):
        """Reads and unpacks the combined robot/trajectory status byte.

        Returns:
            int: The low byte of the received 16-bit feedback value. The
            low nibble encodes the ActuatorState and the high nibble
            encodes the TrajectoryReturn state; callers (e.g.
            `wait_for_ready`) further mask this value to separate the two.

        Raises:
            ValueError: If the received value is not a 16-bit integer.
        """
        #self.logger.info(f"entering _check_robot_state")
        ret = self.receive_data()
        #self.logger.info(f"finished receive_data")
        

        if isinstance(ret, int) and ret <= 0xFFFF:  # Check if ret is a 16-bit value
            high_byte = (ret >> 8) & 0xFF  # Extract upper 8 bits
            low_byte = ret & 0xFF          # Extract lower 8 bits
            #self.logger.info(f"high_byte: {high_byte}, low_byte: {low_byte}")
            return low_byte
        else:
            raise ValueError("Received data is not a 16-bit value")
        return None  # Continue waiting
    
    def wait_for_ready(self,timeout=15,vis=False,acceptable_state=None):
        """Polls the hand until it reports an acceptable actuator state.

        Repeatedly calls `_check_robot_state` (roughly every 0.3s) and logs
        the decoded ActuatorState/TrajectoryReturn on each poll, until the
        masked state matches one of the acceptable states or `timeout`
        elapses.

        Args:
            timeout: Maximum time in seconds to wait before giving up.
            vis: If True, display a tqdm progress bar while waiting.
            acceptable_state: A single ActuatorState value to wait for. If
                None, waits for any of ACTUATOR_IDLE, ACTUATOR_ERROR,
                ACTUATOR_READY, or ACTUATOR_ACTIVE.

        Returns:
            The masked actuator state (int) once it matches one of the
            acceptable states, or None if the timeout elapses first.
        """
        start_time = time.perf_counter()
        time.sleep(0.2) 
        #self.logger.info(f"the self state is: {acceptable_state}")
        if not acceptable_state:
            acceptable_states = [ActuatorState.ACTUATOR_IDLE.value,ActuatorState.ACTUATOR_ERROR.value,ActuatorState.ACTUATOR_READY.value,ActuatorState.ACTUATOR_ACTIVE.value]
        else:
            acceptable_states = [acceptable_state]
        if vis:
            with tqdm(total=timeout,unit="s",desc="Waiting for Robot Ready") as progresbar:
                while 1:
                    #self.logger.info(f"does it get here")

                    raw_state = self._check_robot_state()
                    result = raw_state & 0xF
                    trajectory_state = (raw_state & 0b11110000) >> 4
                    #self.logger.info(f"does it get here x2")
                    self.logger.info(f"Robot state: {ActuatorState(result).name}, Trajectory: {TrajectoryReturn(trajectory_state).name}")
                    time_diff = time.perf_counter() - start_time
                    self.ntrips += 1
                    if result in acceptable_states:
                        return result
                    # time.sleep(0.1)
                    if progresbar.n + time_diff >= timeout:
                        self.logger.error("Timeout waiting for robot ready")
                        break
                    progresbar.update(time_diff)
                    time.sleep(0.3)
                    start_time = time.perf_counter()
                # self.logger.info(f"Roundtrip time: {self.ntrips/timeout} trips per second")
                # print(f"Roundtrip time: {self.ntrips/timeout} trips per second")
        else:
            while 1:
                raw_state = self._check_robot_state()
                result = raw_state & 0xF
                trajectory_state = (raw_state & 0b11110000) >> 4
                #self.logger.info(f"enters else statement")
                self.logger.info(f"Robot state: {ActuatorState(result).name}, Trajectory: {TrajectoryReturn(trajectory_state).name}")
                self.ntrips += 1
                if result in acceptable_states:
                    return result
                # time.sleep(0.1)
                time.sleep(0.3)
                if time.perf_counter() - start_time > timeout:
                    self.logger.error("Timeout waiting for robot ready")
                    break

        if result == ActuatorState.ACTUATOR_BUSY.value:
            self.logger.error(f"Robot Busy")
            # self.logger.info(f"Roundtrip time: {self.ntrips/timeout} trips per second")
            # print(f"Roundtrip time: {self.ntrips/timeout} trips per second")