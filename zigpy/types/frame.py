from __future__ import annotations

import dataclasses

import zigpy.types as t


@dataclasses.dataclass
class ZDOFrame:
    tsn: t.uint8_t
    command_id: t.uin16_t
    payload: zdo_t.ZDOCommand | bytes

    @classmethod
    def deserialize(cls, data: bytes) -> ZDOFrame:
        if len(data) < 3:
            raise ValueError(f"Data is too short for a ZDO frame: {data!r}")

        tsn, data = t.uint8_t.deserialize(data)
        command_id, data = t.uint16_t.deserialize(data)

        try:
            command = ZDO_COMMANDS[command_id]
        except KeyError:
            LOGGER.warning("Unknown ZDO command: %r", command_id)
            return cls(tsn=tsn, command_id=command_id, payload=t.Bytes(data))

        try:
            payload, rest = command.deserialize(data[1:])
        except ValueError:
            LOGGER.warning("Failed to deserialize %r: %r", command, data, exc_info=True)
            return cls(tsn=tsn, command_id=command_id, payload=t.Bytes(data))

        if rest:
            LOGGER.warning("Unhandled trailing data at end of ZDO frame: %r", rest)

        return cls(tsn=tsn, command_id=command_id, payload=payload)

    def serialize(self) -> bytes:
        return self.tsn.serialize() + self.payload.serialize()


class FrameType(t.enum2):
    """ZCL Frame Type."""

    GLOBAL_COMMAND = 0b00
    CLUSTER_COMMAND = 0b01
    RESERVED_2 = 0b10
    RESERVED_3 = 0b11


class Direction(t.enum1):
    CLIENT_TO_SERVER = 0b0
    SERVER_TO_CLIENT = 0b1


class FrameControl(t.Struct, t.uint8_t):
    """
    The frame control field contains information defining the command type and other
    control flags.
    """

    frame_type: FrameType
    is_manufacturer_specific: t.uint1_t
    direction: Direction
    disable_default_response: t.uint1_t
    reserved: t.uint3_t


class ZCLFrame(t.Struct):
    frame_control: FrameControl
    manufacturer_code: t.uint16_t = t.StructField(
        requires=lambda hdr: hdr.frame_control.is_manufacturer_specific
    )
    tsn: t.uint8_t
    command_id: t.uint8_t
    payload: t.Bytes

    def __new__(
        cls,
        frame_control=None,
        manufacturer_code=None,
        tsn=None,
        command_id=None,
        payload=None,
    ) -> ZCLHeader:
        if frame_control is not None and manufacturer_code is not None:
            frame_control.is_manufacturer_specific = True

        return super().__new__(
            cls, frame_control, manufacturer_code, tsn, command_id, payload
        )

    def __setattr__(self, name, value) -> None:
        super().__setattr__(name, value)

        # Flip the bit when the attribute is changed
        if name == "manufacturer_code" and self.frame_control is not None:
            self.frame_control.is_manufacturer_specific = value is not None

    @classmethod
    def deserialize(cls, data: bytes, *, overrides=None) -> tuple[ZCLFrame, bytes]:
        frame, rest = super().deserialize(data)

        if frame.command_id in overrides:
            command = overrides[frame.command_id]
        elif frame.command_id in ZCL_COMMANDS:
            command = ZCL_COMMANDS[frame.command_id]
        else:
            LOGGER.warning("Unknown ZCL command %04X", frame.command_id)
            return frame, rest

        try:
            payload, payload_rest = command.deserialize(frame.payload)
        except ValueError:
            LOGGER.warning("Failed to deserialize %r as %s", frame.payload, command)
            return frame, rest

        if payload_rest:
            LOGGER.warning("Trailing data remains after ZCL command: %r", payload_rest)

        return frame.replace(payload=payload), rest


@dataclasses.dataclass
class NWKFrame:
    """
    Combined NWK + APS frame that contains everything required for a radio library to
    send a packet or to inform zigpy of a received packet.
    """

    src: t.AddrModeAddress
    src_ep: t.uint8_t

    dest: t.AddrModeAddress
    dest_ep: t.uint8_t

    cluster_id: t.uint16_t
    profile: t.uint16_t

    seq: t.uint8_t
    ack: bool

    # Only used for broadcast/multicast
    radius: t.uint8_t | None

    # ZDO if the endpoints are 0, ZCL otherwise
    payload: ZDOFrame | ZCLFrame | bytes
