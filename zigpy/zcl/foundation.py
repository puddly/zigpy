from __future__ import annotations

import dataclasses
import keyword
from typing import Any, Optional, Tuple
import warnings

import zigpy.types as t


class Status(t.enum8):
    SUCCESS = 0x00  # Operation was successful.
    FAILURE = 0x01  # Operation was not successful
    NOT_AUTHORIZED = 0x7E  # The sender of the command does not have
    RESERVED_FIELD_NOT_ZERO = 0x7F  # A reserved field/subfield/bit contains a
    MALFORMED_COMMAND = 0x80  # The command appears to contain the wrong
    UNSUP_CLUSTER_COMMAND = 0x81  # The specified cluster command is not
    UNSUP_GENERAL_COMMAND = 0x82  # The specified general ZCL command is not
    UNSUP_MANUF_CLUSTER_COMMAND = 0x83  # A manufacturer specific unicast,
    UNSUP_MANUF_GENERAL_COMMAND = 0x84  # A manufacturer specific unicast, ZCL
    INVALID_FIELD = 0x85  # At least one field of the command contains an
    UNSUPPORTED_ATTRIBUTE = 0x86  # The specified attribute does not exist on
    INVALID_VALUE = 0x87  # Out of range error, or set to a reserved value.
    READ_ONLY = 0x88  # Attempt to write a read only attribute.
    INSUFFICIENT_SPACE = 0x89  # An operation (e.g. an attempt to create an
    DUPLICATE_EXISTS = 0x8A  # An attempt to create an entry in a table failed
    NOT_FOUND = 0x8B  # The requested information (e.g. table entry)
    UNREPORTABLE_ATTRIBUTE = 0x8C  # Periodic reports cannot be issued for this
    INVALID_DATA_TYPE = 0x8D  # The data type given for an attribute is
    INVALID_SELECTOR = 0x8E  # The selector for an attribute is incorrect.
    WRITE_ONLY = 0x8F  # A request has been made to read an attribute
    INCONSISTENT_STARTUP_STATE = 0x90  # Setting the requested values would put
    DEFINED_OUT_OF_BAND = 0x91  # An attempt has been made to write an
    INCONSISTENT = (
        0x92  # The supplied values (e.g., contents of table cells) are inconsistent
    )
    ACTION_DENIED = 0x93  # The credentials presented by the device sending the
    TIMEOUT = 0x94  # The exchange was aborted due to excessive response time
    ABORT = 0x95  # Failed case when a client or a server decides to abort the upgrade process
    INVALID_IMAGE = 0x96  # Invalid OTA upgrade image (ex. failed signature
    WAIT_FOR_DATA = 0x97  # Server does not have data block available yet
    NO_IMAGE_AVAILABLE = 0x98  # No OTA upgrade image available for a particular client
    REQUIRE_MORE_IMAGE = 0x99  # The client still requires more OTA upgrade image
    NOTIFICATION_PENDING = 0x9A  # The command has been received and is being processed
    HARDWARE_FAILURE = 0xC0  # An operation was unsuccessful due to a
    SOFTWARE_FAILURE = 0xC1  # An operation was unsuccessful due to a
    CALIBRATION_ERROR = 0xC2  # An error occurred during calibration
    UNSUPPORTED_CLUSTER = 0xC3  # The cluster is not supported

    @classmethod
    def _missing_(cls, value):
        chained = t.APSStatus(value)
        status = cls._member_type_.__new__(cls, chained.value)
        status._name_ = chained.name
        status._value_ = value
        return status


class Analog:
    pass


class Discrete:
    pass


class Null:
    pass


class Unknown(t.NoData):
    pass


class TypeValue:
    def __init__(self, python_type=None, value=None):
        # Copy constructor
        if isinstance(python_type, TypeValue):
            other = python_type

            python_type = other.type
            value = other.value

        self.type = python_type
        self.value = value

    def serialize(self):
        return self.type.to_bytes(1, "little") + self.value.serialize()

    @classmethod
    def deserialize(cls, data):
        self = cls()
        self.type, data = t.uint8_t.deserialize(data)
        python_type = DATA_TYPES[self.type][1]
        self.value, data = python_type.deserialize(data)
        return self, data

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"type={type(self.value).__name__}, value={self.value!r}"
            f")"
        )


