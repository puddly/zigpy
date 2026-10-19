"""Tests for the choice of the Green Power backbone."""

from __future__ import annotations

from tests.conftest import make_ieee, make_neighbor
import zigpy.types as t
from zigpy.zgp.backbone import select_backbone

COORDINATOR = make_ieee(0)
R1, R2, R3 = make_ieee(1), make_ieee(2), make_ieee(3)


def links(*reports: tuple[t.EUI64, t.EUI64, int]) -> dict:
    """Neighbor tables from (scanner, neighbor, lqi) reports, in both directions."""
    neighbors: dict[t.EUI64, list] = {}

    for a, b, lqi in reports:
        for scanner, neighbor in ((a, b), (b, a)):
            entry = make_neighbor(ieee=neighbor, nwk=t.NWK(0x1000))
            entry.lqi = lqi
            neighbors.setdefault(scanner, []).append(entry)

    return neighbors


def backbone(routers, neighbors, incumbent=()):
    return select_backbone(
        coordinator=COORDINATOR,
        routers=routers,
        neighbors=neighbors,
        incumbent=incumbent,
    )


def test_no_routers() -> None:
    assert backbone([], {}) == set()


def test_coordinator_covers_once() -> None:
    """A router heard by the coordinator needs one more listener."""
    neighbors = links((COORDINATOR, R1, 250), (COORDINATOR, R2, 250), (R1, R2, 250))

    # r1 hears itself and r2, which with the coordinator covers both twice
    assert backbone([R1, R2], neighbors) == {R1}


def test_out_of_coordinator_reach() -> None:
    """A router the coordinator cannot hear needs two backbone members."""
    neighbors = links((COORDINATOR, R1, 250), (R1, R2, 250))

    assert backbone([R1, R2], neighbors) == {R1, R2}


def test_requirement_capped() -> None:
    """An isolated router can only be covered by itself."""
    assert backbone([R1], {}) == {R1}


def test_weak_link_buys_less() -> None:
    """A weak link counts for little, so each router still has to cover itself."""
    neighbors = links((COORDINATOR, R1, 250), (COORDINATOR, R2, 250), (R1, R2, 60))

    assert backbone([R1, R2], neighbors) == {R1, R2}


def test_weak_links_add_up() -> None:
    """Two half-strength neighbors together count as one listener."""
    # The strong link sets the ceiling, the coordinator hears nobody
    neighbors = links((R2, R3, 250), (R1, R2, 125), (R1, R3, 125))

    # r1 needs itself and both half-strength neighbors to reach two listeners
    assert backbone([R1, R2, R3], neighbors) == {R1, R2, R3}


def test_compressed_lqi_scale() -> None:
    """A stack reporting LQI on a small scale gets the same backbone."""
    neighbors = links((COORDINATOR, R1, 60), (COORDINATOR, R2, 60), (R1, R2, 60))

    assert backbone([R1, R2], neighbors) == {R1}


def test_asymmetric_link() -> None:
    """The weaker direction of a link decides."""
    neighbors = links((COORDINATOR, R1, 250), (COORDINATOR, R2, 250))
    one_way = links((R1, R2, 250))
    neighbors[R1] += one_way[R1]
    neighbors[R2] += one_way[R2]
    neighbors[R2][-1].lqi = 10

    assert backbone([R1, R2], neighbors) == {R1, R2}


def test_keeps_incumbent() -> None:
    """A backbone that still suffices is not reshuffled by a new scan."""
    neighbors = links((COORDINATOR, R1, 250), (COORDINATOR, R2, 250), (R1, R2, 250))

    assert backbone([R1, R2], neighbors) == {R1}
    # r2 covers the same cells, a scan reporting it first changes nothing
    assert backbone([R1, R2], neighbors, incumbent={R2}) == {R2}
    # A member that left the network is dropped from the incumbent
    assert backbone([R1, R2], neighbors, incumbent={R2, R3}) == {R2}

    # Once r2 no longer hears r1, the incumbent is replaced
    neighbors = links((COORDINATOR, R1, 250), (COORDINATOR, R2, 250))
    assert backbone([R1, R2], neighbors, incumbent={R2}) == {R1, R2}


def test_ignores_unknown_neighbors() -> None:
    """End devices and neighbors that are not routers do not count as cells."""
    neighbors = links((COORDINATOR, R1, 250), (COORDINATOR, R2, 250), (R1, R3, 250))

    # r3 is not a router, the link to it means nothing
    assert backbone([R1, R2], neighbors) == {R1, R2}


def test_redundant_pick_pruned() -> None:
    """A member whose cells later picks also cover is dropped."""
    neighbors = links(
        (R1, R2, 250),
        (R1, R3, 250),
        (R2, R3, 250),
        (COORDINATOR, R1, 250),
        (COORDINATOR, R2, 250),
        (COORDINATOR, R3, 250),
    )

    assert len(backbone([R1, R2, R3], neighbors)) == 1
