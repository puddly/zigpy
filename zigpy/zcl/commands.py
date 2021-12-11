import inspect

import zigpy.types as t
from zigpy.zcl.foundation import ZCLCommand


def _hex_uint16_repr(v: int) -> str:
    return t.uint16_t(v)._hex_repr()


class ReadAttributeRecord(t.Struct):
    """Read Attribute Record."""

    attrid: t.uint16_t = t.StructField(repr=_hex_uint16_repr)
    status: Status
    value: TypeValue = t.StructField(requires=lambda s: s.status == Status.SUCCESS)


class Attribute(t.Struct):
    attrid: t.uint16_t = t.StructField(repr=_hex_uint16_repr)
    value: TypeValue


class WriteAttributesStatusRecord(t.Struct):
    status: Status
    attrid: t.uint16_t = t.StructField(
        requires=lambda s: s.status != Status.SUCCESS, repr=_hex_uint16_repr
    )


class WriteAttributesResponse(list):
    """Write Attributes response list.

    Response to Write Attributes request should contain only success status, in
    case when all attributes were successfully written or list of status + attr_id
    records for all failed writes.
    """

    @classmethod
    def deserialize(cls, data: bytes) -> Tuple["WriteAttributesResponse", bytes]:
        record, data = WriteAttributesStatusRecord.deserialize(data)
        r = cls([record])
        if record.status == Status.SUCCESS:
            return r, data

        while len(data) >= 3:
            record, data = WriteAttributesStatusRecord.deserialize(data)
            r.append(record)
        return r, data

    def serialize(self):
        failed = [record for record in self if record.status != Status.SUCCESS]
        if failed:
            return b"".join(
                [WriteAttributesStatusRecord(i).serialize() for i in failed]
            )
        return Status.SUCCESS.serialize()


class ReportingDirection(t.enum8):
    SendReports = 0x00
    ReceiveReports = 0x01


class AttributeReportingStatus(t.enum8):
    Pending = 0x00
    Attribute_Reporting_Complete = 0x01


class AttributeReportingConfig:
    def __init__(self, other=None):
        if isinstance(other, self.__class__):
            self.direction = other.direction
            self.attrid = other.attrid
            if self.direction == ReportingDirection.ReceiveReports:
                self.timeout = other.timeout
                return
            self.datatype = other.datatype
            self.min_interval = other.min_interval
            self.max_interval = other.max_interval
            self.reportable_change = other.reportable_change

    def serialize(self):
        r = ReportingDirection(self.direction).serialize()
        r += t.uint16_t(self.attrid).serialize()
        if self.direction == ReportingDirection.ReceiveReports:
            r += t.uint16_t(self.timeout).serialize()
        else:
            r += t.uint8_t(self.datatype).serialize()
            r += t.uint16_t(self.min_interval).serialize()
            r += t.uint16_t(self.max_interval).serialize()
            datatype = DATA_TYPES.get(self.datatype, None)
            if datatype and datatype[2] is Analog:
                datatype = datatype[1]
                r += datatype(self.reportable_change).serialize()
        return r

    @classmethod
    def deserialize(cls, data):
        self = cls()
        self.direction, data = ReportingDirection.deserialize(data)
        self.attrid, data = t.uint16_t.deserialize(data)
        if self.direction == ReportingDirection.ReceiveReports:
            # Requesting things to be received by me
            self.timeout, data = t.uint16_t.deserialize(data)
        else:
            # Notifying that I will report things to you
            self.datatype, data = t.uint8_t.deserialize(data)
            self.min_interval, data = t.uint16_t.deserialize(data)
            self.max_interval, data = t.uint16_t.deserialize(data)
            datatype = DATA_TYPES[self.datatype]
            if datatype[2] is Analog:
                self.reportable_change, data = datatype[1].deserialize(data)

        return self, data

    def __repr__(self):
        r = f"{self.__class__.__name__}("
        r += f"direction={self.direction}"
        r += f", attrid=0x{self.attrid:04X}"

        if self.direction == ReportingDirection.ReceiveReports:
            r += f", timeout={self.timeout}"
        else:
            r += f", datatype={self.datatype}"
            r += f", min_interval={self.min_interval}"
            r += f", max_interval={self.max_interval}"

            if self.reportable_change is not None:
                r += f", reportable_change={self.reportable_change}"

        r += ")"

        return r


class ConfigureReportingResponseRecord(t.Struct):
    status: Status
    direction: ReportingDirection
    attrid: t.uint16_t = t.StructField(repr=_hex_uint16_repr)

    @classmethod
    def deserialize(cls, data):
        r = cls()
        r.status, data = Status.deserialize(data)
        if r.status == Status.SUCCESS:
            r.direction, data = t.Optional(t.uint8_t).deserialize(data)
            if r.direction is not None:
                r.direction = ReportingDirection(r.direction)
            r.attrid, data = t.Optional(t.uint16_t).deserialize(data)
            return r, data

        r.direction, data = ReportingDirection.deserialize(data)
        r.attrid, data = t.uint16_t.deserialize(data)
        return r, data

    def serialize(self):
        r = Status(self.status).serialize()
        if self.status != Status.SUCCESS:
            r += ReportingDirection(self.direction).serialize()
            r += t.uint16_t(self.attrid).serialize()
        return r

    def __repr__(self):
        r = f"{self.__class__.__name__}(status={self.status}"
        if self.status != Status.SUCCESS:
            r += f", direction={self.direction}, attrid={self.attrid}"
        r += ")"
        return r