class TypedCollection(TypeValue):
    @classmethod
    def deserialize(cls, data):
        self = cls()
        self.type, data = data[0], data[1:]
        python_item_type = DATA_TYPES[self.type][1]
        python_type = t.LVList[python_item_type]
        self.value, data = python_type.deserialize(data)
        return self, data


class Array(TypedCollection):
    pass


class Bag(TypedCollection):
    pass


class Set(TypedCollection):
    pass  # ToDo: Make this a real set?


class DataTypes(dict):
    """DataTypes container."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._idx_by_class = {
            _type: type_id for type_id, (name, _type, ad) in self.items()
        }

    def pytype_to_datatype_id(self, python_type) -> int:
        """Return Zigbee Datatype ID for a give python type."""

        # We return the most specific parent class
        for cls in python_type.__mro__:
            if cls in self._idx_by_class:
                return self._idx_by_class[cls]

        return 0xFF


class ZCLStructure(t.LVList, item_type=TypeValue, length_type=t.uint16_t):
    """ZCL Structure data type."""


DATA_TYPES = DataTypes(
    {
        0x00: ("No data", t.NoData, Null),
        0x08: ("General", t.data8, Discrete),
        0x09: ("General", t.data16, Discrete),
        0x0A: ("General", t.data24, Discrete),
        0x0B: ("General", t.data32, Discrete),
        0x0C: ("General", t.data40, Discrete),
        0x0D: ("General", t.data48, Discrete),
        0x0E: ("General", t.data56, Discrete),
        0x0F: ("General", t.data64, Discrete),
        0x10: ("Boolean", t.Bool, Discrete),
        0x18: ("Bitmap", t.bitmap8, Discrete),
        0x19: ("Bitmap", t.bitmap16, Discrete),
        0x1A: ("Bitmap", t.bitmap24, Discrete),
        0x1B: ("Bitmap", t.bitmap32, Discrete),
        0x1C: ("Bitmap", t.bitmap40, Discrete),
        0x1D: ("Bitmap", t.bitmap48, Discrete),
        0x1E: ("Bitmap", t.bitmap56, Discrete),
        0x1F: ("Bitmap", t.bitmap64, Discrete),
        0x20: ("Unsigned Integer", t.uint8_t, Analog),
        0x21: ("Unsigned Integer", t.uint16_t, Analog),
        0x22: ("Unsigned Integer", t.uint24_t, Analog),
        0x23: ("Unsigned Integer", t.uint32_t, Analog),
        0x24: ("Unsigned Integer", t.uint40_t, Analog),
        0x25: ("Unsigned Integer", t.uint48_t, Analog),
        0x26: ("Unsigned Integer", t.uint56_t, Analog),
        0x27: ("Unsigned Integer", t.uint64_t, Analog),
        0x28: ("Signed Integer", t.int8s, Analog),
        0x29: ("Signed Integer", t.int16s, Analog),
        0x2A: ("Signed Integer", t.int24s, Analog),
        0x2B: ("Signed Integer", t.int32s, Analog),
        0x2C: ("Signed Integer", t.int40s, Analog),
        0x2D: ("Signed Integer", t.int48s, Analog),
        0x2E: ("Signed Integer", t.int56s, Analog),
        0x2F: ("Signed Integer", t.int64s, Analog),
        0x30: ("Enumeration", t.enum8, Discrete),
        0x31: ("Enumeration", t.enum16, Discrete),
        0x38: ("Floating point", t.Half, Analog),
        0x39: ("Floating point", t.Single, Analog),
        0x3A: ("Floating point", t.Double, Analog),
        0x41: ("Octet string", t.LVBytes, Discrete),
        0x42: ("Character string", t.CharacterString, Discrete),
        0x43: ("Long octet string", t.LongOctetString, Discrete),
        0x44: ("Long character string", t.LongCharacterString, Discrete),
        0x48: ("Array", Array, Discrete),
        0x4C: ("Structure", ZCLStructure, Discrete),
        0x50: ("Set", Set, Discrete),
        0x51: ("Bag", Bag, Discrete),
        0xE0: ("Time of day", t.TimeOfDay, Analog),
        0xE1: ("Date", t.Date, Analog),
        0xE2: ("UTCTime", t.UTCTime, Analog),
        0xE8: ("Cluster ID", t.ClusterId, Discrete),
        0xE9: ("Attribute ID", t.AttributeId, Discrete),
        0xEA: ("BACNet OID", t.BACNetOid, Discrete),
        0xF0: ("IEEE address", t.EUI64, Discrete),
        0xF1: ("128-bit security key", t.KeyData, Discrete),
        0xFF: ("Unknown", Unknown, None),
    }
)


class ZCLCommand(t.Struct):
    """
    Base class for ZCL commands. Commands can be defined either by subclassing or by
    directly calling `ZCLCommand` with a `schema` dictionary.
    """

    id: t.uint8_t = None
    name: str = None
    frame_type: FrameType = None
    direction: Direction = None
    is_manufacturer_specific: bool = None

    def __init_subclass__(
        cls,
        *,
        id: t.uint8_t,
        frame_type: FrameType = FrameType.CLUSTER_COMMAND,
        direction: Direction = Direction.CLIENT_TO_SERVER,
        is_manufacturer_specific: bool = False,
    ):
        cls.id = id
        cls.name = cls.__name__
        cls.frame_type = frame_type
        cls.direction = direction
        cls.is_manufacturer_specific = is_manufacturer_specific

    def __new__(cls, *, id, frame_type, direction, is_manufacturer_specific, schema):
        """
        Overloaded class constructor that allows for subclasses to be created inline.
        For example:

        ```Python
        class TestCommand(ZCLCommand, id=0x1234, direction=Direction.CLIENT_TO_SERVER):
            param1: t.uint8_t
            param2: t.uint8_t = t.StructField(optional=True)

        TestCommand = ZCLCommand(
            id=0x1234,
            direction=Direction.CLIENT_TO_SERVER,
            is_manufacturer_specific=False,
            schema={
                "param1": t.uint8_t,
                "param2?": t.uint8_t,
            }
        )
        ```
        """

        cls_attrs = {
            "__annotations__": {},
        }

        for name, param_type in schema.items():
            plain_name = name.rstrip("?")

            # Make sure parameters with names like "foo bar" and "class" can't exist
            if not plain_name.isidentifier() or keyword.iskeyword(plain_name):
                raise ValueError(
                    f"Schema parameter {name} must be a valid Python identifier"
                )

            cls_attrs["__annotations__"][plain_name] = "None"
            cls_attrs[plain_name] = t.StructField(
                type=param_type,
                optional=name.endswith("?"),
            )

        # Create a subclass on the fly
        return type(
            name,
            (cls,),
            cls_attrs,
            id=id,
            frame_type=frame_type,
            direction=direction,
            is_manufacturer_specific=is_manufacturer_specific,
        )


@dataclasses.dataclass(frozen=True)
class ZCLAttributeDef:
    id: t.uint16_t = None
    name: str = None
    type: type = None
    access: str = "rw"
    is_manufacturer_specific: bool = False

    def __post_init__(self):
        if not isinstance(self.id, t.uint16_t):
            object.__setattr__(self, "id", t.uint16_t(self.id))

        assert self.access in {None, "r", "w", "rw"}

    def replace(self, **kwargs) -> ZCLAttributeDef:
        return dataclasses.replace(self, **kwargs)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id=0x{self.id:04X}, "
            f"name={self.name!r}, "
            f"type={self.type}, "
            f"access={self.access!r}, "
            f"is_manufacturer_specific={self.is_manufacturer_specific}"
            f")"
        )
