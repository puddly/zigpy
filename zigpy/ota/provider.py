"""OTA Firmware providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
import datetime
import hashlib
import io
import logging
import os
import os.path
import pathlib
import re
import ssl
import sys
import tarfile
import typing
import urllib.parse

import aiohttp
import attr
import attrs

from zigpy.config import CONF_OTA_DIR, CONF_OTA_SONOFF_URL
from zigpy.ota.image import BaseOTAImage, ImageKey, OTAImageHeader, parse_ota_image
import zigpy.util

LOGGER = logging.getLogger(__name__)


class BaseOtaImage:
    file_version: int
    manufacturer_code: int
    image_type: int

    checksum: str | None
    file_size: int | None

    manufacturer_names: list[str] = attrs.Factory(list)
    model_names: list[str] = attrs.Factory(list)

    changelog: str | None

    min_hardware_version: int | None
    max_hardware_version: int | None
    min_current_file_version: int | None
    max_current_file_version: int | None

    async def fetch(self) -> BaseOTAImage:
        data = await self._fetch()

        if self.file_size is not None and len(data) != self.file_size:
            raise ValueError(
                f"Image size is invalid: expected {self.file_size},"
                f" got {len(data)}"
            )

        if self.checksum is not None:
            algorithm, checksum = self.checksum.split(":")
            hasher = hashlib.new(algorithm)
            await asyncio.get_running_loop().run_in_executor(None, hasher.update, data)

            if hasher.hexdigest() != self.checksum:
                raise ValueError(
                    f"Image checksum is invalid: expected {self.checksum},"
                    f" got {hasher.hexdigest()}"
                )

        return self._cached_contents


class RemoteOtaImage(BaseOTAImage):
    url: str

    async def _fetch(self) -> bytes:
        async with aiohttp.ClientSession(raise_for_status=True) as req:
            async with req.get(self.url) as rsp:
                return await rsp.read()


class LocalOtaImage(BaseOTAImage):
    path: pathlib.Path

    async def _fetch(self) -> bytes:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.path.read_bytes)


class SalusRemoteOtaImage(RemoteOtaImage):
    async def _fetch(self) -> bytes:
        loop = asyncio.get_running_loop()
        data = await super()._fetch()

        return await loop.run_in_executor(None, self._extract_ota, data)

    def _extract_ota(self, data: bytes) -> bytes:
        img_tgz = io.BytesIO(data)

        with tarfile.open(fileobj=img_tgz) as tar:
            for item in tar:
                if not item.name.endswith(".ota"):
                    continue

                f = tar.extractfile(item)

                if f is None:
                    raise ValueError(f"Could not extract {item.name} from OTA archive")

                return f.read()

        raise ValueError("No OTA image found in archive")


async def load_ikea_images():
    # `openssl s_client -connect fw.ota.homesmart.ikea.com:443 -showcerts`
    ssl_ctx = ssl.create_default_context(
        cadata="""\
