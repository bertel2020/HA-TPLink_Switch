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
const disabled = {}; // ports switched off in the preview
const userData = {}; // what Home Assistant keeps per user

const mac = (n, i) => `02:00:00:00:${n.toString(16).padStart(2, "0")}:${i.toString(16).padStart(2, "0")}`;
function snapshot() {
  const ports = Array.from({ length: 24 }, (_, k) => {
    const n = k + 1;
    const s = SAMPLE[n];
    const up = !!s;
    return {
      n, name: names[n] ?? (s ? s[0] : ""), if_name: `port ${n}: Gigabit Copper`, up, speed: up ? s[1] : 0,
      rx_rate: up ? s[2] : 0, tx_rate: up ? s[3] : 0, rx_bytes: up ? s[2] * 4e11 + 1e9 : 0, tx_bytes: up ? s[3] * 4e11 + 1e9 : 0,
      link_changed_at: n === 16 ? new Date(Date.now() - 3 * 3600000).toISOString() : new Date(Date.now() - 40 * 86400000).toISOString(),
      rx_pps: up ? Math.round(s[2] * 90) : null, tx_pps: up ? Math.round(s[3] * 90) : null, rx_mcast_pps: up ? 2.5 : null, rx_bcast_pps: up ? (n === 16 ? 820 : 3.1) : null,
      pvid: n === 12 ? 30 : n >= 11 && n <= 16 ? 20 : n <= 5 ? 1 : 10,
      vlans_untagged: [n === 12 ? 30 : n >= 11 && n <= 16 ? 20 : n <= 5 ? 1 : 10], vlans_tagged: n === 1 || n === 24 ? [10, 20, 30] : [],
      custom_name: names[n] ?? "", alias: s ? s[0] : "", admin_up: disabled[n] === undefined ? n !== 20 : !disabled[n], protected: n === 1 || n === 24,
      rx_errors: up ? s[4] : 0, tx_errors: n === 6 ? 3 : 0, rx_discards: up && n === 16 ? 40 : 0, tx_discards: 0,
      rx_util: up ? Math.round((s[2] / s[1]) * 1000) / 10 : null, tx_util: up ? Math.round((s[3] / s[1]) * 1000) / 10 : null,
      macs: up ? Array.from({ length: s[5] }, (_, i) => ({ mac: mac(n, i + 1), name: i === 0 ? NAMES[n] || null : null, manufacturer: i === 0 && NAMES[n] ? "Beispiel GmbH" : null })) : [],
    };
  });
  return {
    switches: [{ entry_id: "e1", title: "TL-SG3424 Keller", host: "192.168.79.15", mac: "64:66:b3:6c:28:64", manufacturer: "TP-Link", model: "TL-SG3424", hw_version: "1.0", sw_version: "1.11.10 Build 20150713 Rel.53496(n)", location: "Technikraum", contact: "Roberto", description: "JetStream 24-Port Gigabit L2 Managed Switch with 4 Combo SFP Slots",
      can_act: true, qos_mode: "wrr", stp_changes: 4, stp_root_port: 1, features: { igmp: true, dscp: false, dos: true, dhcp: false, dot1x: false, mirror: true }, mirror: [{ monitor: 24, ingress: [5], egress: [5] }],
      vlans: { 1: "Default", 10: "Büro", 20: "IoT", 30: "Gäste" }, can_write: true, uptime: 158 * 86400 + 4 * 3600, interval: 30, last_update_success: true, ports }],
  };
}

// the integration's own 24 hour history: five-minute values, for ports that have a link
function history(port, range = "24h") {
  const sample = SAMPLE[port];
  const bucket = { "24h": 300, "7d": 3600, "30d": 7200 }[range], count = { "24h": 288, "7d": 168, "30d": 360 }[range];
  const end = Date.now() / 1000, start = end - bucket * count;
  let seed = port * 7919;
  const points = !sample ? [] : Array.from({ length: count }, (_, i) => {
    seed = (seed * 9301 + 49297) % 233280;
    const r = () => { seed = (seed * 9301 + 49297) % 233280; return 0.3 + (seed / 233280) * 1.5; };
    return [Math.floor(start / bucket) * bucket + i * bucket, +(sample[2] * r()).toFixed(3), +(sample[3] * r()).toFixed(3)];
  });
  // link events: [time, 1 up / 0 down, speed]; a few per port with a link, the range decides how far back
  const h = 3600, back = (hours) => end - hours * h;
  const events = !sample ? [] : [[back(14), 0, 0], [back(13.9), 1, sample[1]], ...(port === 12 ? [[back(9.5), 1, 100], [back(3), 0, 0], [back(2.95), 1, sample[1]]] : [])]
    .concat(range !== "24h" ? [[back(60), 0, 0], [back(59.5), 1, sample[1]], [back(130), 0, 0], [back(129), 1, sample[1]]] : [])
    .concat(range === "30d" ? [[back(400), 0, 0], [back(399), 1, sample[1]]] : []).sort((a, b) => a[0] - b[0]);
  return { start, end, bucket, points, link: { since: end - (range === "30d" ? 20 : 40) * 86400, up: !!sample, speed: sample ? sample[1] : 0, events } };
}

export function makeHass({ dark = false, language = "de", pushEvery = 5000 } = {}) {
  return {
    language, themes: { darkMode: dark },
    // the panel subscribes; the preview pushes a new snapshot every few seconds like a poll
    connection: {
      async subscribeMessage(callback, message) {
        if (message.type !== "tplink_switch_snmp/subscribe") throw new Error(`unknown command ${message.type}`);
        const timer = setInterval(() => callback(snapshot()), pushEvery);
        window.__pushes = (window.__pushes || 0) + 1;
        return () => { clearInterval(timer); window.__pushes -= 1; };
      },
    },
    async callWS(msg) {
      await new Promise((r) => setTimeout(r, 30));
      if (msg.type === "tplink_switch_snmp/snapshot") return snapshot();
      if (msg.type === "tplink_switch_snmp/set_port_name") { names[msg.port] = msg.name.trim(); return { name: msg.name }; }
      if (msg.type === "frontend/get_user_data") return { value: userData[msg.key] ?? null };
      if (msg.type === "frontend/set_user_data") { userData[msg.key] = msg.value; return null; }
      if (msg.type === "tplink_switch_snmp/set_port_enabled") {
        if (msg.port === 1) throw new Error("Port 1 is protected and is not turned off: it is chosen in the options or an uplink with many devices.");
        disabled[msg.port] = !msg.enabled;
        return { enabled: msg.enabled };
      }
      if (msg.type === "tplink_switch_snmp/action") return { action: msg.action };
      if (msg.type === "tplink_switch_snmp/history") return history(msg.port, msg.range);
      throw new Error(`unknown command ${msg.type}`);
    },
  };
}
