"""Constants for the TP-Link switch SNMP integration."""

from __future__ import annotations

DOMAIN = "tplink_switch_snmp"

CONF_COMMUNITY = "community"
CONF_VERSION = "version"
CONF_USERNAME = "username"
CONF_AUTH_PROTOCOL = "auth_protocol"
CONF_AUTH_KEY = "auth_key"
CONF_PRIV_PROTOCOL = "priv_protocol"
CONF_PRIV_KEY = "priv_key"

VERSION_1 = "1"
VERSION_2C = "2c"
VERSION_3 = "3"
VERSIONS = (VERSION_1, VERSION_2C, VERSION_3)
DEFAULT_VERSION = VERSION_2C

NO_PROTOCOL = "none"
AUTH_PROTOCOLS = ("md5", "sha", "sha224", "sha256", "sha384", "sha512")
PRIV_PROTOCOLS = ("des", "aes128", "aes192", "aes256")
MIN_KEY_LENGTH = 8  # SNMPv3 passphrases must have at least eight characters

DEFAULT_PORT = 161
DEFAULT_COMMUNITY = "public"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ALLOW_WRITE = "allow_write"
CONF_WRITE_COMMUNITY = "write_community"
CONF_PROTECTED_PORTS = "protected_ports"
CONF_TRAP_PORT = "trap_port"  # 0 switches the trap receiver off
DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

