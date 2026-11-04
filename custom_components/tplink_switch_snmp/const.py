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
