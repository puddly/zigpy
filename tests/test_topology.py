from __future__ import annotations

import asyncio
import contextlib
from unittest import mock

import pytest

import zigpy.config as conf
import zigpy.endpoint
import zigpy.profiles
import zigpy.topology
import zigpy.types as t
import zigpy.zdo.types as zdo_t

from tests.conftest import App
from tests.test_appdb import make_ieee


def make_neighbor(
    *,
    ieee: t.EUI64,
    nwk: t.NWK,
    device_type: zdo_t.Neighbor.DeviceType = zdo_t.Neighbor.DeviceType.Router,
    rx_on_when_idle=True,
    relationship: zdo_t.Neighbor.Relationship = zdo_t.Neighbor.Relationship.Child,
) -> zdo_t.Neighbor:
    return zdo_t.Neighbor(
        extended_pan_id=make_ieee(start=0),
        ieee=ieee,
        nwk=nwk,
        device_type=device_type,
        rx_on_when_idle=int(rx_on_when_idle),
        relationship=relationship,
        reserved1=0,
        permit_joining=0,
        reserved2=0,
        depth=15,
        lqi=250,
    )


def make_route(
    *,
    dest_nwk: t.NWK,
    next_hop: t.NWK,
    status: zdo_t.RouteStatus = zdo_t.RouteStatus.Active,
) -> zdo_t.Route:
    return zdo_t.Route(
        DstNWK=dest_nwk,
        RouteStatus=status,
        MemoryConstrained=0,
        ManyToOne=0,
        RouteRecordRequired=0,
        Reserved=0,
        NextHop=next_hop,
    )


def make_node_desc(
    *, logical_type: zdo_t.LogicalType = zdo_t.LogicalType.Router
) -> zdo_t.NodeDescriptor:
    return zdo_t.NodeDescriptor(
        logical_type=logical_type,
        complex_descriptor_available=0,
        user_descriptor_available=0,
        reserved=0,
        aps_flags=0,
        frequency_band=zdo_t.NodeDescriptor.FrequencyBand.Freq2400MHz,
        mac_capability_flags=zdo_t.NodeDescriptor.MACCapabilityFlags.AllocateAddress,
        manufacturer_code=4174,
        maximum_buffer_size=82,
        maximum_incoming_transfer_size=82,
        server_mask=0,
        maximum_outgoing_transfer_size=82,
        descriptor_capability_field=zdo_t.NodeDescriptor.DescriptorCapability.NONE,
    )


@pytest.fixture
def make_initialized_device():
    count = 1

    def inner(app):
        nonlocal count

        dev = app.add_device(nwk=0x1000 + count, ieee=make_ieee(count))
        dev.node_desc = make_node_desc(logical_type=zdo_t.LogicalType.Router)

        ep = dev.add_endpoint(1)
        ep.status = zigpy.endpoint.Status.ZDO_INIT
        ep.profile_id = 260
        ep.device_type = zigpy.profiles.zha.DeviceType.PUMP

        count += 1

        return dev

    return inner


@pytest.fixture
def topology(make_initialized_device):
    app = App(
        conf.ZIGPY_SCHEMA(
            {
                conf.CONF_DEVICE: {conf.CONF_DEVICE_PATH: "/dev/null"},
                conf.CONF_TOPO_SKIP_COORDINATOR: True,
            }
        )
    )

    coordinator = make_initialized_device(app)
    coordinator.nwk = 0x0000

    app.state.node_info.nwk = coordinator.nwk
    app.state.node_info.ieee = coordinator.ieee
    app.state.node_info.logical_type = zdo_t.LogicalType.Coordinator

    return zigpy.topology.Topology(app)


