"""Protocol Interfaces Functional Domain"""

from __future__ import annotations

import zigpy.types as t
from zigpy.zcl import Cluster
from zigpy.zcl.foundation import ZCLAttributeDef, ZCLCommandDef


class DateTime(t.Struct):
    date: t.uint32_t
    time: t.uint32_t


class GenericTunnel(Cluster):
    cluster_id = 0x0600
    ep_attribute = "generic_tunnel"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0001: ("max_income_trans_size", t.uint16_t),
        0x0002: ("max_outgo_trans_size", t.uint16_t),
        0x0003: ("protocol_addr", t.LVBytes),
    }
    server_commands: dict[int, ZCLCommandDef] = {
        0x00: ZCLCommandDef("match_protocol_addr", {}, False)
    }
    client_commands: dict[int, ZCLCommandDef] = {
        0x00: ZCLCommandDef("match_protocol_addr_response", {}, True),
        0x01: ZCLCommandDef("advertise_protocol_address", {}, False),
    }


class BacnetProtocolTunnel(Cluster):
    cluster_id = 0x0601
    ep_attribute = "bacnet_tunnel"
    attributes: dict[int, ZCLAttributeDef] = {}
    server_commands: dict[int, ZCLCommandDef] = {
        0x00: ZCLCommandDef("transfer_npdu", {"npdu": t.LVBytes}, False)
    }
    client_commands: dict[int, ZCLCommandDef] = {}


class AnalogInputRegular(Cluster):
    cluster_id = 0x0602
    ep_attribute = "bacnet_regular_analog_input"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0016: ("cov_increment", t.Single),
        0x001F: ("device_type", t.CharacterString),
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x0076: ("update_interval", t.uint8_t),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class AnalogInputExtended(Cluster):
    cluster_id = 0x0603
    ep_attribute = "bacnet_extended_analog_input"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0011: ("notification_class", t.uint16_t),
        0x0019: ("deadband", t.Single),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x002D: ("high_limit", t.Single),
        0x0034: ("limit_enable", t.bitmap8),
        0x003B: ("low_limit", t.Single),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array) # Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {
        0x00: ZCLCommandDef("transfer_apdu", {}, False),
        0x01: ZCLCommandDef("connect_req", {}, False),
        0x02: ZCLCommandDef("disconnect_req", {}, False),
        0x03: ZCLCommandDef("connect_status_noti", {}, False),
    }
    client_commands: dict[int, ZCLCommandDef] = {}


