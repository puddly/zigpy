import zigpy.types as t
from zigpy.zcl import Cluster


class TLLogicalType(t.enum2):
    Coordinator = 0b00
    Router = 0b01
    EndDevice = 0b10


class TLZigbeeInformation(t.Struct):
    logical_type: TLLogicalType
    rx_on_when_idle: t.uint1_t
    reserved: t.uint5_t


class TLScanRequestInformation(t.Struct):
    # whether the device is factory new
    factory_new: t.uint1_t

    # whether the device is capable of assigning addresses
    address_assignment: t.uint1_t
    reserved1: t.uint2_t

    # indicate the device is capable of initiating a link (i.e., it supports the
    # touchlink commissioning cluster at the client side) or 0 otherwise (i.e., it does
    # not support the touchlink commissioning cluster at the client side).
    touchlink_initiator: t.uint1_t
    undefined: t.uint1_t
    reserved2: t.uint1_t

    # If the ZLL profile is implemented, this bit shall be set to 0. In all other case
    # (Profile Interop / ZigBee 3.0), this bit shall be set to 1
    profile_interop: t.uint1_t


class TLScanResponseInformation(t.Struct):
    factory_new: t.uint1_t
    address_assignment: t.uint1_t
    reserved1: t.uint2_t
    touchlink_initiator: t.uint1_t
    touchlink_priority_request: t.uint1_t
    reserved2: t.uint1_t
    profile_interop: t.uint1_t


class TLDeviceInfoRecord(t.Struct):
    ieee_addr: t.EUI64
    endpoint_id: t.uint8_t
    profile_id: t.uint8_t
    device_id: t.uint16_t
    version: t.uint8_t
    group_id_count: t.uint8_t
    sort: t.uint8_t


class TLStatus(t.enum8):
    Success = 0x00
    Failure = 0x01


class TLGroupInfoRecord(t.Struct):
    group_id: t.Group
    group_type: t.uint8_t


class TLEndpointInfoRecord(t.Struct):
    nwk_addr: t.NWK
    endpoint_id: t.uint8_t
    profile_id: t.uint16_t
    device_id: t.uint16_t
    version: t.uint8_t


