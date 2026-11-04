# Changelog

All notable changes to this integration are recorded here.

## 0.4.0 – 2026-11-04

### New

- **SNMP v1, v2c and v3:** the version can be chosen in the set-up dialog. With v3 there are a user, authentication (MD5, SHA, SHA-224/256/384/512) and encryption (DES, AES-128/192/256). Reconfigure can change the version. Existing entries stay on v2c. With v1 the integration reads the 32-bit counters (v1 has no 64-bit counters) and walks with GETNEXT.
- **Polling interval** in the options (10 to 3600 seconds, default 30), applied without a reload.
- **Discarded packets** (receive/transmit) and **utilization in percent** (receive/transmit) as sensors, both off by default. The panel shows the utilization in the port list and the port detail, and the diagnostics the discarded packets.
- **Link changes:** event `tplink_switch_snmp_link_changed` with a logbook entry ("Port 12 (AP): link up at 1 Gbit/s", "link down", "link was lost and came back"), a **Link changed** sensor (timestamp, off by default) and, in the panel, the time of the last change and a note on ports with changes in the last 24 hours. After a reboot of the switch there are no events.
- **Device assignment:** every device that Home Assistant knows by its MAC address and that was learned at the switch gets a sensor **Port of …** (port number, port name as an attribute). If such a device changes port, the event `tplink_switch_snmp_device_moved` fires, with a logbook entry.
- **SNMP traps** (v1 and v2c) on a port from the options: a trap from the switch triggers a poll at once. A trap counts only with the right community and from the switch's address.
- **Diagnostics** to download, without address, credentials, MAC addresses and port names.
- **English README**; the German README explains set-up, options, events and traps.

### Changed

- The installation section of the READMEs with the buttons for HACS and the set-up.

### Known limits

- Config flow, options, events, traps and diagnostics are checked with a fake switch and Home Assistant's test plugin, not in a running instance. Checked against the real switch are queries with v1 and v2c, the port detection and receiving traps with `snmptrap`; with v3 the switch answers, a user that is set up was not tested.

## 0.3.0 – 2026-11-04

### New

- **Reconfigure:** address, community and port of a switch that is set up can be changed without deleting it. If a different switch answers at the new address, the dialog stops.

### Changed

- Manufacturer and model of the device come from the switch (enterprise number and device description) and are no longer fixed to "TL-SG3424". The panel shows them in the details.
- Ports are the ports of the switch's bridge table, no longer the interfaces whose name starts with "port". This also finds models with another naming, and the VLAN interface is never taken for a port. On the TL-SG3424 port numbers and entity IDs stay the same.

### Fixed

- The uptime carries on when the switch's counter wraps after 497 days and starts over only after a real reboot.
- Device names in the panel use the current device registry lookup; the older one is deprecated since 2026.10.
- The README said SNMP v1/v2c; only v2c is supported.

## 0.2.0 – 2026-11-04

### New

- Sidebar panel **Switch** (admins only) in the look of the EnOcean Eltako integration, light and dark following Home Assistant, German and English. **Overview** with a front panel (ports coloured by link speed, a dot for errors), a port detail with the last 24 hours, the ports with the most traffic and notes on errors and ports that run at 100 Mbit/s only. **Ports** as a table with filters and search, **Devices** with the learned MAC addresses per port, **Diagnostics** with error counters and data volume.
- Ports can be renamed in the panel; the name is stored with the integration.
- Names and manufacturers of devices come from devices Home Assistant knows by their MAC address, for example from "FRITZ!Box Network".
- New websocket commands `tplink_switch_snmp/snapshot` and `tplink_switch_snmp/set_port_name`, both for admins only.
- A preview of the panel without Home Assistant in `scripts/panel-preview/`.

### Known limits

- So far the panel has only been checked in the preview with sample data, not in a running Home Assistant instance.

## 0.1.0 – 2026-11-04

### New

- First version: reads a TP-Link JetStream switch (tested with the TL-SG3424) locally over SNMP v2c. Per port **link**, **speed**, **receive** and **transmit** in Mbit/s and the **number of MAC addresses** (the list is in the attribute `mac_addresses`); total volume and error counters are off by default. **Uptime** on the device.
- Set-up in a dialog with host, community and port; the switch is recognised by its MAC address.
