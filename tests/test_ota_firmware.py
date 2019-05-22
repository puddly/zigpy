from unittest import mock

import pytest

from zigpy.ota.firmware import Firmware, FirmwareKey, OTAImage, OTAImageSubElement

MANUFACTURER_ID = 0x0001
IMAGE_TYPE = 0x1111


@pytest.fixture
def key():
    return FirmwareKey(MANUFACTURER_ID, IMAGE_TYPE)


@pytest.fixture
def ota_image(key):
    image = OTAImage()
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
    image.subelements = [OTAImageSubElement(0x3333, b'TEST')]

    return image


def test_ota_image_subelement():
    assert OTAImageSubElement(0xAAFF, b'').serialize() == b'\xff\xaa\x00\x00\x00\x00'
    assert OTAImageSubElement(0xFFAA, b'a').serialize() == b'\xaa\xff\x01\x00\x00\x00a'


def test_ota_image(ota_image):
    new_ota_image, remaining = OTAImage.deserialize(ota_image.serialize())

    assert not remaining
    assert new_ota_image == ota_image


def test_firmware_key():
    key = FirmwareKey(MANUFACTURER_ID, IMAGE_TYPE)
    assert key.manufacturer_id is MANUFACTURER_ID
    assert key.image_type is IMAGE_TYPE


def test_firmware(key, ota_image):
    s = mock.sentinel
    frm = Firmware(key, s.url, ota_image)

    assert frm.key == key
    assert frm.url == s.url
    assert frm.image == ota_image
    assert frm.size == len(ota_image.serialize())


def test_upgradeable(key, ota_image):
    s = mock.sentinel
    frm = Firmware(key, s.url, ota_image)

    assert frm.upgradeable(MANUFACTURER_ID, IMAGE_TYPE, ota_image.file_version - 1, None)
    assert not frm.upgradeable(MANUFACTURER_ID, IMAGE_TYPE, ota_image.file_version, None)
    assert not frm.upgradeable(MANUFACTURER_ID, IMAGE_TYPE, ota_image.file_version + 1, None)
