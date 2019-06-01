"""OTA Firmware providers."""

import inspect
import pathlib
import asyncio
import logging

from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta

import aiohttp

from zigpy.ota.firmware import FirmwareKey, OTAImage


LOGGER = logging.getLogger(__name__)


def timed_cache(**timedelta_kwargs):
    expiration_delta = timedelta(**timedelta_kwargs)

    def wrapper(function):
        async def replacement(*args, **kwargs):
            now = datetime.utcnow()

            # XXX: I'm sure there's a cleaner way
            key = repr((args, tuple(sorted(kwargs.items()))))
            value, expiration = replacement._cache.get(key, (None, datetime.utcfromtimestamp(0)))

            if expiration > now + expiration_delta:
                return value

            value = await function(*args, **kwargs)
            replacement._cache[key] = (value, now + expiration_delta)

            return value

        replacement._cache = {}

        return replacement
    return wrapper


class BaseOTAProvider:
    async def refresh_firmwares(self):
        pass

    async def get_image(self, key: FirmwareKey) -> Optional[OTAImage]:
        raise NotImplementedError()


class Filesystem(BaseOTAProvider):
    def __init__(self, root):
        self.root = pathlib.Path(root)

    async def get_image(self, key: FirmwareKey) -> Optional[OTAImage]:
        # XXX: There's no real async way to do file IO yet
        return await asyncio.get_running_loop().run_in_executor(None, self._get_image_sync, key)

    def _get_image_sync(self, key: FirmwareKey) -> Optional[OTAImage]:
        candidates = []

        for path in self.root.glob('*.ota'):
            with path.open('rb') as f:
                ota_image = OTAImage.deserialize(f.read())

            if key.is_compatible(ota_image.firmware_key):
                candidates.append(ota_image)

        if not candidates:
            return None

        # Choose the latest one if we have duplicates
        return max(candidates, key=lambda ota: ota.file_version)


class Trådfri(BaseOTAProvider):
    IKEA_MANUFACTURER_CODE = 0x117C
    VERSION_URL = 'https://fw.ota.homesmart.ikea.net/feed/version_info.json'

    async def refresh_firmwares(self):
        self._fetch_versions._cache.clear()
        self.get_image._cache.clear()

    @timed_cache(hours=12)
    async def _fetch_versions(self):
        logger.debug('Downloading OTA info from IKEA')

        async with aiohttp.ClientSession() as session:
            async with session.get(self.VERSION_URL) as response:
                return await response.json(content_type='application/octet-stream')

    @timed_cache(hours=12)
    async def get_image(self, key: FirmwareKey) -> Optional[OTAImage]:
        # Don't hit the IKEA servers unless we actually are requesting an IKEA image
        if key.manufacturer_code != self.IKEA_MANUFACTURER_CODE:
            return

        for fw_info in (await self._fetch_versions()):
            if 'fw_file_version_MSB' not in fw_info:
                continue

            # We can construct this from the JSON, without downloading the OTA image
            fw_key = FirmwareKey(
                fw_info['fw_manufacturer_id'],
                fw_info['fw_image_type'],
                (fw_info['fw_file_version_MSB'] << 16) | fw_info['fw_file_version_LSB']
            )

            if not key.is_compatible(fw_key):
                continue

            async with aiohttp.ClientSession() as session:
                async with session.get(fw_info['fw_binary_url']) as response:
                    ikea_ota_image = await response.read()

            assert len(ikea_ota_image) > 24
            offset = int.from_bytes(ikea_ota_image[16:20], 'little')
            size = int.from_bytes(ikea_ota_image[20:24], 'little')
            assert len(ikea_ota_image) > offset + size

            ota_image = OTAImage.deserialize(ikea_ota[offset:offset + size])
            assert ota_image.firmware_key == fw_key

            return ota_image

        return None
