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
DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

# SNMP object identifiers (numeric, so no MIB files are needed).
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
OID_BRIDGE_ADDRESS = "1.3.6.1.2.1.17.1.1.0"

OID_IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
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
