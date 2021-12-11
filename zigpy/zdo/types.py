from __future__ import annotations

import typing

import zigpy.types as t


class _PowerDescriptorEnums:
    class CurrentPowerMode(t.enum4):
        RxOnSyncedWithNodeDesc = 0b0000
        RxOnPeriodically = 0b0001
        RxOnWhenStimulated = 0b0010

    class PowerSources(t.bitmap4):
        MainsPower = 0b0001
        RechargeableBattery = 0b0010
        DisposableBattery = 0b0100
        Reserved = 0b1000

    class PowerSourceLevel(t.enum4):
        Critical = 0b0000
        Percent33 = 0b0100
        Percent66 = 0b1000
        Percent100 = 0b1100


class PowerDescriptor(t.Struct):
    CurrentPowerMode = _PowerDescriptorEnums.CurrentPowerMode
    PowerSources = _PowerDescriptorEnums.PowerSources
    PowerSourceLevel = _PowerDescriptorEnums.PowerSourceLevel

    current_power_mode: _PowerDescriptorEnums.CurrentPowerMode
    available_power_sources: _PowerDescriptorEnums.PowerSources
    current_power_source: _PowerDescriptorEnums.PowerSources
    current_power_source_level: _PowerDescriptorEnums.PowerSourceLevel


class SimpleDescriptor(t.Struct):
    endpoint: t.uint8_t
    profile: t.uint16_t
    device_type: t.uint16_t
    device_version: t.uint8_t
    input_clusters: t.LVList[t.uint16_t]
    output_clusters: t.LVList[t.uint16_t]


class SizePrefixedSimpleDescriptor(SimpleDescriptor):
    def serialize(self):
        data = super().serialize()
        return len(data).to_bytes(1, "little") + data

    @classmethod
    def deserialize(cls, data):
        if not data or data[0] == 0:
            return None, data[1:]
        return super().deserialize(data[1:])


class LogicalType(t.enum3):
    Coordinator = 0b000
    Router = 0b001
    EndDevice = 0b010


class _NodeDescriptorEnums:
    class MACCapabilityFlags(t.bitmap8):
        NONE = 0

        AlternatePanCoordinator = 0b00000001
        FullFunctionDevice = 0b00000010
        MainsPowered = 0b00000100
        RxOnWhenIdle = 0b00001000
        SecurityCapable = 0b01000000
        AllocateAddress = 0b10000000

    class FrequencyBand(t.bitmap5):
        Freq868MHz = 0b00001
        Freq902MHz = 0b00100
        Freq2400MHz = 0b01000

    class DescriptorCapability(t.bitmap8):
        NONE = 0

        ExtendedActiveEndpointListAvailable = 0b00000001
        ExtendedSimpleDescriptorListAvailable = 0b00000010


