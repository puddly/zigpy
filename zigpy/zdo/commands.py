from __future__ import annotations

import dataclasses
import inspect

import zigpy.types as t
import zigpy.zdo.types as zdo_t


class ZDOCommand(t.Struct):
    """
    Base class for all ZDO commands.
    """

    command_id: t.uint16_t = None

    def __init_subclass__(cls, *, command_id: t.uint16_t):
        super().__init_subclass__()

        cls.command_id = t.uint16_t(command_id)


class NWK_addr_req(ZDOCommand, command_id=0x0000):
    IEEEAddr: t.EUI64
    RequestType: t.uint8_t
    StartIndex: t.uint8_t


class IEEE_addr_req(ZDOCommand, command_id=0x0001):
    NWKAddrOfInterest: t.NWK
    RequestType: t.uint8_t
    StartIndex: t.uint8_t


class Node_Desc_req(ZDOCommand, command_id=0x0002):
    NWKAddrOfInterest: t.NWK


class Power_Desc_req(ZDOCommand, command_id=0x0003):
    NWKAddrOfInterest: t.NWK


class Simple_Desc_req(ZDOCommand, command_id=0x0004):
    NWKAddrOfInterest: t.NWK
    EndPoint: t.uint8_t


class Active_EP_req(ZDOCommand, command_id=0x0005):
    NWKAddrOfInterest: t.NWK


class Match_Desc_req(ZDOCommand, command_id=0x0006):
    NWKAddrOfInterest: t.NWK
    ProfileID: t.uint16_t
    InClusterList: t.LVList[t.uint16_t]
    OutClusterList: t.LVList[t.uint16_t]


class User_Desc_req(ZDOCommand, command_id=0x0011):
    NWKAddrOfInterest: t.NWK


class Discovery_Cache_req(ZDOCommand, command_id=0x0012):
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64


class Device_annce(ZDOCommand, command_id=0x0013):
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64
    Capability: t.uint8_t


class User_Desc_set(ZDOCommand, command_id=0x0014):
    NWKAddrOfInterest: t.NWK
    UserDescriptor: t.FixedList[16, t.uint8_t]  # Really a string


class System_Server_Discovery_req(ZDOCommand, command_id=0x0015):
    ServerMask: t.uint16_t


class Discovery_store_req(ZDOCommand, command_id=0x0016):
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64
    NodeDescSize: t.uint8_t
    PowerDescSize: t.uint8_t
    ActiveEPSize: t.uint8_t
    SimpleDescSizeList: t.LVList[t.uint8_t]


class Node_Desc_store_req(ZDOCommand, command_id=0x0017):
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64
    NodeDescriptor: zdo_t.NodeDescriptor


class Active_EP_store_req(ZDOCommand, command_id=0x0019):
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64
    ActiveEPList: t.LVList[t.uint8_t]


class Simple_Desc_store_req(ZDOCommand, command_id=0x001A):
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64
    SimpleDescriptor: zdo_t.SizePrefixedSimpleDescriptor


class Remove_node_cache_req(ZDOCommand, command_id=0x001B):
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64


class Find_node_cache_req(ZDOCommand, command_id=0x001C):
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64


class Extended_Simple_Desc_req(ZDOCommand, command_id=0x001D):
    NWKAddrOfInterest: t.NWK
    EndPoint: t.uint8_t
    StartIndex: t.uint8_t


class Extended_Active_EP_req(ZDOCommand, command_id=0x001E):
    NWKAddrOfInterest: t.NWK
    StartIndex: t.uint8_t


class Parent_annce(ZDOCommand, command_id=0x001F):
    Children: t.LVList[t.EUI64]
    #  Bind Management Server Services Responses


class End_Device_Bind_req(ZDOCommand, command_id=0x0020):
    BindingTarget: t.uint16_t
    SrcAddress: t.EUI64
    SrcEndpoint: t.uint8_t
    ProfileID: t.uint8_t
    InClusterList: t.LVList[t.uint8_t]
    OutClusterList: t.LVList[t.uint8_t]


