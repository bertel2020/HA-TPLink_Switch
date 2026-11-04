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

## Troubleshooting

- **"The switch does not answer" during set-up:** check the address, the version and the community, and that SNMP is switched on **and saved** at the switch. `snmpget -v2c -c <community> <address> 1.3.6.1.2.1.1.1.0` on the machine that runs Home Assistant checks this. With a wrong community SNMP says nothing back; it looks like a switch that is off.
- **Entities "unavailable":** the switch did not answer two polls in a row. Home Assistant says so once in the log and keeps asking.
- **Data rates missing after the start:** the first poll has nothing to compare with; the rate appears after the second.
- **Reporting a bug:** download the diagnostics (see below) and add the log lines with `tplink_switch_snmp`.

## Use cases

- A message on your phone when the wallbox or the camera loses its link (event `tplink_switch_snmp_link_changed`).
- See which port a device is plugged into, and get a message when it changes port (for example an access point that was moved).
- A link that got slow: ports at 100 Mbit/s only and error counters point to a bad cable.
- The utilization of an uplink over time, without opening the switch itself.

## Removal

*Devices & services → TP-Link Switch (SNMP) → ⋮ → Delete.* The stored history is deleted with it. Nothing changes at the switch; SNMP and the community stay set up there. Afterwards the integration's files can be removed in HACS.

## Sidebar panel

The integration adds the entry **Switch** to the sidebar (admins only):