class NodeDescriptor(t.Struct):
    FrequencyBand = _NodeDescriptorEnums.FrequencyBand
    MACCapabilityFlags = _NodeDescriptorEnums.MACCapabilityFlags
    DescriptorCapability = _NodeDescriptorEnums.DescriptorCapability

    logical_type: LogicalType
    complex_descriptor_available: t.uint1_t
    user_descriptor_available: t.uint1_t
    reserved: t.uint3_t

    aps_flags: t.uint3_t
    frequency_band: _NodeDescriptorEnums.FrequencyBand

    mac_capability_flags: _NodeDescriptorEnums.MACCapabilityFlags
    manufacturer_code: t.uint16_t
    maximum_buffer_size: t.uint8_t
    maximum_incoming_transfer_size: t.uint16_t
    server_mask: t.uint16_t
    maximum_outgoing_transfer_size: t.uint16_t
    descriptor_capability_field: _NodeDescriptorEnums.DescriptorCapability

    def __new__(cls, *args, **kwargs):
        # Old style constructor
        if len(args) == 9 or "byte1" in kwargs or "byte2" in kwargs:
            return cls._old_constructor(*args, **kwargs)

        return super().__new__(cls, *args, **kwargs)

    @classmethod
    def _old_constructor(
        cls: "NodeDescriptor",
        byte1: t.uint8_t = None,
        byte2: t.uint8_t = None,
        mac_capability_flags: MACCapabilityFlags = None,
        manufacturer_code: t.uint16_t = None,
        maximum_buffer_size: t.uint8_t = None,
        maximum_incoming_transfer_size: t.uint16_t = None,
        server_mask: t.uint16_t = None,
        maximum_outgoing_transfer_size: t.uint16_t = None,
        descriptor_capability_field: t.uint8_t = None,
    ) -> NodeDescriptor:
        logical_type = None
        complex_descriptor_available = None
        user_descriptor_available = None
        reserved = None

        if byte1 is not None:
            bits, _ = t.Bits.deserialize(bytes([byte1]))
            logical_type, bits = LogicalType.from_bits(bits)
            complex_descriptor_available, bits = t.uint1_t.from_bits(bits)
            user_descriptor_available, bits = t.uint1_t.from_bits(bits)
            reserved, bits = t.uint3_t.from_bits(bits)

            assert not bits

        aps_flags = None
        frequency_band = None

        if byte2 is not None:
            bits, _ = t.Bits.deserialize(bytes([byte2]))
            aps_flags, bits = t.uint3_t.from_bits(bits)
            frequency_band, bits = cls.FrequencyBand.from_bits(bits)

            assert not bits

        return cls(
            logical_type=logical_type,
            complex_descriptor_available=complex_descriptor_available,
            user_descriptor_available=user_descriptor_available,
            reserved=reserved,
            aps_flags=aps_flags,
            frequency_band=frequency_band,
            mac_capability_flags=mac_capability_flags,
            manufacturer_code=manufacturer_code,
            maximum_buffer_size=maximum_buffer_size,
            maximum_incoming_transfer_size=maximum_incoming_transfer_size,
            server_mask=server_mask,
            maximum_outgoing_transfer_size=maximum_outgoing_transfer_size,
            descriptor_capability_field=descriptor_capability_field,
        )

    @property
    def is_end_device(self) -> bool | None:
        if self.logical_type is None:
            return None

        return self.logical_type == LogicalType.EndDevice

    @property
    def is_router(self) -> bool | None:
        if self.logical_type is None:
            return None

        return self.logical_type == LogicalType.Router

    @property
    def is_coordinator(self) -> bool | None:
        if self.logical_type is None:
            return None

        return self.logical_type == LogicalType.Coordinator

    @property
    def is_alternate_pan_coordinator(self) -> bool | None:
        if self.mac_capability_flags is None:
            return None

        return bool(
            self.mac_capability_flags & self.MACCapabilityFlags.AlternatePanCoordinator
        )

    @property
    def is_full_function_device(self) -> bool | None:
        if self.mac_capability_flags is None:
            return None

        return bool(
            self.mac_capability_flags & self.MACCapabilityFlags.FullFunctionDevice
        )

    @property
    def is_mains_powered(self) -> bool | None:
        if self.mac_capability_flags is None:
            return None

        return bool(self.mac_capability_flags & self.MACCapabilityFlags.MainsPowered)

    @property
    def is_receiver_on_when_idle(self) -> bool | None:
        if self.mac_capability_flags is None:
            return None

        return bool(self.mac_capability_flags & self.MACCapabilityFlags.RxOnWhenIdle)

    @property
    def is_security_capable(self) -> bool | None:
        if self.mac_capability_flags is None:
            return None

        return bool(self.mac_capability_flags & self.MACCapabilityFlags.SecurityCapable)

    @property
    def allocate_address(self) -> bool | None:
        if self.mac_capability_flags is None:
            return None

        return bool(self.mac_capability_flags & self.MACCapabilityFlags.AllocateAddress)


class MultiAddress(t.Struct):
    """Used for binds, represents an IEEE+endpoint or NWK address"""

    addrmode: t.uint8_t
    nwk: t.uint16_t = t.StructField(requires=lambda s: s.addrmode == 0x01)
    ieee: t.EUI64 = t.StructField(requires=lambda s: s.addrmode == 0x03)
    endpoint: t.uint8_t = t.StructField(requires=lambda s: s.addrmode == 0x03)

    @classmethod
    def deserialize(cls, data):
        r, data = super().deserialize(data)

        if r.addrmode not in (0x01, 0x03):
            raise ValueError("Invalid MultiAddress - unknown address mode")

        return r, data

    def serialize(self):
        if self.addrmode not in (0x01, 0x03):
            raise ValueError("Invalid MultiAddress - unknown address mode")

        return super().serialize()


class _NeighborEnums:
    class DeviceType(t.enum2):
        Coordinator = 0x0
        Router = 0x1
        EndDevice = 0x2
        Unknown = 0x3

    class RxOnWhenIdle(t.enum2):
        Off = 0x0
        On = 0x1
        Unknown = 0x2

    class RelationShip(t.enum3):
        Parent = 0x0
        Child = 0x1
        Sibling = 0x2
        NoneOfTheAbove = 0x3
        PreviousChild = 0x4

    class PermitJoins(t.enum2):
        NotAccepting = 0x0
        Accepting = 0x1
        Unknown = 0x2