class ConfigureReportingResponse(t.List[ConfigureReportingResponseRecord]):
    # In the case of successful configuration of all attributes, only a single
    # attribute status record SHALL be included in the command, with the status
    # field set to SUCCESS and the direction and attribute identifier fields omitted

    def serialize(self):
        if not self:
            raise ValueError("Cannot serialize empty list")

        failed = [record for record in self if record.status != Status.SUCCESS]

        if not failed:
            return ConfigureReportingResponseRecord(status=Status.SUCCESS).serialize()

        # Note that attribute status records are not included for successfully
        # configured attributes, in order to save bandwidth.
        return b"".join(
            [ConfigureReportingResponseRecord(r).serialize() for r in failed]
        )


class ReadReportingConfigRecord(t.Struct):
    direction: t.uint8_t
    attrid: t.uint16_t


class DiscoverAttributesResponseRecord(t.Struct):
    attrid: t.uint16_t
    datatype: t.uint8_t


class AttributeAccessControl(t.bitmap8):
    READ = 0x01
    WRITE = 0x02
    REPORT = 0x04


class DiscoverAttributesExtendedResponseRecord(t.Struct):
    attrid: t.uint16_t
    datatype: t.uint8_t
    acl: AttributeAccessControl


class Read_Attributes(
    ZCLCommand,
    id=0x00,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    attribute_ids: t.List[t.uint16_t]


class Read_Attributes_rsp(
    ZCLCommand,
    id=0x01,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    status_records: t.List[foundation.ReadAttributeRecord]


class Write_Attributes(
    ZCLCommand,
    id=0x02,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    attributes: t.List[foundation.Attribute]


class Write_Attributes_Undivided(
    ZCLCommand,
    id=0x03,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    attributes: t.List[foundation.Attribute]


class Write_Attributes_rsp(
    ZCLCommand,
    id=0x04,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    status_records: foundation.WriteAttributesResponse


class Write_Attributes_No_Response(
    ZCLCommand,
    id=0x05,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    attributes: t.List[foundation.Attribute]


class Configure_Reporting(
    ZCLCommand,
    id=0x06,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    config_records: t.List[foundation.AttributeReportingConfig]


class Configure_Reporting_rsp(
    ZCLCommand,
    id=0x07,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    status_records: foundation.ConfigureReportingResponse


class Read_Reporting_Configuration(
    ZCLCommand,
    id=0x08,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    attribute_records: t.List[foundation.ReadReportingConfigRecord]


class Read_Reporting_Configuration_rsp(
    ZCLCommand,
    id=0x09,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    attribute_configs: t.List[foundation.AttributeReportingConfig]


class Report_Attributes(
    ZCLCommand,
    id=0x0A,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    attribute_reports: t.List[foundation.Attribute]


class Default_Response(
    ZCLCommand,
    id=0x0B,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    command_id: t.uint8_t
    status: foundation.Status


class Discover_Attributes(
    ZCLCommand,
    id=0x0C,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    start_attribute_id: t.uint16_t
    max_attribute_ids: t.uint8_t


class Discover_Attributes_rsp(
    ZCLCommand,
    id=0x0D,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    discovery_complete: t.Bool
    attribute_info: t.List[foundation.DiscoverAttributesResponseRecord]


class Discover_Commands_Received(
    ZCLCommand,
    id=0x11,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    start_command_id: t.uint8_t
    max_command_ids: t.uint8_t


class Discover_Commands_Received_rsp(
    ZCLCommand,
    id=0x12,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    discovery_complete: t.Bool
    command_ids: t.List[t.uint8_t]


class Discover_Commands_Generated(
    ZCLCommand,
    id=0x13,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    start_command_id: t.uint8_t
    max_command_ids: t.uint8_t


class Discover_Commands_Generated_rsp(
    ZCLCommand,
    id=0x14,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    discovery_complete: t.Bool
    command_ids: t.List[t.uint8_t]


class Discover_Attribute_Extended(
    ZCLCommand,
    id=0x15,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.CLIENT_TO_SERVER,
):
    start_attribute_id: t.uint16_t
    max_attribute_ids: t.uint8_t


class Discover_Attribute_Extended_rsp(
    ZCLCommand,
    id=0x16,
    frame_type=FrameType.GLOBAL_COMMAND,
    direction=Direction.SERVER_TO_CLIENT,
):
    discovery_complete: t.Bool
    extended_attr_info: t.List[foundation.DiscoverAttributesExtendedResponseRecord]


GLOBAL_COMMANDS = {}
obj = None

for obj in globals():
    if inspect.isclass(obj) and issubclass(obj, ZCLCommand):
        assert obj.frame_type == FrameType.GLOBAL_COMMAND
        GLOBAL_COMMANDS[obj.command_id] = True