- **Overview:** a front panel with every port coloured by link speed, a port detail with the last 24 hours, the time of the last link change and the utilization, the ports with the most traffic and notes on errors, ports that run at 100 Mbit/s only and link changes in the last 24 hours.
- **Ports:** a table with filters, search and utilization in percent.
- **Devices:** the learned MAC addresses per port; names come from devices Home Assistant knows by their MAC address (for example from "FRITZ!Box Network"); the manufacturer from there or else from the MAC address (Home Assistant's manufacturer list, no internet; the random addresses of phones have none).
- **Diagnostics:** errors, discarded packets and data volume per port.

The **Appearance** menu (palette in the header) offers three colour schemes (Ocean, Forest, Graphite), light, dark or like Home Assistant, and three font sizes; the choice is kept per user. The panel gets a new state pushed after every poll of the switch and does not ask by itself.

Ports can be renamed in the panel (the pencil next to the port name); the name is stored with the integration. The history comes from a buffer of the integration's own (24 hours in five-minute values and 7 days in hourly values, saved in `.storage`), so it needs neither the recorder nor the sensors; it starts when the integration starts and is deleted with the switch.

Without Home Assistant, the panel can be viewed with sample data: start `python3 -m http.server 8765` in the repository folder and open `/scripts/panel-preview/index.html` (`?dark=1`, `?lang=en`, `?narrow=1`).

## Dashboard card

The integration brings the card **TP-Link Switch**: the front panel of the switch, coloured by link speed, and below it, for every active port, the devices that Home Assistant knows, with the data rate. A click on a port or a device opens its entity. Unlike the panel, every user sees it.

```yaml
type: custom:tplink-switch-card
title: Basement switch    # optional
device_id: abc123         # optional, only with more than one switch
show_devices: true        # devices per port (default: on)
show_rates: true          # data rate per port (default: on)
```

The card reads the integration's entities; the devices per port are the **Port of …** sensors. A preview without Home Assistant: `/scripts/panel-preview/card.html`.

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
| **Packets/s receive/transmit**, **broadcast/multicast receive** | off | from the packet counters |
| **Port N enabled** (switch) | only with writing | turns the port on or off |

On the device: **Uptime**. For every device that Home Assistant knows by its MAC address and that was learned at the switch, a sensor **Port of …** is added. It shows the port number and, in the attribute `port_name`, the name of the port. The sensor belongs to the switch, not to the other integration's device, because in Home Assistant a device belongs to exactly one integration.

### Which entities are created

Under **Configure** you choose which groups of entities exist (link, rates, speed, data totals, errors, packets, utilization, link changes, MAC addresses, uptime, port of devices) and for which ports (empty = all). What you deselect is not created and is removed from the entity list; its history in Home Assistant is no longer updated. The panel is not affected, it reads from the switch directly.

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

## Writing to the switch (optional)

By default the integration only reads. In the options you can switch on **Allow writing to the switch**; then there are:

- a switch **Port N enabled** per port (`ifAdminStatus`): off means no link, whatever is plugged in.
- in the panel, in the port detail, the button **Turn port off / on** (with a question; locked for protected ports).
- in the panel, when renaming a port, the box **Also save at the switch** (`ifAlias`). The names that already stand at the ports on the switch are shown as the default anyway; a name from the panel takes precedence.

Requirements and protection:

- **v1 and v2c** need a **community of their own with write access** (at the switch under *SNMP → Community*, access *read-write*), entered in the options. **v3** writes with the same user if it has write access. A switch does not answer a write from a read-only community at all; the integration reports that as an error.
- **Protected ports** are never switched off by Home Assistant: those chosen in the options and always those at which at least 10 MAC addresses were learned (mostly uplinks). Whoever switches off the port that Home Assistant reaches the switch through locks themselves out. Switching on is always allowed.
- Changes at the switch last **until it restarts** unless you save the configuration there (*System Tools → Save Config*). The integration does not save it.
- Writing has **not** been tried with the test switch (TL-SG3424, firmware 1.11.10): the community there may only read. It is tested against a fake switch.

## SNMP traps for instant notifications

By default Home Assistant asks the switch at the set interval, so a link change only shows at the next poll. With **Trap port** in the options, Home Assistant also receives SNMP traps (v1 and v2c only): as soon as a trap from the switch arrives, a poll follows at once. The content of the trap is not evaluated.

1. Choose a free UDP port, for example `1162` (ports below 1024 need privileges), and enter it in the options. In Docker the UDP port must be published.
2. At the switch under *SNMP → Notification*, add the address of Home Assistant with that port and **the same community** as a target.

A trap counts only if it comes from the switch's address, resolved when the integration starts, and the community matches. If the port cannot be opened, a warning appears in the log; polling carries on.

## Diagnostics

*Devices & services → TP-Link Switch (SNMP) → ⋮ → Download diagnostics.* The file holds the version, counters, interval and the state of the ports, but no address, no credentials, no MAC addresses and no port names.

## Development

With Python 3.14: `pip install -r requirements-dev.txt`, then `ruff check .`, `mypy`, `pytest --cov=custom_components/tplink_switch_snmp` (coverage is 100 %, the CI demands at least 98 %) and `node --test tests/js/*.test.mjs`. The tests run against a fake switch (`tests/conftest.py`) and Home Assistant's test plugin.

## Limits

- Without the option "Allow writing" it only reads; nothing is changed at the switch.
- **SNMP v1** has no 64-bit counters: the data rates then come from 32-bit counters that wrap every 34 seconds at 1 Gbit/s, and the data volume (off by default) is imprecise. With an interval above 34 seconds, a wrap is lost at full load and the rate comes out too low. Use v2c or v3 for precise values.
- **SNMP v1 and v2c** send the community in clear text. v3 has been checked at the real switch only up to the login (it answers), not with a user that is set up.
- Ports are the ports of the switch's bridge table (the number is the bridge port number), whatever they are called. VLAN, loopback and management interfaces are not ports. This has only been tested with a TL-SG3424; other JetStream models are untested.
- Manufacturer and model are not stated clearly by the switch: the manufacturer comes from the enterprise number, the model is the device description of the switch.
- The uptime carries on past the 497 days after which the switch's counter wraps. If Home Assistant restarts after that, it starts from the counter's value.
- A device behind the uplink port shows up on the port where the switch learned its MAC address. If a device moves between the uplink and another port, that counts as a port change.
- This switch does not provide LLDP neighbours over SNMP.