# SNMP object identifiers (numeric, so no MIB files are needed).
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
OID_SYS_CONTACT = "1.3.6.1.2.1.1.4.0"
OID_SYS_LOCATION = "1.3.6.1.2.1.1.6.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
# TP-Link's own MIB (enterprise 11863): hardware and firmware version of a JetStream switch
OID_TPLINK_HARDWARE = "1.3.6.1.4.1.11863.1.1.3.1.1.1.5.0"
OID_TPLINK_FIRMWARE = "1.3.6.1.4.1.11863.1.1.3.1.1.1.6.0"
# TP-Link's private tables (read from the MIB package of the TL-SG3424, indexed by port number).
# The switch may not have all of them, so they are read apart from the standard ones.
OID_TPLINK = "1.3.6.1.4.1.11863.1.1.3"
OID_LOOP_ENABLED = f"{OID_TPLINK}.2.1.5.4.1.2"  # loopbackDetectionState
OID_LOOP_LOOPED = f"{OID_TPLINK}.2.1.5.4.1.5"  # loopbackDetectionLoopState
OID_LOOP_BLOCKED = f"{OID_TPLINK}.2.1.5.4.1.6"  # loopbackDetectionBlockState
OID_CFG_MODE = f"{OID_TPLINK}.2.1.1.1.1.4"  # l2PortConfigPortMode
OID_CFG_FLOW = f"{OID_TPLINK}.2.1.1.1.1.5"  # l2PortConfigPortFlowCtrl
OID_CFG_LAG = f"{OID_TPLINK}.2.1.1.1.1.6"  # l2PortConfigPortLAG
# l2PortConfigPortMode: how the port is set (6 is auto negotiation)
PORT_MODES = {1: "10half", 2: "10full", 3: "100half", 4: "100full", 5: "1000full", 6: "auto"}
OID_SEC_MAX = f"{OID_TPLINK}.2.1.3.1.1.2"  # l2PortSecurityMaxNum
OID_SEC_LEARNED = f"{OID_TPLINK}.2.1.3.1.1.3"  # l2PortSecurityLearnNum
OID_SEC_ON = f"{OID_TPLINK}.2.1.3.1.1.5"  # l2PortSecurityPortStatus
# stormControlBroadCastRate and the like: the limit in kbit/s (0 is "off")
STORM_LIMITS = {
    1: 128,
    2: 256,
    3: 512,
    4: 1000,
    5: 2000,
    6: 4000,
    7: 5000,
    8: 10000,
    9: 20000,
    10: 40000,
    11: 50000,
}
OID_STORM = f"{OID_TPLINK}.6.2.2.1.1"  # stormControlEntry: 2 broadcast, 3 multicast, 4 unicast
OID_ARP = f"{OID_TPLINK}.8.2.1"  # arpDetection: the switch's ARP protection
OID_SAVE_CONFIG = f"{OID_TPLINK}.11.1.0"  # save: 1 writes the running configuration to flash
OID_REBOOT = f"{OID_TPLINK}.1.3.1.0"  # systemToolReBoot: 1 restarts the switch
EXTRA_TABLES = {
    "loop_on": OID_LOOP_ENABLED,
    "loop": OID_LOOP_LOOPED,
    "loop_blocked": OID_LOOP_BLOCKED,
    "cfg_mode": OID_CFG_MODE,
    "cfg_flow": OID_CFG_FLOW,
    "cfg_lag": OID_CFG_LAG,
    "sec_on": OID_SEC_ON,
    "sec_max": OID_SEC_MAX,
    "sec_learned": OID_SEC_LEARNED,
    "storm_bc": f"{OID_STORM}.2",
    "storm_mc": f"{OID_STORM}.3",
    "storm_ul": f"{OID_STORM}.4",
    "arp_on": f"{OID_ARP}.1.1",  # arpDetectionConfigEnable
    "arp_state": f"{OID_ARP}.2.2.1.2",  # arpDetectionStatState: 1 trusted port, 0 not
    "arp_illegal": f"{OID_ARP}.2.2.1.3",  # arpDetectionStatNonLegalPkt
}
# Traps of the TL-SG3424 that are reported as an alarm event (snmpTrapOID -> what it says)
TRAP_ALARMS = {
    "1.3.6.1.4.1.11863.1.1.3.14.12.1": "cpu_load",  # cpuLoadExceed: over 80 %
    "1.3.6.1.4.1.11863.1.1.3.14.12.2": "memory_load",  # memoryLoadExceed: over 80 %
    "1.3.6.1.4.1.11863.1.1.3.2.1.5.5": "loop",  # loopbackStatusChange
    "1.3.6.1.4.1.11863.1.1.3.6.4.1": "broadcast_storm",  # broadcastRateExceed
    "1.3.6.1.4.1.11863.1.1.3.6.4.2": "multicast_storm",  # multicastRateExceed
}
# RMON etherStatsTable (standard): the errors of a port told apart. The row index is not always
# the port, so etherStatsDataSource (an ifIndex as an OID) says which interface a row is for.
OID_RMON_STATS = "1.3.6.1.2.1.16.1.1.1"
RMON_TABLES = {
    "rmon_source": f"{OID_RMON_STATS}.2",
    "rmon_crc": f"{OID_RMON_STATS}.8",
    "rmon_under": f"{OID_RMON_STATS}.9",
    "rmon_over": f"{OID_RMON_STATS}.10",
    "rmon_frag": f"{OID_RMON_STATS}.11",
    "rmon_jabber": f"{OID_RMON_STATS}.12",
    "rmon_coll": f"{OID_RMON_STATS}.13",
}
# the kinds of error and the column that holds each; the names are the keys of the sensors
ERROR_DETAILS = {
    "crc_errors": "rmon_crc",
    "undersize_packets": "rmon_under",
    "oversize_packets": "rmon_over",
    "fragments": "rmon_frag",
    "jabbers": "rmon_jabber",
    "collisions": "rmon_coll",
}
# Spanning tree (standard BRIDGE-MIB, dot1dStp): topology changes, the root port, the port states
OID_STP = "1.3.6.1.2.1.17.2"
STP_TABLES = {
    "stp_changes": f"{OID_STP}.4",  # dot1dStpTopChanges
    "stp_root_port": f"{OID_STP}.7",  # dot1dStpRootPort
    "stp_state": f"{OID_STP}.15.1.3",  # dot1dStpPortState
}
STP_STATES = {
    1: "disabled",
    2: "blocking",
    3: "listening",
    4: "learning",
    5: "forwarding",
    6: "broken",
}
# VLANs (standard Q-BRIDGE-MIB): the names, who is a member and who sends untagged, the PVID
OID_VLAN = "1.3.6.1.2.1.17.7.1.4"
VLAN_TABLES = {
    "vlan_name": f"{OID_VLAN}.3.1.1",  # dot1qVlanStaticName, by VLAN ID
    "vlan_egress": f"{OID_VLAN}.3.1.2",  # dot1qVlanStaticEgressPorts: a bit per bridge port
    "vlan_untagged": f"{OID_VLAN}.3.1.4",  # dot1qVlanStaticUntaggedPorts
    "vlan_pvid": f"{OID_VLAN}.5.1.1",  # dot1qPvid, by bridge port
}
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
OID_BRIDGE_ADDRESS = "1.3.6.1.2.1.17.1.1.0"

