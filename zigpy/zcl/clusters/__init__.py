# flake8: noqa
from . import (
    closures,
    general,
    homeautomation,
    hvac,
    lighting,
    lightlink,
    manufacturer_specific,
    measurement,
    protocol,
    security,
    smartenergy,
)

__all__ = [
    "closures",
    "general",
    "homeautomation",
    "hvac",
    "lighting",
    "lightlink",
    "manufacturer_specific",
    "measurement",
    "protocol",
    "security",
    "smartenergy",
    "from_name",
]

from zigpy.zcl import Cluster

_CLUSTERS_BY_NAME = {}
_CLUSTERS_BY_ID = {}

for submodule in [
    closures,
    general,
    homeautomation,
    hvac,
    lighting,
    lightlink,
    manufacturer_specific,
    measurement,
    protocol,
    security,
    smartenergy,
]:
    for name in dir(submodule):
        value = getattr(submodule, name)

        try:
            if not issubclass(value, Cluster):
                continue
        except TypeError:
            continue

        if not getattr(value, "ep_attribute", None) or not getattr(
            value, "cluster_id", None
        ):
            continue

        assert value.ep_attribute not in _CLUSTERS_BY_NAME
        _CLUSTERS_BY_NAME[value.ep_attribute] = value
        _CLUSTERS_BY_ID[value.cluster_id] = value

from_id = _CLUSTERS_BY_ID.__getitem__
from_name = _CLUSTERS_BY_NAME.__getitem__
