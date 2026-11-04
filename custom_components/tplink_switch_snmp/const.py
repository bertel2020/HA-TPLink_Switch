"""Constants for the TP-Link switch SNMP integration."""

from __future__ import annotations

DOMAIN = "tplink_switch_snmp"

CONF_COMMUNITY = "community"

DEFAULT_PORT = 161
DEFAULT_COMMUNITY = "public"
DEFAULT_SCAN_INTERVAL = 30

# SNMP object identifiers (numeric, so no MIB files are needed).
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
OID_BRIDGE_ADDRESS = "1.3.6.1.2.1.17.1.1.0"

OID_IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"
OID_IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"
OID_IF_HC_IN_OCTETS = "1.3.6.1.2.1.31.1.1.1.6"
OID_IF_HC_OUT_OCTETS = "1.3.6.1.2.1.31.1.1.1.10"
OID_IF_HIGH_SPEED = "1.3.6.1.2.1.31.1.1.1.15"

# Forwarding database: Q-BRIDGE (per VLAN) first, classic BRIDGE as fallback.
OID_FDB_Q = "1.3.6.1.2.1.17.7.1.2.2.1.2"
OID_FDB = "1.3.6.1.2.1.17.4.3.1.2"
OID_BASE_PORT_IF_INDEX = "1.3.6.1.2.1.17.1.4.1.2"
