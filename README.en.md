# TP-Link Switch (SNMP)

<p align="center"><em><a href="README.md">Deutsche Version</a></em></p>

Reads a TP-Link JetStream switch (tested with the **TL-SG3424**) locally over SNMP: link state, speed, data rate, utilization, errors, discarded packets and the learned MAC addresses per port. It also brings a sidebar panel, events for link and port changes and, if you want, SNMP traps for instant notifications.

## What the switch needs

Switch SNMP on (*SNMP → Global Config*) and save the configuration (*System Tools → Save Config*). Depending on the SNMP version:

- **v1 / v2c:** create a community with read access under *SNMP → Community*.
- **v3:** create a user with a group, authentication and, if you want it, encryption.

## Installation

### Via HACS (recommended)

[![Open the HACS repository in My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bertel2020&repository=HA-TPLink_Switch&category=integration)
[![Add TP-Link Switch (SNMP) to My Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tplink_switch_snmp)

1. Use the first button to open the TP-Link Switch repository in HACS.
2. Download **TP-Link Switch (SNMP)** and restart Home Assistant.
3. Use the second button to add the integration. Alternatively, open
   **Settings → Devices & services → Add integration → TP-Link Switch (SNMP)**
   in Home Assistant.

If the first button does not work, add `https://github.com/bertel2020/HA-TPLink_Switch`
in HACS under **Integrations → Custom repositories** with the category
**Integration**.

### Manual

Copy the directory `custom_components/tplink_switch_snmp` to
`/config/custom_components/tplink_switch_snmp` and restart Home Assistant.

## Set-up

In the dialog first choose **host**, **port** (default 161) and the **SNMP version**, then, depending on the version, the **community** (v1, v2c) or the **user** with authentication and encryption (v3, keys of at least 8 characters). The switch is recognised by its MAC address; the same switch cannot be set up twice.

To change it later: **Devices & services → TP-Link Switch (SNMP) → ⋮ → Reconfigure** for address, version and credentials (the same switch must answer), **Configure** for the options:

- **Polling interval** (10 to 3600 seconds, default 30). Shorter intervals give more precise rates but put more load on the switch.
- **Trap port** (0 = off), see below.

## Sidebar panel

The integration adds the entry **Switch** to the sidebar (admins only):

- **Overview:** a front panel with every port coloured by link speed, a port detail with the last 24 hours (from Home Assistant's history), the time of the last link change and the utilization, the ports with the most traffic and notes on errors, ports that run at 100 Mbit/s only and link changes in the last 24 hours.
- **Ports:** a table with filters, search and utilization in percent.
- **Devices:** the learned MAC addresses per port; names and manufacturers come from devices Home Assistant knows by their MAC address (for example from "FRITZ!Box Network").
- **Diagnostics:** errors, discarded packets and data volume per port.

Ports can be renamed in the panel (the pencil next to the port name); the name is stored with the integration. The history needs the recorder and the port's "Receive" and "Transmit" sensors.

Without Home Assistant, the panel can be viewed with sample data: start `python3 -m http.server 8765` in the repository folder and open `/scripts/panel-preview/index.html` (`?dark=1`, `?lang=en`, `?narrow=1`).

## Entities

Per port:

| Entity | Default | Note |
| --- | --- | --- |
| **Link** (binary_sensor) | on | |
| **Receive**, **Transmit** (Mbit/s) | on | calculated from the switch's counters |
| **Speed** | on | |
| **MAC addresses** | on | the count; the list is in the attribute `mac_addresses` |
| **Receive / transmit utilization** (%) | off | data rate in relation to the link speed |
| **Received / sent total** | off | data volume |
| **Receive / transmit errors** | off | |
| **Receive / transmit discarded** | off | discarded packets |
| **Link changed** (timestamp) | off | time of the last link change |

On the device: **Uptime**. For every device that Home Assistant knows by its MAC address and that was learned at the switch, a sensor **Port of …** is added. It shows the port number and, in the attribute `port_name`, the name of the port. The sensor belongs to the switch, not to the other integration's device, because in Home Assistant a device belongs to exactly one integration.

## Events and logbook

Both events appear in the logbook and can be used as triggers in automations:

- `tplink_switch_snmp_link_changed`: a link changed. Data: `port`, `port_name`, `up`, `speed`, `flap` (the link dropped and came back between two polls), `switch`, `entry_id`, `entity_id`. After a reboot of the switch there are no events.
- `tplink_switch_snmp_device_moved`: a device that Home Assistant knows shows up on another port. Data: `mac`, `name`, `device_id`, `from_port`, `from_port_name`, `to_port`, `to_port_name`, `switch`, `entry_id`.

```yaml
triggers:
  - trigger: event
    event_type: tplink_switch_snmp_link_changed
    event_data:
      port: 12
      up: false
```

## SNMP traps for instant notifications

By default Home Assistant asks the switch at the set interval, so a link change only shows at the next poll. With **Trap port** in the options, Home Assistant also receives SNMP traps (v1 and v2c only): as soon as a trap from the switch arrives, a poll follows at once. The content of the trap is not evaluated.

1. Choose a free UDP port, for example `1162` (ports below 1024 need privileges), and enter it in the options. In Docker the UDP port must be published.
2. At the switch under *SNMP → Notification*, add the address of Home Assistant with that port and **the same community** as a target.

A trap counts only if it comes from the switch's address, resolved when the integration starts, and the community matches. If the port cannot be opened, a warning appears in the log; polling carries on.

## Diagnostics

*Devices & services → TP-Link Switch (SNMP) → ⋮ → Download diagnostics.* The file holds the version, counters, interval and the state of the ports, but no address, no credentials, no MAC addresses and no port names.

## Limits

- It only reads; nothing is changed at the switch.
- **SNMP v1** has no 64-bit counters: the data rates then come from 32-bit counters that wrap every 34 seconds at 1 Gbit/s, and the data volume (off by default) is imprecise. With an interval above 34 seconds, a wrap is lost at full load and the rate comes out too low. Use v2c or v3 for precise values.
- **SNMP v1 and v2c** send the community in clear text. v3 has been checked at the real switch only up to the login (it answers), not with a user that is set up.
- Ports are the ports of the switch's bridge table (the number is the bridge port number), whatever they are called. VLAN, loopback and management interfaces are not ports. This has only been tested with a TL-SG3424; other JetStream models are untested.
- Manufacturer and model are not stated clearly by the switch: the manufacturer comes from the enterprise number, the model is the device description of the switch.
- The uptime carries on past the 497 days after which the switch's counter wraps. If Home Assistant restarts after that, it starts from the counter's value.
- A device behind the uplink port shows up on the port where the switch learned its MAC address. If a device moves between the uplink and another port, that counts as a port change.
- This switch does not provide LLDP neighbours over SNMP.
