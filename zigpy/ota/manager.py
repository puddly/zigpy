"""OTA manager for Zigpy. initial implementation from: https://github.com/zigpy/zigpy/pull/1102"""
from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Ota

if TYPE_CHECKING:
    from zigpy.device import Device
    from zigpy.ota.provider import OtaImageWithMetadata


# Devices often ask for bigger blocks than radios can send
MAXIMUM_IMAGE_BLOCK_SIZE = 40


def find_ota_cluster(device: Device) -> Ota:
    """Finds the first OTA cluster available on the device."""
    for ep in device.non_zdo_endpoints:
        if Ota.cluster_id in ep.out_clusters:
            return ep.out_clusters[Ota.cluster_id]
    else:
        raise ValueError("Device has no OTA cluster")


class OTAManager:
    """Class to manage OTA updates for a device."""

    def __init__(
        self,
        device: Device,
        image: OtaImageWithMetadata,
        progress_callback=None,
    ) -> None:
        self.device = device
        self.ota_cluster = find_ota_cluster(device)

        self.image = image
        self._image_data = image.firmware.serialize()
        self.progress_callback = progress_callback

        self._upgrade_end_future = asyncio.get_running_loop().create_future()
        self.stack = contextlib.ExitStack()

    def __enter__(self) -> OTAManager:
        self.stack.enter_context(
            self.device._application.callback_for_response(
                src=self.device,
                filters=[
                    Ota.ServerCommandDefs.query_next_image.schema(),
                ],
                callback=self._image_query_req,
            )
        )

        self.stack.enter_context(
            self.device._application.callback_for_response(
                src=self.device,
                filters=[
                    Ota.ServerCommandDefs.image_block.schema(),
                ],
                callback=self._image_block_req,
            )
        )

        self.stack.enter_context(
            self.device._application.callback_for_response(
                src=self.device,
                filters=[
                    Ota.ServerCommandDefs.upgrade_end.schema(),
                ],
                callback=self._upgrade_end,
            )
        )

        return self

    def __exit__(self, *exc_details) -> None:
        self.stack.close()

    async def _image_query_req(
        self, hdr: foundation.ZCLHeader, command: Ota.QueryNextImageCommand
    ) -> None:
        """Handle image query request."""
        try:
            assert self.ota_cluster
            await self.ota_cluster.query_next_image_response(
                status=foundation.Status.SUCCESS,
                manufacturer_code=self.image.firmware.header.manufacturer_id,
                image_type=self.image.firmware.header.image_type,
                file_version=self.image.firmware.header.file_version,
                image_size=self.image.firmware.header.image_size,
                tsn=hdr.tsn,
            )
        except Exception as ex:
            self.device.debug("OTA query_next_image handler - exception: %s", ex)
            self._upgrade_end_future.set_result(foundation.Status.FAILURE)

    async def _image_block_req(
        self, hdr: foundation.ZCLHeader, command: Ota.ImageBlockCommand
    ) -> None:
        """Handle image block request."""
        block = self._image_data[
            command.file_offset : command.file_offset
            + min(MAXIMUM_IMAGE_BLOCK_SIZE, command.maximum_data_size)
        ]

        if not block:
            try:
                assert self.ota_cluster
                await self.ota_cluster.image_block_response(
                    status=foundation.Status.MALFORMED_COMMAND,
                    tsn=hdr.tsn,
                )
            except Exception as ex:
                self.device.debug(
                    "OTA image_block handler[MALFORMED_COMMAND] - exception: %s", ex
                )

            self._upgrade_end_future.set_result(foundation.Status.MALFORMED_COMMAND)
            return

        try:
            assert self.ota_cluster
            await self.ota_cluster.image_block_response(
                status=foundation.Status.SUCCESS,
                manufacturer_code=self.image.firmware.header.manufacturer_id,
                image_type=self.image.firmware.header.image_type,
                file_version=self.image.firmware.header.file_version,
                file_offset=command.file_offset,
                image_data=block,
                tsn=hdr.tsn,
            )

            if self.progress_callback is not None:
                self.progress_callback(
                    command.file_offset + len(block), len(self._image_data)
                )
        except Exception as ex:
            self.device.debug("OTA image_block handler - exception: %s", ex)
            self._upgrade_end_future.set_result(foundation.Status.FAILURE)

    async def _upgrade_end(
        self, hdr: foundation.ZCLHeader, command: foundation.CommandSchema
    ) -> None:
        """Handle upgrade end request."""
        try:
            assert self.ota_cluster
            await self.ota_cluster.upgrade_end_response(
                manufacturer_code=self.image.firmware.header.manufacturer_id,
                image_type=self.image.firmware.header.image_type,
                file_version=self.image.firmware.header.file_version,
                current_time=0x00000000,
                upgrade_time=0x00000000,
                tsn=hdr.tsn,
            )

            self._upgrade_end_future.set_result(command.status)
        except Exception as ex:
            self.device.debug("OTA upgrade_end handler - exception: %s", ex)
            self._upgrade_end_future.set_result(foundation.Status.FAILURE)

    async def notify(self) -> None:
        """Notify device of new image."""
        try:
            assert self.ota_cluster
            await self.ota_cluster.image_notify(
                payload_type=(
                    self.ota_cluster.ImageNotifyCommand.PayloadType.QueryJitter
                ),
                query_jitter=100,
            )
        except Exception as ex:
            self.device.debug("OTA image_notify handler - exception: %s", ex)
            self._upgrade_end_future.set_result(foundation.Status.FAILURE)

    async def wait(self) -> foundation.Status:
        """Wait for upgrade end response."""
        return await self._upgrade_end_future


async def update_firmware(
    device: Device,
    image: OtaImageWithMetadata,
    progress_callback: callable = None,
    force: bool = False,
) -> foundation.Status:
    """Update the firmware on a Zigbee device."""
    if force:
        # Force it to send the image even if it's the same version
        image = image.replace(
            image=image.firmware.replace(
                header=image.firmware.header.replace(
                    file_version=0xFFFFFFFF - 1,
                )
            )
        )

    def progress(current: int, total: int):
        progress = (100 * current) / total
        device.info(
            "OTA upgrade progress: (%d / %d): %0.4f%%",
            current,
            total,
            progress,
        )
        if progress_callback is not None:
            progress_callback(current, total, progress)

    with OTAManager(device, image, progress_callback=progress) as ota:
        await ota.notify()
        return await ota.wait()