class Bind_req(ZDOCommand, command_id=0x0021):
    SrcAddress: t.EUI64
    SrcEndpoint: t.uint8_t
    ClusterID: t.uint16_t
    DstAddress: zdo_t.MultiAddress


class Unbind_req(ZDOCommand, command_id=0x0022):
    SrcAddress: t.EUI64
    SrcEndpoint: t.uint8_t
    ClusterID: t.uint16_t
    DstAddress: zdo_t.MultiAddress


# Network Management Server Services Requests
# ... TODO optional stuff ...


class Mgmt_Lqi_req(ZDOCommand, command_id=0x0031):
    StartIndex: t.uint8_t


class Mgmt_Rtg_req(ZDOCommand, command_id=0x0032):
    StartIndex: t.uint8_t


class Mgmt_Bind_req(ZDOCommand, command_id=0x0033):
    StartIndex: t.uint8_t


# ... TODO optional stuff ...


class Mgmt_Leave_req(ZDOCommand, command_id=0x0034):
    DeviceAddress: t.EUI64
    Options: t.bitmap8


class Mgmt_Permit_Joining_req(ZDOCommand, command_id=0x0036):
    PermitDuration: t.uint8_t
    TC_Significant: t.Bool


class Mgmt_NWK_Update_req(ZDOCommand, command_id=0x0038):
    NwkUpdate: zdo_t.NwkUpdate


# ... TODO optional stuff ...
# Responses
# Device and Service Discovery Server Responses


class NWK_addr_rsp(ZDOCommand, command_id=0x8000):
    Status: zdo_t.Status
    IEEEAddr: t.EUI64
    NWKAddr: t.NWK
    NumAssocDev: t.uint8_t = t.StructField(optional=True)
    StartIndex: t.uint8_t = t.StructField(optional=True)
    NWKAddressAssocDevList: t.List[t.NWK] = t.StructField(optional=True)


class IEEE_addr_rsp(ZDOCommand, command_id=0x8001):
    Status: zdo_t.Status
    IEEEAddr: t.EUI64
    NWKAddr: t.NWK
    NumAssocDev: t.uint8_t = t.StructField(optional=True)
    StartIndex: t.uint8_t = t.StructField(optional=True)
    NWKAddrAssocDevList: t.List[t.NWK] = t.StructField(optional=True)


class Node_Desc_rsp(ZDOCommand, command_id=0x8002):
    Status: zdo_t.Status
    NWKAddrOfInterest: t.NWK
    NodeDescriptor: zdo_t.NodeDescriptor = t.StructField(optional=True)


class Power_Desc_rsp(ZDOCommand, command_id=0x8003):
    Status: zdo_t.Status
    NWKAddrOfInterest: t.NWK
    PowerDescriptor: zdo_t.PowerDescriptor = t.StructField(optional=True)


class Simple_Desc_rsp(ZDOCommand, command_id=0x8004):
    Status: zdo_t.Status
    NWKAddrOfInterest: t.NWK
    SimpleDescriptor: zdo_t.SizePrefixedSimpleDescriptor = t.StructField(optional=True)


class Active_EP_rsp(ZDOCommand, command_id=0x8005):
    Status: zdo_t.Status
    NWKAddrOfInterest: t.NWK
    ActiveEPList: t.LVList[t.uint8_t]


class Match_Desc_rsp(ZDOCommand, command_id=0x8006):
    Status: zdo_t.Status
    NWKAddrOfInterest: t.NWK
    MatchList: t.LVList[t.uint8_t]


class User_Desc_rsp(ZDOCommand, command_id=0x8011):
    Status: zdo_t.Status
    NWKAddrOfInterest: t.NWK
    Length: t.uint8_t
    UserDescriptor: t.FixedList[16, t.uint8_t] = t.StructField(optional=True)


class Discovery_Cache_rsp(ZDOCommand, command_id=0x8012):
    Status: zdo_t.Status


class User_Desc_conf(ZDOCommand, command_id=0x8014):
    Status: zdo_t.Status
    NWKAddrOfInterest: t.NWK


