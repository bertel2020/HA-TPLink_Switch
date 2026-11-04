// A stand-in for Home Assistant's hass object: answers the panel's websocket calls with sample
// data shaped like a TL-SG3424 (link and speed as seen at a real one, the rest made up).
const SAMPLE = {
  1: ["Uplink FRITZ!Box", 1000, 0.29, 2.55, 0, 7], 2: ["Drucker Büro", 100, 0.01, 0.01, 0, 1], 5: ["NAS", 1000, 0, 0.01, 0, 1],
  11: ["Kamera Hof", 100, 0.01, 0.02, 0, 1], 12: ["Access Point Flur", 1000, 0.22, 0.31, 0, 21], 15: ["Wallbox", 100, 0, 0.02, 0, 1],
  16: ["Smart-TV Wohnzimmer", 100, 2.41, 0.07, 12, 1], 17: ["Server Keller", 1000, 0.11, 0.12, 0, 2], 22: ["PC Büro", 1000, 0.03, 0.04, 0, 1],
  23: ["Hypervisor", 1000, 0.04, 0.02, 0, 1], 24: ["Switch Dachboden", 1000, 0.25, 0.27, 0, 11],
};
const NAMES = { 1: "Gateway FRITZ!Box", 2: "Drucker HP", 5: "NAS Synology", 12: "Access Point Flur", 16: "Smart-TV", 17: "Server Keller", 22: "PC Büro", 24: "Smart-Steckdose" };
const names = {};

const mac = (n, i) => `02:00:00:00:${n.toString(16).padStart(2, "0")}:${i.toString(16).padStart(2, "0")}`;
function snapshot() {
  const ports = Array.from({ length: 24 }, (_, k) => {
    const n = k + 1;
    const s = SAMPLE[n];
    const up = !!s;
    return {
      n, name: names[n] ?? (s ? s[0] : ""), if_name: `port ${n}: Gigabit Copper`, up, speed: up ? s[1] : 0,
      rx_rate: up ? s[2] : 0, tx_rate: up ? s[3] : 0, rx_bytes: up ? s[2] * 4e11 + 1e9 : 0, tx_bytes: up ? s[3] * 4e11 + 1e9 : 0,
      rx_errors: up ? s[4] : 0, tx_errors: n === 6 ? 3 : 0, rx_discards: up && n === 16 ? 40 : 0, tx_discards: 0,
      rx_util: up ? Math.round((s[2] / s[1]) * 1000) / 10 : null, tx_util: up ? Math.round((s[3] / s[1]) * 1000) / 10 : null,
      macs: up ? Array.from({ length: s[5] }, (_, i) => ({ mac: mac(n, i + 1), name: i === 0 ? NAMES[n] || null : null, manufacturer: i === 0 && NAMES[n] ? "Beispiel GmbH" : null })) : [],
      entities: up ? { rx_rate: `sensor.rx${n}`, tx_rate: `sensor.tx${n}` } : {},
    };
  });
  return {
    switches: [{ entry_id: "e1", title: "TL-SG3424 Keller", host: "192.168.79.15", mac: "64:66:b3:6c:28:64", manufacturer: "TP-Link", model: "JetStream 24-Port Gigabit L2 Managed Switch with 4 Combo SFP Slots", description: "JetStream 24-Port Gigabit L2 Managed Switch with 4 Combo SFP Slots",
      uptime: 158 * 86400 + 4 * 3600, interval: 30, last_update_success: true, ports }],
  };
}

function history(ids, start, end) {
  const out = {};
  for (const id of ids) {
    const base = SAMPLE[+id.replace(/\D/g, "")]?.[id.startsWith("sensor.rx") ? 2 : 3] || 0.05;
    let seed = id.length * 7919;
    out[id] = Array.from({ length: 96 }, (_, i) => {
      seed = (seed * 9301 + 49297) % 233280;
      return { s: String(Math.max(0, base * (0.3 + (seed / 233280) * 1.5)).toFixed(3)), lu: (Date.parse(start) + (i / 95) * (Date.parse(end) - Date.parse(start))) / 1000 };
    });
  }
  return out;
}

export function makeHass({ dark = false, language = "de" } = {}) {
  return {
    language, themes: { darkMode: dark },
    async callWS(msg) {
      await new Promise((r) => setTimeout(r, 30));
      if (msg.type === "tplink_switch_snmp/snapshot") return snapshot();
      if (msg.type === "tplink_switch_snmp/set_port_name") { names[msg.port] = msg.name.trim(); return { name: msg.name }; }
      if (msg.type === "history/history_during_period") return history(msg.entity_ids, msg.start_time, msg.end_time);
      throw new Error(`unknown command ${msg.type}`);
    },
  };
}