@contextlib.contextmanager
def patch_device_tables(
    device,
    neighbors: list | BaseException | zdo_t.Status,
    routes: list | BaseException | zdo_t.Status,
):
    def mgmt_lqi_req(StartIndex: t.uint8_t, **kwargs):
        status = zdo_t.Status.SUCCESS
        entries = 0
        start_index = 0
        table: list[zdo_t.Neighbor] = []

        if isinstance(neighbors, zdo_t.Status):
            status = neighbors
        elif isinstance(neighbors, BaseException):
            raise neighbors
        else:
            entries = len(neighbors)
            start_index = StartIndex
            table = neighbors[StartIndex : StartIndex + 3]

        return list(
            dict(
                Status=status,
                Neighbors=zdo_t.Neighbors(
                    Entries=entries,
                    StartIndex=start_index,
                    NeighborTableList=table,
                ),
            ).values()
        )

    def mgmt_rtg_req(StartIndex: t.uint8_t, **kwargs):
        status = zdo_t.Status.SUCCESS
        entries = 0
        start_index = 0
        table: list[zdo_t.Route] = []

        if isinstance(routes, zdo_t.Status):
            status = routes
        elif isinstance(routes, BaseException):
            raise routes
        else:
            entries = len(routes)
            start_index = StartIndex
            table = routes[StartIndex : StartIndex + 3]

        return list(
            dict(
                Status=status,
                Routes=zdo_t.Routes(
                    Entries=entries,
                    StartIndex=start_index,
                    RoutingTableList=table,
                ),
            ).values()
        )

    lqi_req_patch = mock.patch.object(
        device.zdo, "Mgmt_Lqi_req", mock.AsyncMock(side_effect=mgmt_lqi_req)
    )
    rtg_req_patch = mock.patch.object(
        device.zdo, "Mgmt_Rtg_req", mock.AsyncMock(side_effect=mgmt_rtg_req)
    )

    with lqi_req_patch, rtg_req_patch:
        yield


@mock.patch("zigpy.topology.REQUEST_DELAY", new=(0, 0))
async def test_scan_no_devices(topology) -> None:
    await topology.scan()

    assert not topology.neighbors
    assert not topology.routes


@mock.patch("zigpy.topology.REQUEST_DELAY", new=(0, 0))
@pytest.mark.parametrize(
    "neighbors, routes",
    [
        ([], asyncio.TimeoutError()),
        ([], []),
        (asyncio.TimeoutError(), asyncio.TimeoutError()),
    ],
)
async def test_scan_failures(
    topology, make_initialized_device, neighbors, routes
) -> None:
    dev = make_initialized_device(topology._app)

    with patch_device_tables(dev, neighbors=neighbors, routes=routes):
        await topology.scan()

        assert len(dev.zdo.Mgmt_Lqi_req.mock_calls) == 1
        assert len(dev.zdo.Mgmt_Rtg_req.mock_calls) == 1

    assert not topology.neighbors[dev.ieee]
    assert not topology.routes[dev.ieee]


@mock.patch("zigpy.topology.REQUEST_DELAY", new=(0, 0))
async def test_neighbors_not_supported(topology, make_initialized_device) -> None:
    dev = make_initialized_device(topology._app)

    with patch_device_tables(dev, neighbors=zdo_t.Status.NOT_SUPPORTED, routes=[]):
        await topology.scan()

        assert len(dev.zdo.Mgmt_Lqi_req.mock_calls) == 1
        assert len(dev.zdo.Mgmt_Rtg_req.mock_calls) == 1

        await topology.scan()

        assert len(dev.zdo.Mgmt_Lqi_req.mock_calls) == 1
        assert len(dev.zdo.Mgmt_Rtg_req.mock_calls) == 2


@mock.patch("zigpy.topology.REQUEST_DELAY", new=(0, 0))
async def test_routes_not_supported(topology, make_initialized_device) -> None:
    dev = make_initialized_device(topology._app)

    with patch_device_tables(dev, neighbors=[], routes=zdo_t.Status.NOT_SUPPORTED):
        await topology.scan()

        assert len(dev.zdo.Mgmt_Lqi_req.mock_calls) == 1
        assert len(dev.zdo.Mgmt_Rtg_req.mock_calls) == 1

        await topology.scan()

        assert len(dev.zdo.Mgmt_Lqi_req.mock_calls) == 2
        assert len(dev.zdo.Mgmt_Rtg_req.mock_calls) == 1


