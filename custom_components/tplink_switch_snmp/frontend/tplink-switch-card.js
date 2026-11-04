// Dashboard card "TP-Link Switch": the front panel of the switch with the devices at each port.
// It reads the entities of the integration from Home Assistant, so it works for every user and
// needs no websocket command. Add it with `type: custom:tplink-switch-card`.

const INTEGRATION = "tplink_switch_snmp";

const TEXT = {
  de: {
    title: "Switch",
    noSwitch: "Kein Switch dieser Integration gefunden.",
    linkDown: "kein Link",
    unknownDevice: "Gerät",
    noDevices: "Keine bekannten Geräte an den aktiven Ports.",
    ports: "Ports",
    active: "aktiv",
    rx: "Empfang",
    tx: "Senden",
  },
  en: {
    title: "Switch",
    noSwitch: "No switch of this integration found.",
    linkDown: "no link",
    unknownDevice: "Device",
    noDevices: "No known devices at the active ports.",
    ports: "ports",
    active: "active",
    rx: "Receive",
    tx: "Transmit",
  },
};

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

/** The switches of the integration that Home Assistant knows: [{deviceId, name}]. */
export function findSwitches(hass) {
  const found = new Map();
  for (const entry of Object.values(hass.entities || {})) {
    if (entry.platform !== INTEGRATION || !entry.device_id || found.has(entry.device_id)) continue;
    found.set(entry.device_id, hass.devices?.[entry.device_id]?.name_by_user || hass.devices?.[entry.device_id]?.name || "");
  }
  return [...found].map(([deviceId, name]) => ({ deviceId, name }));
}

const number = (state) => {
  const value = parseFloat(state?.state);
  return Number.isFinite(value) ? value : null;
};

/**
 * The ports of one switch, read from its entities: link, speed and rates, and the devices that
 * Home Assistant knows at the port. Ports are told apart by the `port` attribute of the entities.
 */
export function collectPorts(hass, deviceId) {
  const ports = new Map();
  const port = (n) => {
    if (!ports.has(n)) ports.set(n, { n, up: false, speed: 0, rx: null, tx: null, linkEntity: null, devices: [] });
    return ports.get(n);
  };
  for (const entry of Object.values(hass.entities || {})) {
    if (entry.platform !== INTEGRATION || entry.device_id !== deviceId) continue;
    const state = hass.states?.[entry.entity_id];
    const n = Number(state?.attributes?.port);
    if (!state || !Number.isInteger(n) || n < 1) continue;
    const p = port(n);
    switch (entry.translation_key) {
      case "link":
        p.up = state.state === "on";
        p.linkEntity = entry.entity_id;
        break;
      case "speed":
        p.speed = number(state) ?? 0;
        break;
      case "rx_rate":
        p.rx = number(state);
        break;
      case "tx_rate":
        p.tx = number(state);
        break;
      default:
        break;
    }
  }
  // "Port of …" sensors: their state is the port number the known device is plugged into
  for (const entry of Object.values(hass.entities || {})) {
    if (entry.platform !== INTEGRATION || entry.device_id !== deviceId || entry.translation_key !== "device_port") continue;
    const state = hass.states?.[entry.entity_id];
    const n = number(state);
    if (!state || n == null || !ports.has(n)) continue;
    ports.get(n).devices.push({ name: state.attributes.device_name || state.attributes.mac || "", mac: state.attributes.mac, entity: entry.entity_id });
    ports.get(n).name = state.attributes.port_name || ports.get(n).name || "";
  }
  return [...ports.values()].sort((a, b) => a.n - b.n);
}

const Base = globalThis.HTMLElement ?? class {};

