# Sarcomere Dynamics Software License Notice
# ------------------------------------------
# This software is developed by Sarcomere Dynamics Inc.
# for use with the ARTUS family of robotic products.
#
# Copyright (c) 2023-2026, Sarcomere Dynamics Inc. All rights reserved.
#
# Licensed under the Sarcomere Dynamics Software License.
# See the LICENSE file in the repository for full details.

import logging
import os

from pymodbus.client import ModbusSerialClient

from ..ModbusClient import ModbusClient


def find_port_holders(port):
    """Finds processes that currently have `port` open.

    Used to diagnose "could not exclusively lock port" errors by scanning
    `/proc` for file descriptors pointing at the given path. Linux only.

    Args:
        port: Filesystem path of the serial device to check (e.g.
            '/dev/ttyUSB0').

    Returns:
        A list of 'pid <pid> (<cmdline>)' strings, one per process holding
        the port open. Empty on non-Linux platforms or if nothing holds it.
    """
    holders = []
    try:
        target = os.path.realpath(port)
        for pid in os.listdir("/proc"):
            if not pid.isdigit() or int(pid) == os.getpid():
                continue
            fd_dir = f"/proc/{pid}/fd"
            try:
                for fd in os.listdir(fd_dir):
                    link = os.readlink(os.path.join(fd_dir, fd))
                    if link == target or link == f"{target} (deleted)":
                        with open(f"/proc/{pid}/cmdline") as f:
                            cmd = f.read().replace("\0", " ").strip() or "?"
                        suffix = (
                            " [stale fd, port re-enumerated]"
                            if link.endswith("(deleted)")
                            else ""
                        )
                        holders.append(f"pid {pid} ({cmd}){suffix}")
                        break
            except (PermissionError, FileNotFoundError, OSError):
                continue
    except Exception:
        pass
    return holders


class ModbusRTU(ModbusClient):
    """Modbus RTU transport for RS485 communication with an ARTUS hand.

    Wraps a `pymodbus` `ModbusSerialClient` to send and receive data over
    RS485. The only data received is hand feedback, which must be polled;
    sends use the Modbus "write single register" and "write multiple
    registers" functions.

    Attributes:
        port: Serial device path (e.g. '/dev/ttyUSB0').
        baudrate: Serial baud rate.
        timeout: Serial read timeout in seconds.
        slave_address: Modbus slave address of the target hand.
        logger: Logger used for status and error messages.
        client: The underlying `pymodbus` `ModbusSerialClient` instance,
            created on the first call to `open`.
    """

    def __init__(
        self,
        port: str,
        baudrate: int,
        slave_address: int,
        timeout: float,
        logger: logging.Logger | None,
    ):
        """Initializes connection parameters without opening the port.

        Args:
            port: Serial device path to connect to.
            baudrate: Serial baud rate.
            timeout: Serial read timeout in seconds.
            logger: Logger to use; a module-level logger is created if None.
            slave_address: Modbus slave address of the target hand.
        """
        self.port = port
        self.baudrate = baudrate
        super().__init__(timeout=timeout, logger=logger, slave_address=slave_address)

    def open(self):
        """Opens the ModbusRTU serial connection.

        Raises:
            ConnectionError: If the port could not be opened; the error
                message includes any processes found holding the port via
                `find_port_holders`.
        """
        client = getattr(self, "client", None)
        if client is not None:
            try:
                client.close()
            except Exception:
                self.logger.error("Failed to close existing ModbusRTU client.")

        try:
            # retries=0: retry behaviour is handled in send/receive below,
            # matching the previous minimalmodbus implementation
            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=self.timeout,
                retries=0,
            )
            if not self.client.connect():
                holders = find_port_holders(self.port)
                msg = f"Could not open {self.port} @ {self.baudrate} baudrate"
                if holders:
                    msg += f". Port is held by: {'; '.join(holders)}"
                raise ConnectionError(msg)

            self.logger.info(f"Opening {self.port} @ {self.baudrate} baudrate")
        except Exception as e:
            self.logger.error(e)
            self.logger.error(f"Error opening {self.port} @ {self.baudrate} baudrate")
            raise
