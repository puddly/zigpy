"""Implement OTA for Zigbee devices."""

import asyncio
import logging
from typing import Optional

from zigpy.ota.firmware import FirmwareKey, OTAImage

LOGGER = logging.getLogger(__name__)


class OTA:
    def __init__(self, providers):
        self.providers = providers

        # XXX: Evict stale images from the cache.
        # Most OTA upgrades are only a few hundred KB so it isn't a huge leak.
        self._image_cache = {}

    async def refresh_firmwares(self) -> None:
        LOGGER.debug("Refreshing OTA firmwares")
        await asyncio.gather(*[p.refresh_firmwares() for p in self.providers])

    def immediately_get_firmware(self, key: FirmwareKey) -> Optional[OTAImage]:
        assert key.version is not None
        return self._image_cache.get(key)

    async def get_firmware(self, key: FirmwareKey) -> Optional[OTAImage]:
        if key.version is not None:
            if key in self._image_cache:
                return self._image_cache[key]

            logger.warning('Firmware %s is supposed to be in the cache!', key)

        firmwares = asyncio.gather(*[p.get_firmware(key) for p in self.providers])
        firmwares = [f for f in firmwares if f is not None]

        if not firmwares:
            return None

        latest = max(firmwares, key=lambda f: f.image_version)

        # OTA block requests will always refer to a specific firmware version so we should cache it.
        # It wouldn't make sense for the image to change yet retain this info.
        self._image_cache[latest.firmare_key] = latest

        return latest


    def pin_firmware(self, firmware: OTAImage) -> FirmwareKey:
        pass