@mock.patch("zigpy.topology.REQUEST_DELAY", new=(0, 0))
async def test_scan_end_device(topology, make_initialized_device) -> None:
    dev = make_initialized_device(topology._app)
    dev.node_desc.logical_type = zdo_t.LogicalType.EndDevice

    with patch_device_tables(dev, neighbors=[], routes=[]):
        await topology.scan()

        # The device will not be scanned because it is not a router
        assert len(dev.zdo.Mgmt_Lqi_req.mock_calls) == 0
        assert len(dev.zdo.Mgmt_Rtg_req.mock_calls) == 0


@mock.patch("zigpy.topology.REQUEST_DELAY", new=(0, 0))
async def test_scan_skip_coordinator(topology, make_initialized_device) -> None:
    app = topology._app
    coordinator = make_initialized_device(topology._app)
    coordinator.nwk = 0x0000

    app.state.node_info.nwk = coordinator.nwk
    app.state.node_info.ieee = coordinator.ieee
    app.state.node_info.logical_type = zdo_t.LogicalType.Coordinator

    with patch_device_tables(coordinator, neighbors=[], routes=[]):
        await topology.scan()

        assert len(coordinator.zdo.Mgmt_Lqi_req.mock_calls) == 0
        assert len(coordinator.zdo.Mgmt_Rtg_req.mock_calls) == 0

    assert not topology.neighbors[coordinator.ieee]
    assert not topology.routes[coordinator.ieee]


@mock.patch("zigpy.topology.REQUEST_DELAY", new=(0, 0))
async def test_scan_scan_coordinator(topology) -> None:
    app = topology._app
    app.config[conf.CONF_TOPO_SKIP_COORDINATOR] = False

    coordinator = app._device
    assert coordinator.nwk == 0x0000

    with patch_device_tables(
        coordinator,
        neighbors=[
            make_neighbor(ieee=make_ieee(2), nwk=0x1234),
        ],
        routes=[
            make_route(dest_nwk=0x1234, next_hop=0x1234),
        ],
    ):
        await topology.scan()

        assert len(coordinator.zdo.Mgmt_Lqi_req.mock_calls) == 1
        assert len(coordinator.zdo.Mgmt_Rtg_req.mock_calls) == 1

    assert topology.neighbors[coordinator.ieee] == [
        make_neighbor(ieee=make_ieee(2), nwk=0x1234)
    ]
    assert topology.routes[coordinator.ieee] == [
        make_route(dest_nwk=0x1234, next_hop=0x1234)
    ]


@mock.patch("zigpy.topology.REQUEST_DELAY", new=(0, 0))
@mock.patch("zigpy.application.ControllerApplication._discover_unknown_device")
async def test_discover_new_devices(
    discover_unknown_device, topology, make_initialized_device
) -> None:
    dev1 = make_initialized_device(topology._app)
    dev2 = make_initialized_device(topology._app)

    await topology._find_unknown_devices(
        neighbors={
            dev1.ieee: [
                # Existing devices
                make_neighbor(ieee=dev1.ieee, nwk=dev1.nwk),
                make_neighbor(ieee=dev2.ieee, nwk=dev2.nwk),
                # Unknown device
                make_neighbor(
                    ieee=t.EUI64.convert("aa:bb:cc:dd:11:22:33:44"), nwk=0xFF00
                ),
            ],
            dev2.ieee: [],
        },
        routes={
            dev1.ieee: [
                # Existing devices
                make_route(dest_nwk=dev1.nwk, next_hop=dev1.nwk),
                make_route(dest_nwk=dev2.nwk, next_hop=dev2.nwk),
                # Via existing devices
                make_route(dest_nwk=0xFF01, next_hop=dev2.nwk),
                make_route(dest_nwk=dev2.nwk, next_hop=0xFF02),
                # Inactive route
                make_route(
                    dest_nwk=0xFF03, next_hop=0xFF04, status=zdo_t.RouteStatus.Inactive
                ),
            ],
            dev2.ieee: [],
        },
    )

    assert len(discover_unknown_device.mock_calls) == 3
    assert mock.call(0xFF00) in discover_unknown_device.mock_calls
    assert mock.call(0xFF01) in discover_unknown_device.mock_calls
    assert mock.call(0xFF02) in discover_unknown_device.mock_calls