class System_Server_Discovery_rsp(ZDOCommand, command_id=0x8015):
    Status: zdo_t.Status
    ServerMask: t.uint16_t


class Discovery_Store_rsp(ZDOCommand, command_id=0x8016):
    Status: zdo_t.Status


class Node_Desc_store_rsp(ZDOCommand, command_id=0x8017):
    Status: zdo_t.Status


class Power_Desc_store_rsp(ZDOCommand, command_id=0x8018):
    Status: zdo_t.Status
    IEEEAddr: t.EUI64
    PowerDescriptor: zdo_t.PowerDescriptor


class Active_EP_store_rsp(ZDOCommand, command_id=0x8019):
    Status: zdo_t.Status


class Simple_Desc_store_rsp(ZDOCommand, command_id=0x801A):
    Status: zdo_t.Status


class Remove_node_cache_rsp(ZDOCommand, command_id=0x801B):
    Status: zdo_t.Status


class Find_node_cache_rsp(ZDOCommand, command_id=0x801C):
    CacheNWKAddr: t.EUI64
    NWKAddr: t.NWK
    IEEEAddr: t.EUI64


class Extended_Simple_Desc_rsp(ZDOCommand, command_id=0x801D):
    Status: zdo_t.Status
    NWKAddr: t.NWK
    Endpoint: t.uint8_t
    AppInputClusterCount: t.uint8_t
    AppOutputClusterCount: t.uint8_t
    StartIndex: t.uint8_t
    AppClusterList: t.List[t.uint16_t] = t.StructField(optional=True)


class Extended_Active_EP_rsp(ZDOCommand, command_id=0x801E):
    Status: zdo_t.Status
    NWKAddrOfInterest: t.NWK
    ActiveEPCount: t.uint8_t
    StartIndex: t.uint8_t
    ActiveEPList: t.List[t.uint8_t]


class Parent_annce_rsp(ZDOCommand, command_id=0x801F):
    Status: zdo_t.Status
    Children: t.LVList[t.EUI64]


#  Bind Management Server Services Responses


class End_Device_Bind_rsp(ZDOCommand, command_id=0x8020):
    Status: zdo_t.Status


class Bind_rsp(ZDOCommand, command_id=0x8021):
    Status: zdo_t.Status


class Unbind_rsp(ZDOCommand, command_id=0x8022):
    Status: zdo_t.Status
    # ... TODO optional stuff ...
    # Network Management Server Services Responses


class Mgmt_Lqi_rsp(ZDOCommand, command_id=0x8031):
    Status: zdo_t.Status
    Neighbors: zdo_t.Neighbors = t.StructField(optional=True)


class Mgmt_Rtg_rsp(ZDOCommand, command_id=0x8032):
    Status: zdo_t.Status
    Routes: zdo_t.Routes = t.StructField(optional=True)


class Mgmt_Bind_rsp(ZDOCommand, command_id=0x8033):
    Status: zdo_t.Status
    BindingTableEntries: t.uint8_t
    StartIndex: t.uint8_t
    BindingTableList: t.LVList[zdo_t.Binding]


# ... TODO optional stuff ...


class Mgmt_Leave_rsp(ZDOCommand, command_id=0x8034):
    Status: zdo_t.Status


class Mgmt_Permit_Joining_rsp(ZDOCommand, command_id=0x8036):
    Status: zdo_t.Status


class Mgmt_NWK_Update_rsp(ZDOCommand, command_id=0x8038):
    Status: zdo_t.Status
    ScannedChannels: t.Channels
    TotalTransmissions: t.uint16_t
    TransmissionFailures: t.uint16_t
    EnergyValues: t.LVList[t.uint8_t]


obj = None  # required for `obj` to not be created as a global during iteration
ZDO_COMMANDS = {}

for obj in globals():
    if inspect.isclass(obj) and issubclass(obj, ZDOCommand):
        ZDO_COMMANDS[obj.command_id] = obj

del obj