-----BEGIN CERTIFICATE-----
MIICGDCCAZ+gAwIBAgIUdfH0KDnENv/dEcxH8iVqGGGDqrowCgYIKoZIzj0EAwMw
SzELMAkGA1UEBhMCU0UxGjAYBgNVBAoMEUlLRUEgb2YgU3dlZGVuIEFCMSAwHgYD
VQQDDBdJS0VBIEhvbWUgc21hcnQgUm9vdCBDQTAgFw0yMTA1MjYxOTAxMDlaGA8y
MDcxMDUxNDE5MDEwOFowSzELMAkGA1UEBhMCU0UxGjAYBgNVBAoMEUlLRUEgb2Yg
U3dlZGVuIEFCMSAwHgYDVQQDDBdJS0VBIEhvbWUgc21hcnQgUm9vdCBDQTB2MBAG
ByqGSM49AgEGBSuBBAAiA2IABIDRUvKGFMUu2zIhTdgfrfNcPULwMlc0TGSrDLBA
oTr0SMMV4044CRZQbl81N4qiuHGhFzCnXapZogkiVuFu7ZqSslsFuELFjc6ZxBjk
Kmud+pQM6QQdsKTE/cS06dA+P6NCMEAwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4E
FgQUcdlEnfX0MyZA4zAdY6CLOye9wfwwDgYDVR0PAQH/BAQDAgGGMAoGCCqGSM49
BAMDA2cAMGQCMG6mFIeB2GCFch3r0Gre4xRH+f5pn/bwLr9yGKywpeWvnUPsQ1KW
ckMLyxbeNPXdQQIwQc2YZDq/Mz0mOkoheTUWiZxK2a5bk0Uz1XuGshXmQvEg5TGy
2kVHW/Mz9/xwpy4u
-----END CERTIFICATE-----"""
    )

    async with aiohttp.ClientSession(headers={"accept": "application/json;q=0.9,*/*;q=0.8"}, raise_for_status=True) as req:
        async with req.get("https://fw.ota.homesmart.ikea.com/DIRIGERA/version_info.json", ssl=ssl_ctx) as rsp:
            # IKEA does not always respond with an appropriate Content-Type but the
            # response is always JSON
            fw_lst = await rsp.json(content_type=None)

    for fw in fw_lst:
        # Skip the gateway image
        if "fw_image_type" not in fw:
            continue

        file_version_match = re.match(r".*_v(?P<v>\d+)_.*", fw["fw_binary_url"])

        yield RemoteOtaImage(
            file_version=int(file_version_match.group("v"), 10),
            manufacturer_code=4476,
            image_type=fw["fw_type"],
            checksum="sha3-256:" + fw["fw_sha3_256"],
            url=fw["fw_binary_url"],
        )


async def load_ledvance_images():
    async with aiohttp.ClientSession(headers={"accept": "application/json"}, raise_for_status=True) as req:
        async with req.get("https://api.update.ledvance.com/v1/zigbee/firmwares") as rsp:
            fw_lst = await rsp.json()

    for fw in fw_lst["firmwares"]:
        identity = fw["identity"]
        version_parts = identity["version"]

        # This matches the OTA file's `image_version` for every image
        version = (
            (version_parts["major"] << 24)
            | (version_parts["minor"] << 16)
            | (version_parts["build"] << 8)
            | (version_parts["revision"] << 0)
        )

        yield RemoteOtaImage(
            file_version=int(fw["fullName"].split("/")[1], 16),
            manufacturer_code=identity["company"],
            image_type=identity["product"],
            checksum="sha256:" + fw["shA256"],
            file_size=fw["length"]
            url=(
                "https://api.update.ledvance.com/v1/zigbee/firmwares/download?"
                + urllib.parse.urlencode(
                    {
                        "Company": identity["company"],
                        "Product": identity["product"],
                        "Version": (
                            f"{version_parts['major']}.{version_parts['minor']}"
                            f".{version_parts['build']}.{version_parts['revision']}"
                        ),
                    }
                )
            ),
            release_notes=fw["releaseNotes"],
        )


async def load_salus_images():
    async with aiohttp.ClientSession(headers={"accept": "application/json"}, raise_for_status=True) as req:
        async with req.get("https://eu.salusconnect.io/demo/default/status/firmware") as rsp:
            fw_lst = await rsp.json()

    for fw in fw_lst["versions"]:
        yield SalusRemoteOtaImage(
            file_version=int(fw["version"]),
            model_names=[fw["model"]],
            manufacturer_code=4216,
            image_type=None,
            checksum=None,
            file_size=None,
            url=fw["url"],
        )


async def load_sonoff_images():
    async with aiohttp.ClientSession(headers={"accept": "application/json;q=0.9,*/*;q=0.8"}, raise_for_status=True) as req:
        async with req.get("https://zigbee-ota.sonoff.tech/releases/upgrade.json") as rsp:
            fw_lst = await rsp.json()

    for fw in fw_lst:
        yield RemoteOtaImage(
            file_version=fw["fw_file_version"],
            manufacturer_code=fw["fw_manufacturer_id"],
            image_type=fw["fw_image_type"],
            file_size=fw["fw_filesize"],
            url=fw["fw_binary_url"],
        )


async def load_inovelli_images():
    async with aiohttp.ClientSession(headers={"accept": "application/json"}, raise_for_status=True) as req:
        async with req.get("https://files.inovelli.com/firmware/firmware-zha.json") as rsp:
            fw_lst = await rsp.json()

    for model, firmwares in fw_lst.items():
        for fw in firmwares:
            yield RemoteOtaImage(
                file_version=int(fw["version"], 16),
                manufacturer_id=fw["manufacturer_id"],
                image_type=fw["image_type"],
                model_names=[model],
                checksum=None,
                file_size=None,
                url=fw["firmware"],
            )


async def load_third_reality_images():
    async with aiohttp.ClientSession(headers={"accept": "application/json"}, raise_for_status=True) as req:
        async with req.get("https://tr-zha.s3.amazonaws.com/firmware.json") as rsp:
            fw_lst = await rsp.json()

    for fw in fw_lst["versions"]:
        yield RemoteOtaImage(
            file_version=fw["fileVersion"],
            manufacturer_id=fw["manufacturerId"],
            model_names=[fw["modelId"]],
            image_type=fw["imageType"],
            checksum=None,
            file_size=None,
            url=fw["url"],
        )


async def load_remote_provider_images(provider_url: str):
    async with aiohttp.ClientSession(headers={"accept": "application/json"}, raise_for_status=True) as req:
        async with req.get(provider_url) as rsp:
            fw_lst = await rsp.json()

    for fw in fw_lst:
        yield RemoteOtaImage(
            file_version=fw["file_version"],
            manufacturer_id=fw["manufacturer_id"],
            image_type=fw["image_type"],
            manufacturer_names=[],
            model_names=[] if "model_names" not in fw else fw["model_names"],
            checksum=fw["checksum"],
            file_size=None,
            url=fw["binary_url"],
            min_hardware_version=fw.get("min_hardware_version"),
            max_hardware_version=fw.get("max_hardware_version"),
            min_current_file_version=fw.get("min_current_file_version"),
            max_current_file_version=fw.get("max_current_file_version"),
        )


async def load_advanced_file_images(ota_dir: pathlib.Path):
    loop = asyncio.get_running_loop()

    for path in ota_dir.rglob("*"):
        if not path.is_file():
            continue

        data = await loop.run_in_executor(None, path.read_bytes)

        try:
            image, _ = parse_ota_image(data)
        except Exception as exc:
            LOGGER.debug("Failed to parse image %s: %r", path, exc)
            continue

        yield LocalOtaImage(
            file_version=image.header.file_version,
            manufacturer_code=image.header.manufacturer_id,
            image_type=image.header.image_type,
            checksum=None,
            file_size=len(data),
            manufacturer_names=[],
            model_names=[],
            changelog=None,
            min_hardware_version=image.header.minimum_hardware_version,
            max_hardware_version=image.header.maximum_hardware_version,
        )


def _load_z2m_index(index: dict, *, index_root: pathlib.Path | None = None):
    loop = asyncio.get_running_loop()

    for obj in index:
        if "path" in obj and index_root is not None:
            yield LocalOtaImage(
                file_version=obj["fileVersion"],
                manufacturer_code=obj["manufacturerCode"],
                image_type=obj["imageType"],
                checksum="sha512:" + obj["sha512"],
                file_size=obj["fileSize"],
                manufacturer_names=obj.get("manufacturerNames", []),
                model_names=[obj["modelId"]] if "modelId" in obj else [],
                path=index_root / obj["path"],
            )
        else:
            yield RemoteOtaImage(
                file_version=obj["fileVersion"],
                manufacturer_code=obj["manufacturerCode"],
                image_type=obj["imageType"],
                checksum="sha512:" + obj["sha512"],
                file_size=obj["fileSize"],
                manufacturer_names=obj.get("manufacturerNames", []),
                model_names=[obj["modelId"]] if "modelId" in obj else [],
                url=obj["url"],
            )


async def load_z2m_index_local(index_path: pathlib.Path):
    index = next(index_path.rglob("index.json"), None)

    if index is None:
        raise ValueError(f"Not Z2M index file exists in {index_path}")

    yield from _load_z2m_index(index, index_root=index_path.parent)


async def load_z2m_index_remote(index_url: str):
    # https://raw.githubusercontent.com/Koenkk/zigbee-OTA/master/index.json
    async with aiohttp.ClientSession(headers={"accept": "application/json"}, raise_for_status=True) as req:
        async with req.get(provider_url) as rsp:
            fw_lst = await rsp.json()

    yield from _load_z2m_index(fw_lst)
