"""Firmware update package.

Exposes the legacy :class:`FirmwareUpdater` and the Modbus RTU based
:class:`FirmwareUpdaterNew` used to flash firmware onto ARTUS hands over
the bus.
"""

from .FirmwareUpdaterNew import FirmwareUpdaterNew