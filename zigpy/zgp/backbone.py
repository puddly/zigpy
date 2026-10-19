"""The routers involved in Green Power commissioning.

Chosen from the neighbor tables gathered by the topology scanner: every router, as a
place a GPD may be, must be heard by an expected `BACKBONE_COVERAGE` of the members
and the coordinator together. A router hears itself with certainty and a neighbor in
proportion to the link's LQI, rescaled to the network's own range so the scale a stack
reports LQI on does not matter. The LQI is a bias, not a probability: weak links are
never ruled out, they just buy less coverage.
"""

from __future__ import annotations

import collections
from collections.abc import Iterable, Mapping
import math

import zigpy.types as t
import zigpy.zdo.types as zdo_types

BACKBONE_COVERAGE = 2.0
# The ceiling of the LQI rescaling ignores outliers
BACKBONE_LQI_PERCENTILE = 0.95

EPSILON = 1e-9


def select_backbone(
    *,
    coordinator: t.EUI64,
    routers: Iterable[t.EUI64],
    neighbors: Mapping[t.EUI64, Iterable[zdo_types.Neighbor]],
    incumbent: Iterable[t.EUI64] = (),
) -> set[t.EUI64]:
    """Pick a greedy multicover of the routers, keeping `incumbent` while it suffices."""
    routers = sorted(routers)
    cells = {coordinator, *routers}

    # The weaker direction of a link decides, when both were reported
    links: dict[frozenset[t.EUI64], int] = {}

    for scanned, scanned_neighbors in neighbors.items():
        if scanned not in cells:
            continue

        for neighbor in scanned_neighbors:
            if neighbor.ieee not in cells or neighbor.ieee == scanned:
                continue

            link = frozenset((scanned, neighbor.ieee))
            links[link] = min(links.get(link, 255), neighbor.lqi)

    if links:
        lqis = sorted(links.values())
        ceiling = lqis[math.ceil((len(lqis) - 1) * BACKBONE_LQI_PERCENTILE)]
    else:
        ceiling = 0

    covers: dict[t.EUI64, dict[t.EUI64, float]] = {node: {node: 1.0} for node in cells}

    for link, lqi in links.items():
        a, b = link
        weight = min(1.0, lqi / ceiling) if ceiling > 0 else 0.0
        covers[a][b] = weight
        covers[b][a] = weight

    required = {}

    for cell in cells:
        achievable = sum(covers[node].get(cell, 0.0) for node in cells)
        needed = min(BACKBONE_COVERAGE, achievable)
        needed -= covers[coordinator].get(cell, 0.0)
        required[cell] = max(needed, 0.0)

    def satisfied(members: Iterable[t.EUI64]) -> bool:
        coverage: dict[t.EUI64, float] = collections.defaultdict(float)

        for member in members:
            for cell, weight in covers[member].items():
                coverage[cell] += weight

        return all(
            coverage[cell] + EPSILON >= needed for cell, needed in required.items()
        )

    kept = {ieee for ieee in incumbent if ieee in cells and ieee != coordinator}

    if satisfied(kept):
        return kept

    deficits = dict(required)
    chosen: list[t.EUI64] = []

    while max(deficits.values(), default=0.0) > EPSILON:
        # Ties resolve to the first router in address order
        gain, member = max(
            (
                (
                    sum(
                        min(weight, deficits[cell])
                        for cell, weight in covers[router].items()
                    ),
                    router,
                )
                for router in routers
                if router not in chosen
            ),
            key=lambda item: (item[0], [-b for b in item[1]]),
        )

        if gain <= EPSILON:
            break

        chosen.append(member)

        for cell, weight in covers[member].items():
            deficits[cell] = max(deficits[cell] - weight, 0.0)

    # Drop members made redundant by later picks, latest first
    for member in reversed(list(chosen)):
        if satisfied(other for other in chosen if other != member):
            chosen.remove(member)

    return set(chosen)
