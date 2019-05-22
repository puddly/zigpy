import asyncio
from unittest import mock

import pytest

import zigpy.application
import zigpy.ota
import zigpy.ota.firmware
import zigpy.ota.provider

MANUFACTURER_ID = 0x0001
IMAGE_TYPE = 0x1111


@pytest.fixture
def ota_image(key):
    image = zigpy.ota.firmware.OTAImage()
    image.ota_header_control_field = 0x0000
    image.manufacturer_code = key.manufacturer_id
    image.image_type = key.image_type
    image.file_version = 0x1111
    image.zigbee_stack_version = 0x2222
    image.ota_header_string = b'test' * 8
    image.security_credential_version = None
    image.upgrade_file_destination = None
    image.minimum_hardware_version = None
    image.maximum_hardare_version = None
    image.unknown_optional_fields = None
    image.subelements = [zigpy.ota.firmware.OTAImageSubElement(0x3333, b'TEST')]

    return image


@pytest.fixture
def firmware(key, ota_image):
    return zigpy.ota.firmware.Firmware(key, 'http://example.org/', ota_image)


@pytest.fixture
def key():
    return zigpy.ota.firmware.FirmwareKey(MANUFACTURER_ID, IMAGE_TYPE)


@pytest.fixture
def ota():
    app = mock.MagicMock(spec_set=zigpy.application.ControllerApplication)
    tradfri = mock.MagicMock(spec_set=zigpy.ota.provider.Trådfri)
    with mock.patch('zigpy.ota.provider.Trådfri', tradfri):
        return zigpy.ota.OTA(app)


@pytest.mark.asyncio
async def test_ota_initialize(ota):
    init_mock = mock.MagicMock()
    init_mock.side_effect = asyncio.coroutine(mock.MagicMock())
    ota.listener_event = mock.MagicMock(return_value=[init_mock()])
    await ota._initialize()

    assert ota.listener_event.call_count == 1
    assert ota.listener_event.call_args[0][0] == 'initialize_provider'
    assert init_mock.call_count == 1


@pytest.mark.asyncio
async def test_refresh_firmware(ota):
    handler_mock = mock.MagicMock()
    handler_mock.side_effect = asyncio.coroutine(mock.MagicMock())
    ota.listener_event = mock.MagicMock(return_value=[handler_mock()])
    await ota.refresh_firmwares()

    assert ota.listener_event.call_count == 1
    assert ota.listener_event.call_args[0][0] == 'refresh_firmwares'
    assert handler_mock.call_count == 1


def test_initialize(ota):
    ota._initialize = mock.MagicMock()
    ota._initialize.side_effect = asyncio.coroutine(mock.MagicMock())

    assert ota.not_initialized
    ota.initialize()
    assert not ota.not_initialized
    assert ota._initialize.call_count == 1


def test_get_firmware_empty(ota, firmware, key):
    handler_mock = mock.MagicMock(return_value=[None])
    ota.listener_event = mock.MagicMock(side_effect=handler_mock)

    assert len(ota._firmwares) == 0
    res = ota.get_firmware(MANUFACTURER_ID, IMAGE_TYPE)

    assert len(ota._firmwares) == 0
    assert res is None
    assert ota.listener_event.call_count == 1
    assert ota.listener_event.call_args[0][0] == 'get_firmware'
    assert ota.listener_event.call_args[0][1] == key


def test_get_firmware_new(ota, firmware, key, ota_image):
    ota_image.file_version += 1
    newer = zigpy.ota.firmware.Firmware(key, 'http://example.org/', ota_image)

    handler_mock = mock.MagicMock(return_value=[None, firmware, newer])
    ota.listener_event = mock.MagicMock(side_effect=handler_mock)

    assert len(ota._firmwares) == 0
    res = ota.get_firmware(MANUFACTURER_ID, IMAGE_TYPE)

    assert len(ota._firmwares) == 1
    assert res is newer
    assert ota.listener_event.call_count == 1
    assert ota.listener_event.call_args[0][0] == 'get_firmware'
    assert ota.listener_event.call_args[0][1] == key

    ota.listener_event.reset_mock()
    assert len(ota._firmwares) == 1
    res = ota.get_firmware(MANUFACTURER_ID, IMAGE_TYPE)

    assert len(ota._firmwares) == 1
    assert res is newer
    assert ota.listener_event.call_count == 0
