# Changelog

All notable changes to this integration are recorded here.

## 0.9.0 – 2026-11-05

### New

- **Loop detection:** for every port where the switch's loop detection is on there is a binary sensor **Port N loop** (problem; attribute `blocked` when the switch has blocked the port). The panel shows a note and a tag on the port's card. The values come from TP-Link's MIB for the TL-SG3424 and are not yet checked against real hardware; if the table is missing, the sensors are simply not created. New group "Loop found" in the options (if you saved the selection before, pick it there).
- **Port settings in the panel:** the panel reads from TP-Link's table how a port is set (auto negotiation or fixed to 10/100/1000 Mbit/s with duplex), the flow control and the trunk. A port with a fixed setting gets a tag on its card and a note on the overview, because the other end then has to be set the same way. A trunk is tagged too. This often explains ports that run at 100 Mbit/s only. This is not yet checked against real hardware either.
- **Port security:** if a port has the switch's port security on and has learned as many MAC addresses as it may, the panel tags it and shows a note on the overview: one more device does not get onto the network at that port. Not yet checked against real hardware.
- **Storm control and settings in the port card:** the card shown when hovering a port also lists the storm control limits (broadcast, multicast, unicast), the flow control and the learned against the allowed MAC addresses, as far as the switch reports them.
- **Alarms from the switch:** with trap receiving on, a trap for CPU or memory load over 80 %, a loop or a storm control limit fires the event `tplink_switch_snmp_alarm` (with a text in the logbook). The poll that follows still runs at once.
- **Error details:** the switch counts CRC errors, collisions, undersize and oversize packets, fragments and jabbers per port through RMON (`etherStats`). They are diagnostic sensors (off by default, only at ports the switch reports values for; new group "Error details") and part of the port card. The diagnostics table then says more exactly what to check: collisions point to a duplex mismatch, CRC errors and fragments to the cable. Not yet checked against real hardware.
- **Spanning tree:** the panel tags ports with a link that the spanning tree does not use at the moment (blocking, listening, learning) and explains on the overview that this is wanted for a spare cable. There is also the diagnostic sensor **STP topology changes** (off by default, new group "STP") and the event `tplink_switch_snmp_alarm` with `stp_topology_change` when the counter rises. It reads the standard `BRIDGE-MIB`, from any maker.

## 0.8.0 – 2026-11-04

### New

- **Panel:** Hovering a port shows a card with link and speed, receive and transmit with utilization, errors, last link change and the devices at the port. It also shows on keyboard focus and stays put when the data refreshes.
- **Choose the entities:** In the options you decide which groups of entities are created (link, rates, speed, data totals, errors, packets, utilization, link changes, MAC addresses, uptime, port of devices) and for which ports. Deselected entities are removed from the registry. Without a choice everything stays as before.

## 0.7.0 – 2026-11-04

### New

- **Repair issue:** if the switch does not answer for ten minutes, Home Assistant says so under *Settings → Repairs*; the notice goes away as soon as it answers again.
- **Panel:** a port can be turned off and on in the port detail (only if writing is allowed in the options), with a question before turning it off. Protected ports are locked and say why. New websocket command `tplink_switch_snmp/set_port_enabled`, for admins only; the snapshot has `protected` per port.

### Fixed

- Hints in the panel say "1 port", not "1 ports", in German and English.
- On a phone the statistics in the header card no longer wrap with stray dividers but sit in two columns. All four tabs run at all three font sizes without sideways overflow.
- The **Port of …** sensor of a device that was deleted in Home Assistant is removed, also if that happened while the integration was off.

### Changed

- Schemas use `probatio` as Home Assistant has since 2026.10 (before: `voluptuous`; the two are the same code there).
- Type checking with `mypy` (strict) in the CI, test coverage 100 % (the CI demands at least 98 %), `quality_scale.yaml` updated to match. Type errors it found are fixed.

## 0.6.0 – 2026-11-04

### New

- **Dashboard card** `custom:tplink-switch-card`: the front panel of the switch coloured by link speed and, for every active port, the devices that Home Assistant knows, with the data rate. Clicks open the entity. The card reads the integration's entities, so it also works for users without administrator rights. The port entities have the attribute `port` for that.
- **Writing to the switch** (option, off by default): a switch **Port N enabled** per port (`ifAdminStatus`) and the option to save port names at the switch (`ifAlias`). v1 and v2c need a community with write access. Uplinks (at least 10 learned MAC addresses) and the chosen **protected ports** are never switched off. Not tested on real hardware: the test switch's community may only read.
- **Names from the switch:** the port names that stand at the switch (`ifAlias`) are the default in the panel, in events and in the logbook; a name from the panel takes precedence. The panel shows "switched off" for ports that are off at the switch.
- **Device information from the switch:** model, hardware and firmware version, location and contact are read from the switch (from TP-Link's own MIB for TP-Link) and shown on the device and in the panel's details.
- **More counters** (off by default): packets per second (receive, transmit) and broadcast and multicast received. The panel shows them in the diagnostics and reports a lot of broadcast (from 500 packets per second) as a hint of a loop.
- **Manufacturer from the MAC address** in the device list when no known device names it (Home Assistant's manufacturer list, no internet; random addresses have none).
- **Panel:** sortable columns in the port and device lists, **CSV export** of what is shown (semicolon, with the mark for Excel, a decimal comma in German) and a **7-day history** in hourly values next to the 24 hours.
- Icons for all entities, a `quality_scale.yaml` for orientation, explanations for every field of the set-up and, in the README, sections on troubleshooting, use cases and removal.

### Fixed

- The panel's static files and the card are registered only once. If the last switch was removed and set up again, the second registration could have failed.

### Known limits

- Writing to the switch is only tested against a fake switch. CPU, memory and temperature do not exist at the test switch (firmware 1.11.10), neither in standard MIBs nor in TP-Link's MIB; the integration therefore does not show them.

## 0.5.0 – 2026-11-04

### New

- Sidebar panel, **Appearance** (palette in the header): three colour schemes as in the EnOcean panel, **Ocean** (as before), **Forest** and **Graphite**, each light and dark (light or dark follows Home Assistant if you want, the default), plus three font sizes (Small 12.6 px, Normal 14 px, Large 16 px; the smallest texts stay at 10.5 px or more). The choice is kept per Home Assistant user and also remembered in the browser.
- Sidebar panel, **history without the recorder**: the integration keeps a buffer of the data rates of its own (24 hours in five-minute averages per port) and saves it in `.storage`, also at shutdown; a restart leaves no gap. The history needs neither the recorder nor the "Receive" and "Transmit" sensors, starts when the integration starts and is deleted with the switch. New websocket command `tplink_switch_snmp/history`.

### Changed

- The panel no longer asks every 15 seconds: after each poll of the switch the integration sends the state to the open panel (new websocket command `tplink_switch_snmp/subscribe`). Only if the subscription is lost does the panel ask now and then. A longer polling interval therefore also means less traffic in the panel.
- `recorder` is no longer a dependency, and the snapshot no longer contains the entity IDs of the data rates (`entities`).

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
