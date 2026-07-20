"""
Shared mocks for ArtusAPI tests (no hardware).
"""

from __future__ import annotations

import unittest.mock as mock
from contextlib import contextmanager
from typing import Any, Generator, Tuple, Type

from ArtusAPI.communication.new_communication import ActuatorState


def make_communication_mock() -> mock.MagicMock:
    """Builds a MagicMock standing in for NewCommunication.

    Returns:
        A MagicMock with the NewCommunication methods used by ArtusAPI_V2
        (open_connection, close_connection, send_data, receive_data,
        wait_for_ready, _check_robot_state) pre-configured with sane defaults.
    """
    m = mock.MagicMock()
    m.open_connection = mock.Mock()
    m.close_connection = mock.Mock()
    m.send_data = mock.Mock(return_value=True)
    m.receive_data = mock.Mock(return_value=0)
    m.wait_for_ready = mock.Mock(return_value=ActuatorState.ACTUATOR_IDLE.value)
    m._check_robot_state = mock.Mock(return_value=ActuatorState.ACTUATOR_IDLE.value)
    return m


@contextmanager
def patched_artus_api_v2_constructor(
    communication_mock: mock.MagicMock | None = None,
) -> Generator[Tuple[Type, mock.MagicMock], None, None]:
    """Patches NewCommunication, time.sleep, and signal.signal while constructing ArtusAPI_V2.

    Args:
        communication_mock: Mock to substitute for the real NewCommunication
            instance. If None, one is created via make_communication_mock().

    Yields:
        A tuple of (ArtusAPI_V2 class, communication mock instance returned
        to the API).
    """
    if communication_mock is None:
        communication_mock = make_communication_mock()

    import ArtusAPI.artus_api_new as api_mod

    with mock.patch.object(api_mod, "NewCommunication", autospec=True) as nc_cls:
        nc_cls.return_value = communication_mock
        with mock.patch.object(api_mod.time, "sleep"):
            with mock.patch.object(api_mod.signal, "signal"):
                yield api_mod.ArtusAPI_V2, communication_mock


def build_api(
    robot_type: str = "artus_lite",
    hand_type: str = "left",
    communication_mock: mock.MagicMock | None = None,
    **kwargs: Any,
):
    """Constructs ArtusAPI_V2 with communication fully mocked.

    Args:
        robot_type: Robot type string passed to ArtusAPI_V2 (e.g. "artus_lite").
        hand_type: Hand type string passed to ArtusAPI_V2 (e.g. "left").
        communication_mock: Mock to substitute for the real NewCommunication
            instance. If None, one is created via make_communication_mock().
        **kwargs: Additional keyword arguments forwarded to ArtusAPI_V2.

    Returns:
        A tuple of (ArtusAPI_V2 instance, communication mock instance).
    """
    comm = communication_mock or make_communication_mock()
    with patched_artus_api_v2_constructor(comm) as (Cls, _):
        api = Cls(
            robot_type=robot_type,
            hand_type=hand_type,
            communication_method="RS485_RTU",
            communication_channel_identifier="MOCK",
            **kwargs,
        )
    return api, comm