class TouchlinkCommissioning(Cluster):
    cluster_id = 0x1000
    ep_attribute = "touchlink_commissioning"
    attributes = {}
    server_commands = {
        # Touchlink
        0x00: (
            "scan_request",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "zigbee_information": TLZigbeeInformation,
                "touchlink_information": TLScanRequestInformation,
            },
            False,
        ),
        0x02: (
            "device_info_request",
            {"inter_pan_transaction_id": t.uint32_t, "start_index": t.uint8_t},
            False,
        ),
        0x06: (
            "identify_request",
            {"inter_pan_transaction_id": t.uint32_t, "identify_duration": t.uint16_t},
            False,
        ),
        0x07: (
            "reset_to_factory_new_request",
            {"inter_pan_transaction_id": t.uint32_t},
            False,
        ),
        0x10: (
            "network_start_request",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "epid": t.EUI64,
                "key_index": t.uint8_t,
                "encrypted_network_key": t.KeyData,
                "logical_channel": t.uint8_t,
                "pan_id": t.PanId,
                "nwk_addr": t.NWK,
                "group_identifiers_begin": t.Group,
                "group_identifiers_end": t.Group,
                "free_network_addr_range_begin": t.NWK,
                "free_network_addr_range_end": t.NWK,
                "free_group_id_range_begin": t.Group,
                "free_group_id_range_end": t.Group,
                "initiator_ieee": t.EUI64,
                "initiator_nwk": t.NWK,
            },
            False,
        ),
        0x12: (
            "network_join_router_request",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "epid": t.EUI64,
                "key_index": t.uint8_t,
                "encrypted_network_key": t.KeyData,
                "nwk_update_id": t.uint8_t,
                "logical_channel": t.uint8_t,
                "pan_id": t.PanId,
                "nwk_addr": t.NWK,
                "group_identifiers_begin": t.Group,
                "group_identifiers_end": t.Group,
                "free_network_addr_range_begin": t.NWK,
                "free_network_addr_range_end": t.NWK,
                "free_group_id_range_begin": t.Group,
                "free_group_id_range_end": t.Group,
            },
            False,
        ),
        0x14: (
            "network_join_end_device_request",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "epid": t.EUI64,
                "key_index": t.uint8_t,
                "encrypted_network_key": t.KeyData,
                "nwk_update_id": t.uint8_t,
                "logical_channel": t.uint8_t,
                "pan_id": t.PanId,
                "nwk_addr": t.NWK,
                "group_identifiers_begin": t.Group,
                "group_identifiers_end": t.Group,
                "free_network_addr_range_begin": t.NWK,
                "free_network_addr_range_end": t.NWK,
                "free_group_id_range_begin": t.Group,
                "free_group_id_range_end": t.Group,
            },
            False,
        ),
        0x16: (
            "network_update_request",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "epid": t.EUI64,
                "nwk_update_id": t.uint8_t,
                "logical_channel": t.uint8_t,
                "pan_id": t.PanId,
                "nwk_addr": t.NWK,
            },
            False,
        ),
        # Utility
        0x41: (
            "get_group_identifiers_request",
            {
                "start_index": t.uint8_t,
            },
            False,
        ),
        0x42: (
            "get_endpoint_list_request",
            {
                "start_index": t.uint8_t,
            },
            False,
        ),
    }
    client_commands = {
        # Touchlink
        0x01: (
            "scan_response",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "rssi_correction": t.uint8_t,
                "zigbee_info": TLZigbeeInformation,
                "touchlink_info": TLScanResponseInformation,
                "key_bitmask": t.uint16_t,
                "response_id": t.uint32_t,
                "epid": t.EUI64,
                "nwk_update_id": t.uint8_t,
                "logical_channel": t.uint8_t,
                "pan_id": t.PanId,
                "nwk_addr": t.NWK,
                "num_sub_devices": t.uint8_t,
                "total_group_ids": t.uint8_t,
                "endpoint_id": t.Optional(t.uint8_t),
                "profile_id": t.Optional(t.uint16_t),
                "device_id": t.Optional(t.uint16_t),
                "version": t.Optional(t.uint8_t),
                "group_id_count": t.Optional(t.uint8_t),
            },
            True,
        ),
        0x03: (
            "device_info_response",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "num_sub_devices": t.uint8_t,
                "start_index": t.uint8_t,
                "device_info_records": t.LVList[TLDeviceInfoRecord],
            },
            True,
        ),
        0x11: (
            "network_start_response",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "status": TLStatus,
                "epid": t.EUI64,
                "nwk_update_id": t.uint8_t,
                "logical_channel": t.uint8_t,
                "pan_id": t.PanId,
            },
            True,
        ),
        0x13: (
            "network_join_router_response",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "status": TLStatus,
            },
            True,
        ),
        0x15: (
            "network_join_end_device_response",
            {
                "inter_pan_transaction_id": t.uint32_t,
                "status": TLStatus,
            },
            True,
        ),
        # Utility
        0x40: (
            "endpoint_info",
            {
                "ieee_addr": t.EUI64,
                "nwk_addr": t.NWK,
                "endpoint_id": t.uint8_t,
                "profile_id": t.uint16_t,
                "device_id": t.uint16_t,
                "version": t.uint8_t,
            },
            True,
        ),
        0x41: (
            "get_group_identifiers_response",
            {
                "total": t.uint8_t,
                "start_index": t.uint8_t,
                "group_info_records": t.LVList[TLGroupInfoRecord],
            },
            True,
        ),
        0x42: (
            "get_endpoint_list_response",
            {
                "total": t.uint8_t,
                "start_index": t.uint8_t,
                "endpoint_info_records": t.LVList[TLEndpointInfoRecord],
            },
            True,
        ),
    }
