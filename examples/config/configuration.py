"""
Sarcomere Dynamics Software License Notice
------------------------------------------
This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

Licensed under the Sarcomere Dynamics Software License.
See the LICENSE file in the repository for full details.
"""

import yaml
from types import SimpleNamespace

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
import serial.tools.list_ports

from ArtusAPI.artus_api_new import ArtusAPI_V2
from ArtusAPI.common.SlaveIDMap import (
    SLAVE_ID_BY_ROBOT_HAND,
    expected_slave_id,
    robot_hand_from_slave_id,
)
from ArtusAPI.common.ModbusMap import ModbusMap
from ArtusAPI.communication.RS485_RTU.rs485_rtu import find_port_holders

import os
import sys
import logging
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Project Root", PROJECT_ROOT)
sys.path.append(PROJECT_ROOT)

class ArtusConfig:
    """
    This class is used to load and convert the configuration file into a dictionary to be used by the ArtusAPI_V2 class.
    """
    def __init__(self, config_file = PROJECT_ROOT + f"/examples/config/robot_config.yaml"):
        self.config = self.load_and_convert_config(config_file)

    def load_and_convert_config(self, config_file):
        with open(config_file, 'r') as file:
            config_dict = yaml.safe_load(file)
        return self.dict_to_namespace(config_dict)

    def dict_to_namespace(self, d):
        if isinstance(d, dict):
            return SimpleNamespace(**{k: self.dict_to_namespace(v) for k, v in d.items()})
        elif isinstance(d, list):
            return [self.dict_to_namespace(i) for i in d]
        else:
            return d

    def check_and_print_robot_config(self, hand_type):
        # Get the robot config for the specified hand type (left or right)
        if hand_type == 'left':
            robot_config = self.config.robots.left_hand_robot
        elif hand_type == 'right':
            robot_config = self.config.robots.right_hand_robot
        else:
            raise ValueError("Invalid hand type. Choose 'left' or 'right'.")

        # Check if the robot is connected and print values if true
        if robot_config.robot_connected:
            print(f"//n{hand_type.capitalize()} Hand Robot Configuration:")
            for key, value in vars(robot_config).items():
                print(f"{key}: {value}")
        else:
            print(f"//n{hand_type.capitalize()} hand robot is not connected.")

    def find_single_robot_type(self)->str:
        if self.config.robots.left_hand_robot.robot_connected == True and self.config.robots.right_hand_robot.robot_connected == False:
            return self.config.robots.left_hand_robot.robot_type
        elif self.config.robots.right_hand_robot.robot_connected == True and self.config.robots.left_hand_robot.robot_connected == False:
            return self.config.robots.right_hand_robot.robot_type
        else:
            raise ValueError("No robot connected")
            return None

    def get_api(self, logger=None):
        """
        Returns an instance of the appropriate API (ArtusAPI or ArtusAPI_V2)
        based on the connected robot. Only one robot can be connected at a time.
        Checks the robot connected status and returns the appropriate API instance.
        """

        # Figure out which robot is connected
        if self.config.robots.left_hand_robot.robot_connected and not self.config.robots.right_hand_robot.robot_connected:
            robot_cfg = self.config.robots.left_hand_robot
            print(f"Left hand robot connected")
        elif self.config.robots.right_hand_robot.robot_connected and not self.config.robots.left_hand_robot.robot_connected:
            robot_cfg = self.config.robots.right_hand_robot
            print(f"Right hand robot connected")
        else:
            raise ValueError("No robot connected or multiple robots connected. Only one robot can be connected at a time.")

        robot_cfg = self._preflight(robot_cfg, logger)
        return self.return_api(robot_cfg=robot_cfg, logger=logger)

    # ------------------------------------------------------------------
    # Pre-flight helpers
    # ------------------------------------------------------------------

    def _preflight(self, robot_cfg, logger):
        """Validate port and slave ID before instantiating the API, correcting
        robot_cfg in place if either needs to be discovered."""
        if getattr(robot_cfg, 'communication_method', 'RS485_RTU') == 'Modbus_TCP':
            # serial port selection and slave ID probing only apply to RS485
            return robot_cfg
        robot_cfg = self._validate_port_or_select(robot_cfg, logger)
        robot_cfg = self._validate_slave_or_discover(robot_cfg, logger)
        return robot_cfg

    def _validate_port_or_select(self, robot_cfg, logger):
        """If the configured serial port is not available, list available ports
        and prompt the user to pick one."""
        available_ports = serial.tools.list_ports.comports()
        available_devices = [p.device for p in available_ports]

        if robot_cfg.communication_channel_identifier in available_devices:
            return robot_cfg

        if not available_ports:
            raise RuntimeError(
                "No serial ports found. Check USB connection."
            )

        if len(available_ports) == 1:
            selected = available_ports[0].device
            print(
                f"Configured port {robot_cfg.communication_channel_identifier} not available. "
                f"Auto-selecting only available port: {selected}"
            )
            robot_cfg.communication_channel_identifier = selected
            return robot_cfg

        print(f"\nConfigured port {robot_cfg.communication_channel_identifier} not available.")
        print("\nAvailable ports:")
        for i, p in enumerate(available_ports):
            print(f"  [{i}] {p.device:<20} {p.description}")

        while True:
            try:
                choice = int(input(f"\nSelect port number (0-{len(available_ports) - 1}): "))
                if 0 <= choice < len(available_ports):
                    robot_cfg.communication_channel_identifier = available_ports[choice].device
                    return robot_cfg
                print(f"Enter a number between 0 and {len(available_ports) - 1}.")
            except ValueError:
                print("Invalid input. Enter a number.")

    def _validate_slave_or_discover(self, robot_cfg, logger):
        """Probe the configured Modbus slave ID. If it does not respond, scan
        all known slave IDs and update robot_cfg with what is actually found."""
        port = robot_cfg.communication_channel_identifier
        baudrate = getattr(robot_cfg, 'baudrate', 115200)
        configured_slave = expected_slave_id(robot_cfg.robot_type, robot_cfg.hand_type)
        status_reg = ModbusMap().modbus_reg_map['feedback_register']
        all_slave_ids = list(SLAVE_ID_BY_ROBOT_HAND.values())

        client = ModbusSerialClient(
            port=port, baudrate=baudrate,
            bytesize=8, parity='N', stopbits=1,
            timeout=0.15, retries=0,
        )
        if not client.connect():
            holders = find_port_holders(port)
            msg = f"Could not open {port} to probe slave ID."
            if holders:
                msg += f" Port is held by: {'; '.join(holders)}"
            raise RuntimeError(msg)

        def _probe(slave_id) -> bool:
            try:
                result = client.read_holding_registers(status_reg, count=1, device_id=slave_id)
                return not result.isError()
            except ModbusException:
                return False

        try:
            # Probe the configured slave ID first.
            if _probe(configured_slave):
                return robot_cfg

            # No response — scan all known IDs.
            print(
                f"\nNo response at configured slave ID {configured_slave} "
                f"({robot_cfg.robot_type}/{robot_cfg.hand_type}). Scanning all slave IDs..."
            )

            found_id = None
            for slave_id in all_slave_ids:
                if slave_id == configured_slave:
                    continue
                if _probe(slave_id):
                    found_id = slave_id
                    break

            if found_id is None:
                raise RuntimeError(
                    f"No ARTUS hand found on {port}. Check power and USB connection."
                )

            discovered_type, discovered_hand = robot_hand_from_slave_id(found_id)
            msg = (
                f"Found slave ID {found_id} ({discovered_type}/{discovered_hand}). "
                f"Update robot_config.yaml: robot_type: {discovered_type}, hand_type: {discovered_hand}"
            )
            if logger:
                logger.warning(msg)
            else:
                print(f"WARNING: {msg}")

            robot_cfg.robot_type = discovered_type
            robot_cfg.hand_type = discovered_hand
            return robot_cfg

        finally:
            client.close()
    
    def return_api(self,robot_cfg:dict=None,logger=None):
        """
        Return an instance of the appropriate API
        :param: robot_cfg: dictionary of robot configuration
        """
        if robot_cfg is None:
            return None
        # if hasattr(robot_cfg, 'robot_type') and 'lite' in str(robot_cfg.robot_type).lower():
        #     # Use ArtusAPI_V2 for 'artus_talos', otherwise fallback to ArtusAPI
        #     return ArtusAPI(logger=logger,
        #         robot_type=robot_cfg.robot_type,
        #         communication_method=robot_cfg.communication_method,
        #         communication_channel_identifier=robot_cfg.communication_channel_identifier,
        #         hand_type=robot_cfg.hand_type,
        #         reset_on_start=robot_cfg.reset_on_start,
        #         communication_frequency=robot_cfg.streaming_frequency if hasattr(robot_cfg, "streaming_frequency") else 20
        #     )
        # else:
        return ArtusAPI_V2(logger=logger,
            robot_type=robot_cfg.robot_type,
            communication_method=robot_cfg.communication_method,
            communication_channel_identifier=robot_cfg.communication_channel_identifier,
            hand_type=robot_cfg.hand_type,
            communication_frequency=robot_cfg.streaming_frequency if hasattr(robot_cfg, "streaming_frequency") else 20,
            baudrate=getattr(robot_cfg, "baudrate", 115200),
        )
            

    def get_robot_calibrate(self, hand_type:str=None) -> bool:
        """
        Returns True if the robot calibrate flag is set in config, False otherwise
        """
        if hand_type is None:
            if self.config.robots.left_hand_robot.robot_connected:
                return self.config.robots.left_hand_robot.calibrate
            elif self.config.robots.right_hand_robot.robot_connected:
                return self.config.robots.right_hand_robot.calibrate
            else:
                return False
        elif hand_type == 'left':
            return self.config.robots.left_hand_robot.calibrate
        elif hand_type == 'right':
            return self.config.robots.right_hand_robot.calibrate

    def get_robot_wake_up(self, hand_type:str=None) -> bool:
        """
        Returns True if the robot wake up flag is set in config, False otherwise
        """
        if hand_type is None:
            if self.config.robots.left_hand_robot.robot_connected:
                return self.config.robots.left_hand_robot.start_robot
            elif self.config.robots.right_hand_robot.robot_connected:
                return self.config.robots.right_hand_robot.start_robot
            else:
                return False
        elif hand_type == 'left':
            return self.config.robots.left_hand_robot.start_robot
        elif hand_type == 'right':
            return self.config.robots.right_hand_robot.start_robot
        else:
            raise ValueError("Invalid hand type. Choose 'left' or 'right'.")

# Example usage
if __name__ == "__main__":
    robot_config = ArtusConfig()

    # Check and print configuration for left hand robot
    robot_config.check_and_print_robot_config('left')

    # Check and print configuration for right hand robot
    robot_config.check_and_print_robot_config('right')