OID_IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_IF_LAST_CHANGE = "1.3.6.1.2.1.2.2.1.9"
# Packet counters: 64 bit for SNMP v2c and v3, 32 bit for v1
OID_IF_HC_PACKETS = {
    "rx_uc": "1.3.6.1.2.1.31.1.1.1.7",
    "rx_mc": "1.3.6.1.2.1.31.1.1.1.8",
    "rx_bc": "1.3.6.1.2.1.31.1.1.1.9",
    "tx_uc": "1.3.6.1.2.1.31.1.1.1.11",
    "tx_mc": "1.3.6.1.2.1.31.1.1.1.12",
    "tx_bc": "1.3.6.1.2.1.31.1.1.1.13",
}
OID_IF_PACKETS = {
    "rx_uc": "1.3.6.1.2.1.2.2.1.11",
    "rx_mc": "1.3.6.1.2.1.31.1.1.1.2",
    "rx_bc": "1.3.6.1.2.1.31.1.1.1.3",
    "tx_uc": "1.3.6.1.2.1.2.2.1.17",
    "tx_mc": "1.3.6.1.2.1.31.1.1.1.4",
    "tx_bc": "1.3.6.1.2.1.31.1.1.1.5",
}
OID_IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"
OID_IF_ALIAS = "1.3.6.1.2.1.31.1.1.1.18"
ADMIN_UP = 1
ADMIN_DOWN = 2
# A port that has learned this many MAC addresses is an uplink to more of the network: it is
# not switched off from Home Assistant, whoever asks.
PROTECTED_MAC_COUNT = 10
OID_IF_IN_DISCARDS = "1.3.6.1.2.1.2.2.1.13"
OID_IF_OUT_DISCARDS = "1.3.6.1.2.1.2.2.1.19"
OID_IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"
OID_IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"
OID_IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"  # 32 bit, the only ones SNMPv1 has
OID_IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"
OID_IF_HC_IN_OCTETS = "1.3.6.1.2.1.31.1.1.1.6"
OID_IF_HC_OUT_OCTETS = "1.3.6.1.2.1.31.1.1.1.10"
OID_IF_HIGH_SPEED = "1.3.6.1.2.1.31.1.1.1.15"

# Forwarding database: Q-BRIDGE (per VLAN) first, classic BRIDGE as fallback.
OID_FDB_Q = "1.3.6.1.2.1.17.7.1.2.2.1.2"
OID_FDB = "1.3.6.1.2.1.17.4.3.1.2"
OID_BASE_PORT_IF_INDEX = "1.3.6.1.2.1.17.1.4.1.2"

CONF_PORT_NAMES = "port_names"
PORT_NAME_MAX = 40

PANEL_PATH = "tplink-switch"

EVENT_LINK_CHANGED = f"{DOMAIN}_link_changed"
EVENT_DEVICE_MOVED = f"{DOMAIN}_device_moved"
EVENT_ALARM = f"{DOMAIN}_alarm"

# Which entities are created: groups of them can be left out, and so can ports (options).
CONF_ENTITY_GROUPS = "entity_groups"
CONF_ENTITY_PORTS = "entity_ports"  # empty: all ports
# group -> the keys of the per-port entities in it (the last part of their unique IDs)
PORT_ENTITY_GROUPS: dict[str, tuple[str, ...]] = {
    "link": ("link",),
    "rates": ("rx_rate", "tx_rate"),
    "speed": ("speed",),
    "totals": ("rx_total", "tx_total"),
    "errors": ("rx_errors", "tx_errors", "rx_discards", "tx_discards"),
    "packets": ("rx_packets", "tx_packets", "rx_broadcast", "rx_multicast"),
    "utilization": ("rx_utilization", "tx_utilization"),
    "link_changed": ("link_changed",),
    "macs": ("macs",),
    "loop": ("loop",),
    "error_details": tuple(ERROR_DETAILS),
    "arp": ("arp_illegal",),
    "vlan": ("pvid",),
}
# groups of entities that belong to the switch and not to a port
SWITCH_ENTITY_GROUPS = ("uptime", "devices", "stp")
ENTITY_GROUPS = (*PORT_ENTITY_GROUPS, *SWITCH_ENTITY_GROUPS)
