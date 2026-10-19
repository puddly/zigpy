"""Shared fixtures for Green Power tests."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from tests.conftest import NCP_IEEE, add_initialized_device, make_ieee, make_neighbor
import zigpy.types as t
import zigpy.zgp.manager
from zigpy.zgp.manager import GreenPowerManager

PROXY_NWK = t.NWK(0x1234)


def add_proxy(app, nwk: int, ieee: t.EUI64):
    """Add a router the coordinator hears well, which puts it in the GP backbone."""
    router = add_initialized_device(app, nwk=t.NWK(nwk), ieee=ieee)
    app.topology.neighbors[NCP_IEEE].append(
        make_neighbor(ieee=router.ieee, nwk=router.nwk)
    )
    app.topology.neighbors[router.ieee].append(
        make_neighbor(ieee=NCP_IEEE, nwk=t.NWK(0x0000))
    )

    return router


@pytest.fixture(autouse=True)
def no_gp_delays():
    """The census settle and the pairing resend spacing only add time in tests."""
    with (
        patch.object(zigpy.zgp.manager, "GP_CENSUS_SETTLE", 0),
        patch.object(zigpy.zgp.manager, "GP_PAIRING_RESEND_INTERVAL", 0),
    ):
        yield


@pytest.fixture
def manager(app) -> GreenPowerManager:
    """Return the GP manager attached to the test application.

    A valid operational Zigbee channel (15) is pinned on the app state so
    GP responses that encode `channel - 11` don't underflow. Individual
    tests remain free to overwrite `app.state.network_info.channel`.
    """
    app.state.network_info.channel = 15
    add_proxy(app, nwk=PROXY_NWK, ieee=make_ieee(0x50))

    return app.green_power


@pytest.fixture
def proxy(app, manager):
    """The backbone router that forwards the GPDFs in these tests."""
    return app.get_device(nwk=PROXY_NWK)


async def wait_for_gp_processing() -> None:
    """Wait for the manager to finish processing received commissioning GPDFs."""
    await asyncio.gather(
        *(
            task
            for task in asyncio.all_tasks()
            if task.get_name().startswith("gp_process_command")
        )
    )