class TplinkSwitchCard extends Base {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    if (this.attachShadow) {
      this.attachShadow({ mode: "open" });
      // one listener for the lifetime of the card; the content below it is replaced on every update
      this.shadowRoot.addEventListener("click", (event) => {
        const entityId = event.target.closest("[data-entity]")?.dataset.entity;
        if (entityId) this.dispatchEvent(new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId } }));
      });
    }
  }

  setConfig(config) {
    this._config = { show_devices: true, show_rates: true, ...config };
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 6;
  }

  static getStubConfig() {
    return { show_devices: true, show_rates: true };
  }

  get _t() {
    return TEXT[(this._hass?.language || "en").startsWith("de") ? "de" : "en"];
  }

  _num(value) {
    return new Intl.NumberFormat(this._hass?.language || "en", { maximumFractionDigits: value < 10 ? 2 : 1 }).format(value);
  }

  _render() {
    if (!this._hass || !this.shadowRoot) return;
    const t = this._t;
    const switches = findSwitches(this._hass);
    const chosen = switches.find((s) => s.deviceId === this._config.device_id) ?? switches[0];
    const title = this._config.title ?? (chosen?.name || t.title);
    if (!chosen) {
      this.shadowRoot.innerHTML = `${this._style()}<ha-card header="${escapeHtml(title)}"><div class="empty">${escapeHtml(t.noSwitch)}</div></ha-card>`;
      return;
    }
    const ports = collectPorts(this._hass, chosen.deviceId);
    const odd = ports.filter((p) => p.n % 2 === 1);
    const even = ports.filter((p) => p.n % 2 === 0);
    const tile = (p) => {
      const cls = !p.up ? "down" : p.speed >= 1000 ? "g1000" : p.speed >= 100 ? "g100" : "g10";
      const label = `${p.name ? `${p.name} · ` : ""}${p.up ? `${p.speed} Mbit/s` : t.linkDown}`;
      return `<button class="port ${cls}" data-entity="${escapeHtml(p.linkEntity || "")}" title="${escapeHtml(`Port ${p.n}: ${label}`)}" aria-label="${escapeHtml(`Port ${p.n}: ${label}`)}"><span class="n">${p.n}</span><span class="jack"></span></button>`;
    };
    const columns = Math.max(odd.length, even.length);
    const active = ports.filter((p) => p.up);
    const listed = this._config.show_devices ? active.filter((p) => p.devices.length) : [];
    const rows = listed
      .map((p) => {
        const rates = this._config.show_rates && (p.rx != null || p.tx != null) ? `<span class="rates">${t.rx} ${this._num(p.rx ?? 0)} · ${t.tx} ${this._num(p.tx ?? 0)} Mbit/s</span>` : "";
        const chips = p.devices.map((d) => `<button class="dev" data-entity="${escapeHtml(d.entity)}">${escapeHtml(d.name || t.unknownDevice)}</button>`).join("");
        return `<div class="row"><div class="head"><b>Port ${p.n}</b>${p.name ? `<span class="sub">${escapeHtml(p.name)}</span>` : ""}${rates}</div><div class="devs">${chips}</div></div>`;
      })
      .join("");
    this.shadowRoot.innerHTML = `${this._style()}<ha-card header="${escapeHtml(title)}">
      <div class="sum">${active.length} / ${ports.length} ${escapeHtml(t.ports)} ${escapeHtml(t.active)}</div>
      <div class="plate" style="--cols:${columns}"><div class="row-ports">${odd.map(tile).join("")}</div><div class="row-ports">${even.map(tile).join("")}</div></div>
      ${this._config.show_devices ? `<div class="list">${rows || `<div class="empty">${escapeHtml(t.noDevices)}</div>`}</div>` : ""}
    </ha-card>`;
  }

  _style() {
    return `<style>
      :host { display: block; }
      .sum { padding: 0 16px 8px; color: var(--secondary-text-color); font-size: 13px; }
      .plate { margin: 0 16px; padding: 10px; border: 1px solid var(--divider-color); border-radius: 10px; background: var(--secondary-background-color, transparent); display: grid; gap: 6px; overflow-x: auto; }
      .row-ports { display: grid; grid-template-columns: repeat(var(--cols, 12), minmax(30px, 1fr)); gap: 6px; min-width: 420px; }
      .port { all: unset; box-sizing: border-box; cursor: pointer; text-align: center; padding: 3px 2px 5px; border-radius: 6px; border: 1px solid var(--divider-color); background: var(--card-background-color, #fff); display: grid; gap: 2px; }
      .port:hover { border-color: var(--primary-color); }
      .port:focus-visible, .dev:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
      .n { font-size: 10px; color: var(--secondary-text-color); }
      .jack { height: 14px; border-radius: 3px; border: 2px solid var(--disabled-text-color, #bbb); opacity: .8; }
      .g1000 .jack { border-color: var(--success-color, #2e9b57); background: color-mix(in srgb, var(--success-color, #2e9b57) 28%, transparent); opacity: 1; }
      .g100 .jack { border-color: var(--warning-color, #d98a1e); background: color-mix(in srgb, var(--warning-color, #d98a1e) 28%, transparent); opacity: 1; }
      .g10 .jack { border-color: var(--error-color, #c0392b); background: color-mix(in srgb, var(--error-color, #c0392b) 22%, transparent); opacity: 1; }
      .list { padding: 8px 16px 12px; display: grid; gap: 10px; }
      .row { display: grid; gap: 4px; }
      .head { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; font-size: 14px; }
      .sub, .rates { color: var(--secondary-text-color); font-size: 12px; }
      .rates { margin-left: auto; }
      .devs { display: flex; flex-wrap: wrap; gap: 6px; }
      .dev { all: unset; cursor: pointer; padding: 2px 10px; border-radius: 12px; font-size: 12px; background: var(--primary-color); color: var(--text-primary-color, #fff); opacity: .9; }
      .dev:hover { opacity: 1; }
      .empty { padding: 12px 16px; color: var(--secondary-text-color); font-size: 13px; }
    </style>`;
  }
}

if (typeof customElements !== "undefined" && !customElements.get("tplink-switch-card")) {
  customElements.define("tplink-switch-card", TplinkSwitchCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "tplink-switch-card",
    name: "TP-Link Switch",
    description: "The front panel of the switch with the devices at each port.",
  });
}

export { TplinkSwitchCard };
