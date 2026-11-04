# Changelog

All notable changes to this integration are recorded here.

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
