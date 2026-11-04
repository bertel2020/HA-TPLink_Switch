// Tests for what the dashboard card reads from Home Assistant. Run with: node --test tests/js/*.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";

import { collectPorts, findSwitches } from "../../custom_components/tplink_switch_snmp/frontend/tplink-switch-card.js";

const entity = (entity_id, translation_key, device_id = "dev1", platform = "tplink_switch_snmp") => [
  entity_id,
  { entity_id, translation_key, device_id, platform },
];
const state = (value, attributes = {}) => ({ state: value, attributes });

function hass() {
  const entities = Object.fromEntries([
    entity("binary_sensor.p1_link", "link"),
    entity("sensor.p1_speed", "speed"),
    entity("sensor.p1_rx", "rx_rate"),
    entity("sensor.p1_tx", "tx_rate"),
    entity("binary_sensor.p2_link", "link"),
    entity("sensor.p2_speed", "speed"),
    entity("sensor.drucker_port", "device_port"),
    entity("sensor.gast_port", "device_port"),
    entity("binary_sensor.other_link", "link", "dev2"), // another switch
    entity("light.kitchen", null, "dev1", "hue"), // another integration on the same device id
  ]);
  const states = {
    "binary_sensor.p1_link": state("on", { port: 1 }),
    "sensor.p1_speed": state("1000", { port: 1 }),
    "sensor.p1_rx": state("2.5", { port: 1 }),
    "sensor.p1_tx": state("unavailable", { port: 1 }),
    "binary_sensor.p2_link": state("off", { port: 2 }),
    "sensor.p2_speed": state("0", { port: 2 }),
    "sensor.drucker_port": state("1", { mac: "aa:bb", device_name: "Drucker", port_name: "Büro" }),
    "sensor.gast_port": state("unknown", { mac: "cc:dd", device_name: "Gast" }),
    "binary_sensor.other_link": state("on", { port: 7 }),
    "light.kitchen": state("on", { port: 9 }),
  };
  return { entities, states, devices: { dev1: { name: "TL-SG3424" }, dev2: { name: "Zweiter" } } };
}

test("the switches are found by the integration, once per device", () => {
  assert.deepEqual(findSwitches(hass()), [
    { deviceId: "dev1", name: "TL-SG3424" },
    { deviceId: "dev2", name: "Zweiter" },
  ]);
});

test("a user's own device name wins over the name", () => {
  const h = hass();
  h.devices.dev1.name_by_user = "Keller";
  assert.equal(findSwitches(h)[0].name, "Keller");
});

test("link, speed and rates of a port come together", () => {
  const [p1, p2] = collectPorts(hass(), "dev1");
  assert.deepEqual([p1.n, p1.up, p1.speed, p1.rx, p1.tx], [1, true, 1000, 2.5, null]);
  assert.deepEqual([p2.n, p2.up, p2.speed], [2, false, 0]);
  assert.equal(p1.linkEntity, "binary_sensor.p1_link");
});

test("only the ports of that switch are listed, in order", () => {
  assert.deepEqual(collectPorts(hass(), "dev1").map((p) => p.n), [1, 2]);
  assert.deepEqual(collectPorts(hass(), "dev2").map((p) => p.n), [7]);
});

test("a known device is listed at its port, one without a port is not", () => {
  const [p1, p2] = collectPorts(hass(), "dev1");
  assert.deepEqual(p1.devices.map((d) => d.name), ["Drucker"]);
  assert.equal(p1.name, "Büro");
  assert.deepEqual(p2.devices, []);
});

test("entities without a port number are left out", () => {
  const h = hass();
  for (const id of ["binary_sensor.p1_link", "sensor.p1_speed", "sensor.p1_rx", "sensor.p1_tx"]) h.states[id].attributes = {};
  assert.deepEqual(collectPorts(h, "dev1").map((p) => p.n), [2]);
});

test("nothing is found without the entity registry", () => {
  assert.deepEqual(findSwitches({}), []);
  assert.deepEqual(collectPorts({}, "dev1"), []);
});