class Neighbor(t.Struct):
    """Neighbor Descriptor"""

    PermitJoins = _NeighborEnums.PermitJoins
    DeviceType = _NeighborEnums.DeviceType
    RxOnWhenIdle = _NeighborEnums.RxOnWhenIdle
    RelationShip = _NeighborEnums.RelationShip

    extended_pan_id: t.ExtendedPanId
    ieee: t.EUI64
    nwk: t.NWK

    device_type: _NeighborEnums.DeviceType
    rx_on_when_idle: _NeighborEnums.RxOnWhenIdle
    relationship: _NeighborEnums.RelationShip
    reserved1: t.uint1_t

    permit_joining: _NeighborEnums.PermitJoins
    reserved2: t.uint6_t

    depth: t.uint8_t
    lqi: t.uint8_t

    @classmethod
    def _parse_packed(cls, packed: t.uint8_t) -> dict[str, typing.Any]:
        data = 18 * b"\x00" + t.uint16_t(packed).serialize() + 3 * b"\x00"
        tmp_neighbor, _ = cls.deserialize(data)

        return {
            "device_type": tmp_neighbor.device_type,
            "rx_on_when_idle": tmp_neighbor.rx_on_when_idle,
            "relationship": tmp_neighbor.relationship,
            "reserved1": tmp_neighbor.reserved1,
        }


class Neighbors(t.Struct):
    """Mgmt_Lqi_rsp"""

    entries: t.uint8_t
    start_index: t.uint8_t
    neighbor_table_list: t.LVList[Neighbor]


class Route(t.Struct):
    """Route Descriptor"""

    DstNWK: t.NWK
    RouteStatus: t.uint8_t
    NextHop: t.NWK


class Routes(t.Struct):
    Entries: t.uint8_t
    StartIndex: t.uint8_t
    RoutingTableList: t.LVList[Route]


class NwkUpdate(t.Struct):
    CHANNEL_CHANGE_REQ = 0xFE
    CHANNEL_MASK_MANAGER_ADDR_CHANGE_REQ = 0xFF

    ScanChannels: t.Channels
    ScanDuration: t.uint8_t
    ScanCount: t.uint8_t = t.StructField(requires=lambda s: s.ScanDuration <= 0x05)
    nwkUpdateId: t.uint8_t = t.StructField(
        requires=lambda s: s.ScanDuration
        in (s.CHANNEL_CHANGE_REQ, s.CHANNEL_MASK_MANAGER_ADDR_CHANGE_REQ)
    )
    nwkManagerAddr: t.NWK = t.StructField(
        requires=lambda s: s.ScanDuration == s.CHANNEL_MASK_MANAGER_ADDR_CHANGE_REQ
    )


class Binding(t.Struct):
    SrcAddress: t.EUI64
    SrcEndpoint: t.uint8_t
    ClusterId: t.uint16_t
    DstAddress: MultiAddress


class Status(t.enum8):
    # The requested operation or transmission was completed successfully.
    SUCCESS = 0x00
    # The supplied request type was invalid.
    INV_REQUESTTYPE = 0x80
    # The requested device did not exist on a device following a child
    # descriptor request to a parent.
    DEVICE_NOT_FOUND = 0x81
    # The supplied endpoint was equal to = 0x00 or between 0xf1 and 0xff.
    INVALID_EP = 0x82
    # The requested endpoint is not described by a simple descriptor.
    NOT_ACTIVE = 0x83
    # The requested optional feature is not supported on the target device.
    NOT_SUPPORTED = 0x84
    # A timeout has occurred with the requested operation.
    TIMEOUT = 0x85
    # The end device bind request was unsuccessful due to a failure to match
    # any suitable clusters.
    NO_MATCH = 0x86
    # The unbind request was unsuccessful due to the coordinator or source
    # device not having an entry in its binding table to unbind.
    NO_ENTRY = 0x88
    # A child descriptor was not available following a discovery request to a
    # parent.
    NO_DESCRIPTOR = 0x89
    # The device does not have storage space to support the requested
    # operation.
    INSUFFICIENT_SPACE = 0x8A
    # The device is not in the proper state to support the requested operation.
    NOT_PERMITTED = 0x8B
    # The device does not have table space to support the operation.
    TABLE_FULL = 0x8C
    # The permissions configuration table on the target indicates that the
    # request is not authorized from this device.
    NOT_AUTHORIZED = 0x8D

    @classmethod
    def _missing_(cls, value):
        chained = t.APSStatus(value)
        status = cls._member_type_.__new__(cls, chained.value)
        status._name_ = chained.name
        status._value_ = value
        return status