class AnalogOutputRegular(Cluster):
    cluster_id = 0x0604
    ep_attribute = "bacnet_regular_analog_output"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0016: ("cov_increment", t.Single),
        0x001F: ("device_type", t.CharacterString),
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x0076: ("update_interval", t.uint8_t),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class AnalogOutputExtended(Cluster):
    cluster_id = 0x0605
    ep_attribute = "bacnet_extended_analog_output"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0011: ("notification_class", t.uint16_t),
        0x0019: ("deadband", t.Single),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x002D: ("high_limit", t.Single),
        0x0034: ("limit_enable", t.bitmap8),
        0x003B: ("low_limit", t.Single),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array)# Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class AnalogValueRegular(Cluster):
    cluster_id = 0x0606
    ep_attribute = "bacnet_regular_analog_value"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0016: ("cov_increment", t.Single),
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class AnalogValueExtended(Cluster):
    cluster_id = 0x0607
    ep_attribute = "bacnet_extended_analog_value"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0011: ("notification_class", t.uint16_t),
        0x0019: ("deadband", t.Single),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x002D: ("high_limit", t.Single),
        0x0034: ("limit_enable", t.bitmap8),
        0x003B: ("low_limit", t.Single),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array),  # Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class BinaryInputRegular(Cluster):
    cluster_id = 0x0608
    ep_attribute = "bacnet_regular_binary_input"
    attributes: dict[int, ZCLAttributeDef] = {
        0x000F: ("change_of_state_count", t.uint32_t),
        0x0010: ("change_of_state_time", DateTime),
        0x001F: ("device_type", t.CharacterString),
        0x0021: ("elapsed_active_time", t.uint32_t),
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x0072: ("time_of_at_reset", DateTime),
        0x0073: ("time_of_sc_reset", DateTime),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class BinaryInputExtended(Cluster):
    cluster_id = 0x0609
    ep_attribute = "bacnet_extended_binary_input"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0006: ("alarm_value", t.Bool),
        0x0011: ("notification_class", t.uint16_t),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array),  # Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class BinaryOutputRegular(Cluster):
    cluster_id = 0x060A
    ep_attribute = "bacnet_regular_binary_output"
    attributes: dict[int, ZCLAttributeDef] = {
        0x000F: ("change_of_state_count", t.uint32_t),
        0x0010: ("change_of_state_time", DateTime),
        0x001F: ("device_type", t.CharacterString),
        0x0021: ("elapsed_active_time", t.uint32_t),
        0x0028: ("feed_back_value", t.enum8),
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x0072: ("time_of_at_reset", DateTime),
        0x0073: ("time_of_sc_reset", DateTime),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class BinaryOutputExtended(Cluster):
    cluster_id = 0x060B
    ep_attribute = "bacnet_extended_binary_output"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0011: ("notification_class", t.uint16_t),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array),  # Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class BinaryValueRegular(Cluster):
    cluster_id = 0x060C
    ep_attribute = "bacnet_regular_binary_value"
    attributes: dict[int, ZCLAttributeDef] = {
        0x000F: ("change_of_state_count", t.uint32_t),
        0x0010: ("change_of_state_time", DateTime),
        0x0021: ("elapsed_active_time", t.uint32_t),
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x0072: ("time_of_at_reset", DateTime),
        0x0073: ("time_of_sc_reset", DateTime),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class BinaryValueExtended(Cluster):
    cluster_id = 0x060D
    ep_attribute = "bacnet_extended_binary_value"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0006: ("alarm_value", t.Bool),
        0x0011: ("notification_class", t.uint16_t),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array),  # Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class MultistateInputRegular(Cluster):
    cluster_id = 0x060E
    ep_attribute = "bacnet_regular_multistate_input"
    attributes: dict[int, ZCLAttributeDef] = {
        0x001F: ("device_type", t.CharacterString),
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class MultistateInputExtended(Cluster):
    cluster_id = 0x060F
    ep_attribute = "bacnet_extended_multistate_input"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0006: ("alarm_value", t.uint16_t),
        0x0011: ("notification_class", t.uint16_t),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x0025: ("fault_values", t.uint16_t),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array),  # Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class MultistateOutputRegular(Cluster):
    cluster_id = 0x0610
    ep_attribute = "bacnet_regular_multistate_output"
    attributes: dict[int, ZCLAttributeDef] = {
        0x001F: ("device_type", t.CharacterString),
        0x0028: ("feed_back_value", t.enum8),
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class MultistateOutputExtended(Cluster):
    cluster_id = 0x0611
    ep_attribute = "bacnet_extended_multistate_output"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0011: ("notification_class", t.uint16_t),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array),  # Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class MultistateValueRegular(Cluster):
    cluster_id = 0x0612
    ep_attribute = "bacnet_regular_multistate_value"
    attributes: dict[int, ZCLAttributeDef] = {
        0x004B: ("object_id", t.FixedList[4, t.uint8_t]),
        0x004D: ("object_name", t.CharacterString),
        0x004F: ("object_type", t.enum16),
        0x00A8: ("profile_name", t.CharacterString),
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}


class MultistateValueExtended(Cluster):
    cluster_id = 0x0613
    ep_attribute = "bacnet_extended_multistate_value"
    attributes: dict[int, ZCLAttributeDef] = {
        0x0000: ("acked_transitions", t.bitmap8),
        0x0006: ("alarm_value", t.uint16_t),
        0x0011: ("notification_class", t.uint16_t),
        0x0023: ("event_enable", t.bitmap8),
        0x0024: ("event_state", t.enum8),
        0x0025: ("fault_values", t.uint16_t),
        0x0048: ("notify_type", t.enum8),
        0x0071: ("time_delay", t.uint8_t),
        # 0x0082: ('event_time_stamps', TODO.array),  # Array[3] of (16-bit unsigned
        # integer, time of day, or structure of (date, time of day))
    }
    server_commands: dict[int, ZCLCommandDef] = {}
    client_commands: dict[int, ZCLCommandDef] = {}
