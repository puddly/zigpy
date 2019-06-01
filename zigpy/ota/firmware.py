"""OTA Firmware handling."""
import attr

import zigpy.types as t


@attr.s(frozen=True)
class FirmwareKey:
    manufacturer_code = attr.ib(default=None)
    image_type = attr.ib(default=None)
    file_version = attr.ib(default=None)

    def is_compatible(self, key: FirmwareKey) -> bool:
        # We expect the other key to be fully populated
        assert key.version is not None

        if self.file_version is None:
            return (self.manufacturer_code, self.image_type) == (key.manufacturer_code, key.image_type)

        return self == key



@attr.s
class OTAImageSubElement:
    tag_id = attr.ib(default=None)
    data = attr.ib(default=None)

    def serialize(self):
        return t.uint16_t(self.tag_id).serialize() \
            + t.uint32_t(len(self.data)).serialize() \
            + self.data

    @property
    def size(self):
        return 2 + 4 + len(self.data)

    @classmethod
    def deserialize(cls, data):
        tag_id, data = t.uint16_t.deserialize(data)
        length, data = t.uint32_t.deserialize(data)
        assert len(data) >= length
        tag_data, data = data[:length], data[length:]

        return cls(tag_id, tag_data), data


@attr.s
class OTAImage:
    ota_header_control_field = attr.ib(default=None)
    manufacturer_code = attr.ib(default=None)
    image_type = attr.ib(default=None)
    file_version = attr.ib(default=None)
    zigbee_stack_version = attr.ib(default=None)
    ota_header_string = attr.ib(default=None)

    security_credential_version = attr.ib(default=None)
    upgrade_file_destination = attr.ib(default=None)
    minimum_hardware_version = attr.ib(default=None)
    maximum_hardware_version = attr.ib(default=None)
    unknown_optional_fields = attr.ib(default=None)

    subelements = attr.ib(default=attr.Factory(list))

    def __attrs_post_init__(self):
        self._cached_image = None

    def get_block(self, offset, size):
        # Firmware images are assumed to be immutable once a block has been requested
        if self._cached_image is None:
            self._cached_image = self.serialize()

        if offset > len(self._cached_image):
            raise ValueError('Offset exceeds total image size')

        return self._cached_image[offset:offset + size]

    @property
    def firmware_key(self) -> FirmwareKey:
        return FirmwareKey(self.manufacturer_code, self.image_type, self.file_version)

    def should_upgrade(self, manufacturer_code, img_type, ver, hw_ver) -> bool:
        """Check if it should upgrade"""

        if self.manufacturer_code != manufacturer_code or self.image_type != img_type:
            return False

        # Firmware downgrades are possible so this shouldn't be a hard requirement
        if self.file_version <= ver:
            return False

        if hw_ver is not None:
            if self.minimum_hardware_version is not None and self.minimum_hardware_version > hw_ver:
                return False

            if self.maximum_hardware_version is not None and self.maximum_hardware_version < hw_ver:
                return False

        return True

    @property
    def _total_header_length(self):
        # Minimal header
        total = 56

        # Add in the optional fields
        total += 1 if self.security_credential_version is not None else 0
        total += 8 if self.upgrade_file_destination is not None else 0
        total += 2 if self.minimum_hardware_version is not None else 0
        total += 2 if self.maximum_hardware_version is not None else 0
        total += len(self.unknown_optional_fields or b'')

        return total

    @property
    def size(self):
        if self._cached_image is not None:
            return len(self._cached_image)

        return self._total_header_length + sum(e.size for e in self.subelements)

    @classmethod
    def deserialize(cls, data):
        data_copy = data
        instance = cls()

        ota_upgrade_file_identifier, data = t.uint32_t.deserialize(data)
        assert ota_upgrade_file_identifier == 0x0BEEF11E

        ota_header_version, data = t.uint16_t.deserialize(data)
        assert ota_header_version == 0x0100

        ota_header_length, data = t.uint16_t.deserialize(data)
        instance.ota_header_control_field, data = t.uint16_t.deserialize(data)
        instance.manufacturer_code, data = t.uint16_t.deserialize(data)
        instance.image_type, data = t.uint16_t.deserialize(data)
        instance.file_version, data = t.uint32_t.deserialize(data)
        instance.zigbee_stack_version, data = t.uint16_t.deserialize(data)
        instance.ota_header_string, data = data[:32], data[32:]

        total_image_size, data = t.uint32_t.deserialize(data)

        optional_fields_length = ota_header_length - 56

        if optional_fields_length >= 1:
            instance.security_credential_version, data = t.uint8_t.deserialize(data)
            optional_fields_length -= 1

        if optional_fields_length >= 8:
            instance.upgrade_file_destination, data = t.EUI64.deserialize(data)
            optional_fields_length -= 8

        if optional_fields_length >= 2:
            instance.minimum_hardware_version, data = t.uint16_t.deserialize(data)
            optional_fields_length -= 2

        if optional_fields_length >= 2:
            instance.maximum_hardware_version, data = t.uint16_t.deserialize(data)
            optional_fields_length -= 2

        if optional_fields_length > 0:
            instance.unknown_optional_fields, data = data[:optional_fields_length], data[optional_fields_length:]

        num_sub_elements_bytes = total_image_size - ota_header_length

        while num_sub_elements_bytes > 0:
            subelement, data = OTAImageSubElement.deserialize(data)
            instance.subelements.append(subelement)

            num_sub_elements_bytes -= len(subelement.serialize())

        # This can only happen if the last subelement is corrupted
        # and data contains more than an OTA image, which is unlikely
        assert num_sub_elements_bytes == 0

        # Final sanity check
        assert data_copy == instance.serialize() + data

        return instance, data

    def serialize(self):
        result = bytearray()
        result += t.uint32_t(0x0BEEF11E).serialize()
        result += t.uint16_t(0x0100).serialize()
        result += t.uint16_t(self._total_header_length).serialize()

        result += t.uint16_t(self.ota_header_control_field).serialize()
        result += t.uint16_t(self.manufacturer_code).serialize()
        result += t.uint16_t(self.image_type).serialize()
        result += t.uint32_t(self.file_version).serialize()
        result += t.uint16_t(self.zigbee_stack_version).serialize()

        assert len(self.ota_header_string) == 32
        result += self.ota_header_string
        result += t.uint32_t(self.size).serialize()

        # Make sure the optional fields are all set in order or not at all
        optional_fields = (self.security_credential_version, self.upgrade_file_destination,
                           self.minimum_hardware_version, self.maximum_hardware_version)

        assert all(optional_fields[:sum(f is not None for f in optional_fields)])

        if self.security_credential_version is not None:
            result += t.uint8_t(self.security_credential_version).serialize()

        if self.upgrade_file_destination is not None:
            result += t.EUI64(self.upgrade_file_destination).serialize()

        if self.minimum_hardware_version is not None:
            result += t.uint16_t(self.minimum_hardware_version).serialize()

        if self.maximum_hardware_version is not None:
            result += t.uint16_t(self.maximum_hardware_version).serialize()

        if self.unknown_optional_fields is not None:
            result += self.unknown_optional_fields

        for subelement in self.subelements:
            result += subelement.serialize()

        return result
