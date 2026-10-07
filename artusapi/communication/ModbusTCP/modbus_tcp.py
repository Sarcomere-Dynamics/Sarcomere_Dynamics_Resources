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
import socket

from pymodbus.client import ModbusTcpClient

from ..ModbusClient import ModbusClient

MODBUS_TCP_DEFAULT_TIMEOUT_SECONDS = 1.0


class ModbusTCP(ModbusClient):
    """Modbus TCP transport for communicating with an ARTUS hand over Ethernet/WiFi.

    Wraps a `pymodbus` `ModbusTcpClient`, exposing the same open/send/receive/
    close interface as `ModbusRTU`, with connection retry logic in `send`
    and `receive`.

    Attributes:
        host: Hostname or IP address of the Modbus TCP server.
        port: TCP port of the Modbus TCP server.
        timeout: Socket timeout in seconds.
        slave_address: Modbus unit/device id of the target hand.
        logger: Logger used for status and error messages.
        client: The underlying `pymodbus` `ModbusTcpClient` instance,
            created on the first call to `open`.
    """

    def __init__(
        self,
        host: str,
        port: int,
        slave_address: int,
        timeout: float,
        logger: logging.Logger | None,
    ):
        """Initializes connection parameters without connecting.

        Args:
            host: Hostname or IP address of the Modbus TCP server.
            port: TCP port of the Modbus TCP server.
            timeout: Socket timeout in seconds.
            logger: Logger to use; a module-level logger is created if None.
            slave_address: Modbus unit/device id of the target hand.
        """
        self.host = host
        self.port = port
        super().__init__(timeout=timeout, logger=logger, slave_address=slave_address)

    def open(self):
        """Opens (or reopens) the Modbus TCP connection.

        No-op if already connected. Closes and discards any stale client
        before creating a new `ModbusTcpClient` and connecting.

        Raises:
            ConnectionError: If the TCP connection could not be established.
        """
        if self.is_connected():
            return
        client = getattr(self, "client", None)
        if client is not None:
            try:
                client.close()
            except Exception:
                self.logger.error("Failed to close existing ModbusTCP client.")

        try:
            self.client = ModbusTcpClient(
                host=self.host, port=self.port, timeout=self.timeout, retries=0
            )
            if not self.client.connect():
                raise ConnectionError(
                    f"Could not open Modbus TCP connection to {self.host}:{self.port}"
                )
            # Disable Nagle's algorithm so small register writes go out immediately
            # instead of being buffered/delayed, which otherwise caps send frequency.
            if getattr(self.client, "socket", None) is not None:
                try:
                    self.client.socket.setsockopt(
                        socket.IPPROTO_TCP, socket.TCP_NODELAY, 1
                    )
                    self.logger.debug("Disabled Nagle's algorithm (TCP_NODELAY=1)")
                except Exception as e:
                    self.logger.warning(f"Could not set TCP_NODELAY socket option: {e}")
            self.logger.info(f"Opened TCP connection to {self.host}:{self.port}")
        except Exception as e:
            self.logger.error(e)
            self.logger.error(
                f"Error opening TCP connection to {self.host}:{self.port}"
            )
            raise
