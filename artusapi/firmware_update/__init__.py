"""Firmware update package.

Exposes the legacy :class:`ActuatorUpdater` and the Modbus RTU based
:class:`ActuatorUpdater` used to flash firmware onto ARTUS hands over
the bus.
"""

from .actuator_updater import ActuatorUpdater

__all__ = ["ActuatorUpdater"]
