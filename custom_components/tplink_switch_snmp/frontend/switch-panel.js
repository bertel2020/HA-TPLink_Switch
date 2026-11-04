// Sidebar panel "Switch": a plain web component without a build step. It reads the websocket
// commands of the integration (websocket_api.py) and the history of the port rate sensors.
// Its parts are loaded with the query string of this file, so an update loads every part new.
const V = new URL(import.meta.url).search;
const [{ STYLES }, { translator }, theme] = await Promise.all([
  import(`./styles.js${V}`),
  import(`./texts.js${V}`),
  import(`./theme.js${V}`),
]);
const { applyAppearance, cleanPrefs, DEFAULTS, MODES, SCHEMES, SIZES, tokens } = theme;

const DOMAIN = "tplink_switch_snmp";
const LOOK_KEY = "tplink_switch_snmp_look";
// The server pushes every poll. This slow check only matters if the subscription is lost.
const FALLBACK_MS = 60000;
const STALE_MS = 5 * 60000;
const MAX_MACS = 50;

// Material Design Icons (Apache 2.0)
const ICON = {
  palette: "M12,3A9,9 0 0,0 3,12A9,9 0 0,0 12,21A1.5,1.5 0 0,0 13.5,19.5C13.5,19.11 13.35,18.76 13.11,18.5C12.88,18.23 12.75,17.88 12.75,17.5A1.5,1.5 0 0,1 14.25,16H16A5,5 0 0,0 21,11C21,6.58 16.97,3 12,3M6.5,12A1.5,1.5 0 0,1 5,10.5A1.5,1.5 0 0,1 6.5,9A1.5,1.5 0 0,1 8,10.5A1.5,1.5 0 0,1 6.5,12M9.5,8A1.5,1.5 0 0,1 8,6.5A1.5,1.5 0 0,1 9.5,5A1.5,1.5 0 0,1 11,6.5A1.5,1.5 0 0,1 9.5,8M14.5,8A1.5,1.5 0 0,1 13,6.5A1.5,1.5 0 0,1 14.5,5A1.5,1.5 0 0,1 16,6.5A1.5,1.5 0 0,1 14.5,8M17.5,12A1.5,1.5 0 0,1 16,10.5A1.5,1.5 0 0,1 17.5,9A1.5,1.5 0 0,1 19,10.5A1.5,1.5 0 0,1 17.5,12Z",
  lan: "M10,2C8.89,2 8,2.89 8,4V7C8,8.11 8.89,9 10,9H11V11H2V13H6V15H5C3.89,15 3,15.89 3,17V20C3,21.11 3.89,22 5,22H9C10.11,22 11,21.11 11,20V17C11,15.89 10.11,15 9,15H8V13H16V15H15C13.89,15 13,15.89 13,17V20C13,21.11 13.89,22 15,22H19C20.11,22 21,21.11 21,20V17C21,15.89 20.11,15 19,15H18V13H22V11H13V9H14C15.11,9 16,8.11 16,7V4C16,2.89 15.11,2 14,2H10Z",
  search: "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",
  open: "M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z",
  menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
  warn: "M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z",
  ok: "M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M10,17L5,12L6.41,10.58L10,14.17L17.59,6.58L19,8L10,17Z",
  next: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  edit: "M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z",
};
const icon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${ICON[name]}"/></svg>`;

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class TplinkSwitchPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._listen();
    this._hass = null;
    this._t = translator("en");
    this._lang = "en";
    this._data = null;
    this._error = null;
    this._tab = "overview";
    this._entry = null; // entry_id of the shown switch
    this._sel = null; // selected port number
    this._filter = "all";
    this._dfilter = "all";
    this._q = "";
    this._dq = "";
    this._details = false;
    this._editing = false;
    this._history = new Map(); // port key -> {at, rx, tx}
    this._timer = null;
    this._loading = false;
    this._unsub = null;
    this._subscribing = false;
    this._look = { ...DEFAULTS };
    this._lookKey = null;
    this._menuOpen = false;
    this._lastData = 0;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    const lang = hass.language || "en";
    if (first) {
      try {
        this._look = cleanPrefs(JSON.parse(localStorage.getItem(LOOK_KEY)));
      } catch {
        this._look = { ...DEFAULTS };
      }
    }
    this._applyLook();
    if (first) this._loadLook();
    if (lang !== this._lang) {
      this._lang = lang;
      this._t = translator(lang);
      if (this._data) this._render();
    }
    if (first) this._load();
    if (this.isConnected) this._subscribe();
  }

  set narrow(value) {
    this.toggleAttribute("narrow", !!value);
  }

  set panel(_value) {}

  connectedCallback() {
    this._timer = setInterval(() => {
      // with a working subscription nothing is polled, unless the data has gone stale
      if (!this._unsub || Date.now() - this._lastData > STALE_MS) this._load();
    }, FALLBACK_MS);
    if (this._hass) {
      this._load();
      this._subscribe();
    }
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._unsub?.();
    this._unsub = null;
  }

  // The integration sends the snapshot after each poll of a switch; the connection brings the
  // subscription back after a reconnect.
  async _subscribe() {
    if (this._unsub || this._subscribing || !this._hass?.connection) return;
    this._subscribing = true;
    try {
      this._unsub = await this._hass.connection.subscribeMessage(
        (event) => {
          this._data = event.switches;
          this._error = null;
          this._lastData = Date.now();
          this._render();
        },
        { type: `${DOMAIN}/subscribe` },
      );
    } catch {
      this._unsub = null; // the slow check keeps the panel up to date
    } finally {
      this._subscribing = false;
    }
  }

  async _load() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try {
      const result = await this._hass.callWS({ type: `${DOMAIN}/snapshot` });
      this._data = result.switches;
      this._error = null;
      this._lastData = Date.now();
    } catch (err) {
      this._error = err?.message || String(err);
    } finally {
      this._loading = false;
    }
    this._render();
  }

  // ---- appearance ----------------------------------------------------------------------------

  // the palette is set again only when the choice or Home Assistant's mode changed
  _applyLook() {
    const dark = this._hass?.themes?.darkMode;
    const key = `${this._look.scheme}|${this._look.mode}|${this._look.size}|${dark}`;
    if (key === this._lookKey) return;
    this._lookKey = key;
    applyAppearance(this, this._look, dark);
  }

  // the choice of this Home Assistant user wins over the browser's cache
  async _loadLook() {
    try {
      const { value } = await this._hass.callWS({ type: "frontend/get_user_data", key: LOOK_KEY });
      if (!value) return;
      this._look = cleanPrefs(value);
      localStorage.setItem(LOOK_KEY, JSON.stringify(this._look));
      this._applyLook();
      this._render();
    } catch {
      // no user data (older Home Assistant): the browser's cache stays
    }
  }

  _setLook(patch) {
    this._look = cleanPrefs({ ...this._look, ...patch });
    try {
      localStorage.setItem(LOOK_KEY, JSON.stringify(this._look));
    } catch {
      // storage blocked: the choice holds until the page is closed
    }
    this._hass.callWS({ type: "frontend/set_user_data", key: LOOK_KEY, value: this._look }).catch(() => {});
    this._applyLook();
  }

  _lookMenu() {
    const t = this._t;
    const dark = this.hasAttribute("dark");
    const group = (kind, label, options) =>
      `<div class="lookgroup" role="radiogroup" aria-label="${esc(label)}"><span class="lookhead">${esc(label)}</span>${options
        .map(
          ([value, text, dot]) =>
            `<button role="radio" aria-checked="${this._look[kind] === value}" data-a="look" data-kind="${kind}" data-v="${esc(value)}">${dot ? `<i class="dot" style="background:${dot}"></i>` : ""}${esc(text)}</button>`,
        )
        .join("")}</div>`;
    const accent = (name) => tokens({ ...this._look, scheme: name }, dark)["--accent"];
    return `<div class="look-menu" id="lookMenu" aria-label="${esc(t("lookTitle"))}">${
      group("scheme", t("lookScheme"), Object.keys(SCHEMES).map((n) => [n, t(n), accent(n)])) +
      group("mode", t("lookMode"), MODES.map((n) => [n, t(n)])) +
      group("size", t("lookSize"), Object.keys(SIZES).map((n) => [n, t(n)]))
    }</div>`;
  }

  // ---- helpers -------------------------------------------------------------------------------

  get _switch() {
    const list = this._data || [];
    return list.find((s) => s.entry_id === this._entry) || list[0] || null;
  }

  _num(value, digits = 2) {
    if (value == null) return this._t("noData");
    return new Intl.NumberFormat(this._lang, { minimumFractionDigits: 0, maximumFractionDigits: value < 10 ? digits : 1 }).format(value);
  }

  _bytes(value) {
    const units = ["B", "kB", "MB", "GB", "TB", "PB"];
    let v = value;
    let i = 0;
    while (v >= 1000 && i < units.length - 1) {
      v /= 1000;
      i += 1;
    }
    return `${new Intl.NumberFormat(this._lang, { maximumFractionDigits: i ? 1 : 0 }).format(v)} ${units[i]}`;
  }

  _uptime(seconds) {
    const t = this._t;
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    if (d) return { big: String(d), unit: t("days") };
    if (h) return { big: String(h), unit: t("hours") };
    return { big: String(Math.floor(seconds / 60)), unit: t("minutes") };
  }

  _portLabel(p) {
    return p.name || "";
  }

  _total(p) {
    return (p.rx_rate || 0) + (p.tx_rate || 0);
  }

  _linkClass(p) {
    if (!p.up) return "";
    return p.speed >= 1000 ? "s1000" : p.speed >= 100 ? "s100" : "s10";
  }

  _speedText(p) {
    const t = this._t;
    if (!p.up) return t("noLink");
    return p.speed >= 1000 ? t("l1000") : p.speed >= 100 ? t("l100") : t("l10");
  }

  _util(value) {
    return value == null ? "" : `${this._num(value, 1)} %`;
  }

  // Time of the last link change; null if it is the link-up at the switch's own start.
  _changedAt(sw, p) {
    if (!p.link_changed_at) return null;
    const at = Date.parse(p.link_changed_at);
    const boot = Date.now() - sw.uptime * 1000;
    return at > boot + 300000 ? at : null;
  }

  _ago(at) {
    const seconds = Math.round((at - Date.now()) / 1000);
    const rtf = new Intl.RelativeTimeFormat(this._lang, { numeric: "auto" });
    for (const [unit, size] of [["day", 86400], ["hour", 3600], ["minute", 60]]) {
      if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit);
    }
    return rtf.format(seconds, "second");
  }

  _errors(p) {
    return (p.rx_errors || 0) + (p.tx_errors || 0);
  }

  _allMacs(sw) {
    return sw.ports.flatMap((p) => p.macs.map((m) => ({ ...m, port: p })));
  }

  // ---- history -------------------------------------------------------------------------------

  async _loadHistory(sw, port) {
    const key = `${sw.entry_id}:${port.n}`;
    const cached = this._history.get(key);
    if (cached && Date.now() - cached.at < 60000) return;
    this._history.set(key, { ...cached, at: Date.now() });
    try {
      const res = await this._hass.callWS({ type: `${DOMAIN}/history`, entry_id: sw.entry_id, port: port.n });
      this._history.set(key, {
        at: Date.now(),
        t0: res.start * 1000,
        t1: res.end * 1000,
        rx: res.points.map(([t, rx]) => ({ t: t * 1000, v: rx })),
        tx: res.points.map(([t, , tx]) => ({ t: t * 1000, v: tx })),
      });
    } catch {
      this._history.set(key, { at: Date.now(), rx: [], tx: [], t0: Date.now() - 86400000, t1: Date.now() });
    }
    if (this._tab === "overview" && this._sel === port.n) this._render();
  }

  _chart(sw, port) {
    const h = this._history.get(`${sw.entry_id}:${port.n}`);
    const t = this._t;
    if (!h || !h.rx || (!h.rx.length && !h.tx.length)) return `<div class="nodata">${esc(t("noHistory"))}</div>`;
    const max = Math.max(0.01, ...h.rx.map((p) => p.v), ...h.tx.map((p) => p.v)) * 1.15;
    const path = (pts, color) => {
      if (!pts.length) return "";
      const xy = pts.map((p) => `${(Math.max(0, (p.t - h.t0) / (h.t1 - h.t0)) * 300).toFixed(1)},${(60 - (p.v / max) * 56).toFixed(1)}`);
      const last = xy[xy.length - 1].split(",")[0];
      return `<path class="f" fill="${color}" d="M${xy[0].split(",")[0]},60 L${xy.join(" L")} L${last},60 Z"/><path class="l" stroke="${color}" d="M${xy.join(" L")}"/>`;
    };
    return `<svg class="spark" viewBox="0 0 300 60" preserveAspectRatio="none" role="img" aria-label="${esc(t("history"))}">${path(h.rx, "var(--rx)")}${path(h.tx, "var(--tx)")}</svg>`;
  }

  // ---- rendering -----------------------------------------------------------------------------

  _render() {
    const root = this.shadowRoot;
    const active = root.activeElement;
    const focus = active && active.id ? { id: active.id, start: active.selectionStart, end: active.selectionEnd } : null;
    const t = this._t;
    const sw = this._switch;
    if (sw && !sw.ports.some((p) => p.n === this._sel)) this._sel = (sw.ports.find((p) => p.up) || sw.ports[0])?.n ?? null;
    root.innerHTML = `<style>${STYLES}</style>${this._header()}<main class="app">${
      this._error && !this._data ? `<div class="card error">${esc(t("loadError", { e: this._error }))}</div>` : !sw ? `<div class="card empty">${esc(t("noSwitch"))}</div>` : this._switchCard(sw) + this._view(sw)
    }</main>`;
    this._bind();
    if (this._tab === "overview" && sw) {
      const port = sw.ports.find((p) => p.n === this._sel);
      if (port && port.up) this._loadHistory(sw, port);
    }
    if (focus) {
      const el = root.getElementById(focus.id);
      if (el) {
        el.focus();
        if (focus.start != null && el.setSelectionRange) el.setSelectionRange(focus.start, focus.end);
      }
    }
  }

  _header() {
    const t = this._t;
    const tab = (id, label) => `<button class="tab" role="tab" aria-selected="${this._tab === id}" data-a="tab" data-v="${id}">${esc(label)}</button>`;
    return `<header class="topbar"><div class="topbar-in">
      <button class="menu" data-a="menu" aria-label="${esc(t("menu"))}">${icon("menu")}</button>
      <div class="brand"><div class="logo">${icon("lan")}</div>${esc(t("title"))}</div>
      <nav role="tablist">${tab("overview", t("overview"))}${tab("ports", t("ports"))}${tab("devices", t("devices"))}${tab("diag", t("diag"))}</nav>
      <span class="lookwrap">
        <button class="icon-btn" id="lookBtn" data-a="look-toggle" title="${esc(t("lookTitle"))}" aria-label="${esc(t("lookTitle"))}" aria-haspopup="true" aria-expanded="${this._menuOpen}">${icon("palette")}</button>
        ${this._menuOpen ? this._lookMenu() : ""}
      </span>
      <button class="chip outline" data-a="integration">${icon("open")}${esc(t("integration"))}</button>
    </div></header>`;
  }

  _switchCard(sw) {
    const t = this._t;
    const up = sw.ports.filter((p) => p.up).length;
    const rate = sw.ports.reduce((s, p) => s + this._total(p), 0);
    const macs = sw.ports.reduce((s, p) => s + p.macs.length, 0);
    const up_ = this._uptime(sw.uptime);
    const picker =
      this._data.length > 1
        ? `<select class="swpick" data-a="switch" aria-label="${esc(t("switchLabel"))}">${this._data.map((s) => `<option value="${esc(s.entry_id)}" ${s.entry_id === sw.entry_id ? "selected" : ""}>${esc(s.title)}</option>`).join("")}</select>`
        : "";
    const status = sw.last_update_success ? `<span class="on"><span class="dot"></span>${esc(t("connected"))}</span>` : `<span class="off"><span class="dot"></span>${esc(t("unreachable"))}</span>`;
    return `<section class="card"><div class="sw">
      <div class="sw-icon">${icon("lan")}</div>
      <div><div class="sw-name">${esc(sw.title)}</div>
        <div class="sw-meta">${status}<span>${esc(sw.description)}</span><span class="mono">${esc(sw.mac)} · ${esc(sw.host)}</span></div></div>
      <div class="stats">
        <div class="stat"><b>${up}</b> <span>${esc(t("activePorts", { total: sw.ports.length }))}</span><span class="sub">${esc(t("active"))}</span></div>
        <div class="stat"><b>${this._num(rate)}</b> <span>Mbit/s</span><span class="sub">${esc(t("throughput"))}</span></div>
        <div class="stat"><b>${macs}</b> <span>${esc(t("devs"))}</span><span class="sub">${esc(t("devicesLearned"))}</span></div>
        <div class="stat"><b>${up_.big}</b> <span>${esc(up_.unit)}</span><span class="sub">${esc(t("uptime"))}</span></div>
        <div class="stat" style="display:flex;gap:8px;align-items:center">${picker}<button class="chip" data-a="details" aria-expanded="${this._details}">${esc(this._details ? t("detailsOpen") : t("detailsClosed"))}</button></div>
      </div></div>
      ${this._details ? `<div class="details"><div class="kv">
        <div><span>${esc(t("vendor"))}</span><span>${esc(sw.manufacturer || t("noData"))}</span></div><div><span>${esc(t("model"))}</span><span>${esc(sw.model || t("noData"))}</span></div>
        <div><span>${esc(t("poll"))}</span><span>${esc(t("pollValue", { s: sw.interval }))}</span></div><div><span>${esc(t("address"))}</span><span class="mono">${esc(sw.host)}</span></div>
        <div><span>${esc(t("macAddress"))}</span><span class="mono">${esc(sw.mac)}</span></div>
        <div><span>${esc(t("hardware"))}</span><span>${esc(sw.hw_version || t("noData"))}</span></div><div><span>${esc(t("firmware"))}</span><span>${esc(sw.sw_version || t("noData"))}</span></div>
        <div><span>${esc(t("location"))}</span><span>${esc(sw.location || t("noData"))}</span></div><div><span>${esc(t("contact"))}</span><span>${esc(sw.contact || t("noData"))}</span></div></div></div>` : ""}
    </section>`;
  }

  _view(sw) {
    return { overview: () => this._overview(sw), ports: () => this._portsView(sw), devices: () => this._devicesView(sw), diag: () => this._diagView(sw) }[this._tab]();
  }

  _plate(sw) {
    const odd = sw.ports.filter((p) => p.n % 2 === 1);
    const even = sw.ports.filter((p) => p.n % 2 === 0);
    const cols = Math.max(odd.length, even.length);
    const t = this._t;
    const jack = (p) => {
      const speed = p.up ? (p.speed >= 1000 ? "1G" : p.speed >= 100 ? "100M" : "10M") : "";
      return `<button class="port ${this._linkClass(p)} ${this._errors(p) ? "err" : ""} ${p.n === this._sel ? "sel" : ""}" data-a="port" data-v="${p.n}" aria-label="${esc(`${t("port")} ${p.n}, ${this._speedText(p)}`)}" title="${esc(this._portLabel(p))}"><span class="n">${p.n}</span><span class="jack"></span><span class="v">${speed}</span></button>`;
    };
    return `<div class="plate" style="--cols:${cols}"><div class="plate-row">${odd.map(jack).join("")}</div><div class="plate-row">${even.map(jack).join("")}</div></div>`;
  }

  _overview(sw) {
    const t = this._t;
    const live = sw.last_update_success ? `<span class="live"><span class="dot"></span>${esc(t("live"))}</span>` : `<span class="live stale"><span class="dot"></span>${esc(t("stale"))}</span>`;
    const top = sw.ports.filter((p) => p.up && this._total(p) > 0).sort((a, b) => this._total(b) - this._total(a)).slice(0, 5);
    const max = top.length ? this._total(top[0]) : 1;
    const slow = sw.ports.filter((p) => p.up && p.speed > 0 && p.speed < 1000);
    const errs = sw.ports.filter((p) => this._errors(p));
    const day = Date.now() - 86400000;
    const flips = sw.ports.filter((p) => (this._changedAt(sw, p) ?? 0) > day);
    const note = (cls, ic, title, text) => `<div class="issue ${cls}">${icon(ic)}<div><b>${esc(title)}</b><br>${esc(text)}</div></div>`;
    const issues = [
      errs.length ? note("warn", "warn", t("errorPorts", { n: errs.length }), t("errorPortsText", { ports: errs.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      slow.length ? note("warn", "warn", t("slowPorts", { n: slow.length }), t("slowPortsText", { ports: slow.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      flips.length ? note("warn", "warn", t("linkChanges", { n: flips.length }), t("linkChangesText", { ports: flips.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      !errs.length && !slow.length && !flips.length ? note("ok", "ok", t("allFine"), t("allFineText")) : "",
    ].join("");
    return `<section class="card"><div class="card-h"><h2>${esc(t("faceplate"))}</h2>${live}<span class="grow"></span><span class="sub">${esc(t("clickPort"))}</span></div>
      <div class="face">${this._plate(sw)}<div class="legend">
        <span><i style="border-color:var(--g1000);background:color-mix(in srgb,var(--g1000) 28%,transparent)"></i>${esc(t("l1000"))}</span>
        <span><i style="border-color:var(--g100);background:color-mix(in srgb,var(--g100) 28%,transparent)"></i>${esc(t("l100"))}</span>
        <span><i style="border-color:var(--gdown);background:color-mix(in srgb,var(--gdown) 25%,transparent)"></i>${esc(t("noLink"))}</span>
        <span><i style="border:0;border-radius:50%;width:8px;height:8px;background:var(--bad);vertical-align:0"></i>${esc(t("errorsSinceStart"))}</span></div></div></section>
      ${this._detail(sw)}
      <div class="twocol">
        <section class="card"><div class="card-h"><h2>${esc(t("mostLoad"))}</h2><span class="grow"></span><span class="sub">${esc(t("mostLoadSub"))}</span></div>
          <div class="toplist">${top.map((p) => `<div class="toprow"><span>${esc(t("port"))} ${p.n}<span class="sub"> ${esc(this._portLabel(p))}</span></span><span class="b"><i style="width:${(this._total(p) / max) * 100}%"></i></span><span class="mono" style="text-align:right">${this._num(this._total(p))}</span></div>`).join("") || `<span class="sub">${esc(t("noData"))}</span>`}</div></section>
        <section class="card"><div class="card-h"><h2>${esc(t("notes"))}</h2></div><div class="issues">${issues}</div></section>
      </div>`;
  }

  _detail(sw) {
    const t = this._t;
    const p = sw.ports.find((x) => x.n === this._sel);
    if (!p) return "";
    const title = this._editing
      ? `<div class="nameedit"><b>${esc(t("port"))} ${p.n}</b><input id="portname" maxlength="40" value="${esc(p.name)}" placeholder="${esc(t("portName"))}" aria-label="${esc(t("portName"))}"><button class="chip" data-a="save">${esc(t("save"))}</button><button class="chip" data-a="cancel">${esc(t("cancel"))}</button></div>`
      : `<h3>${esc(t("port"))} ${p.n}${p.name ? " · " + esc(p.name) : ""} <button class="rowbtn" data-a="rename" title="${esc(t("rename"))}" aria-label="${esc(t("rename"))}">${icon("edit")}</button>
          <span class="tag ${p.up ? "ok" : ""}">${p.up ? esc(t("link")) + " " + esc(this._speedText(p)) : esc(t("noLink"))}</span>${p.up && p.speed > 0 && p.speed < 1000 ? `<span class="tag warn">${esc(t("only100"))}</span>` : ""}${this._errors(p) ? `<span class="tag bad">${esc(t("errorsN", { n: this._errors(p) }))}</span>` : ""}</h3>`;
    const macs = p.macs.slice(0, MAX_MACS);
    const macList = macs.length
      ? `<div class="maclist">${macs.map((m) => `<div><span>${m.name ? esc(m.name) : `<span class="muted">${esc(t("unknown"))}</span>`}</span><span class="mono muted">${esc(m.mac)}</span></div>`).join("")}${p.macs.length > MAX_MACS ? `<div><span class="muted">${esc(t("moreN", { n: p.macs.length - MAX_MACS }))}</span></div>` : ""}</div>`
      : "";
    return `<section class="card"><div class="pd">
      <div>${title}<div class="sub" style="margin:4px 0 10px">${esc(t("history"))}</div>
        ${p.up ? this._chart(sw, p) : `<div class="nodata">${esc(t("noLink"))}</div>`}
        ${this._changedAt(sw, p) ? `<div class="sub" style="margin-top:6px">${esc(t("linkChangedAgo", { when: this._ago(this._changedAt(sw, p)) }))}</div>` : ""}
        <div class="lg"><span><i style="background:var(--rx)"></i>${esc(t("receive"))} ${this._num(p.rx_rate)} Mbit/s${p.rx_util != null ? ` (${esc(this._util(p.rx_util))})` : ""}</span><span><i style="background:var(--tx)"></i>${esc(t("send"))} ${this._num(p.tx_rate)} Mbit/s${p.tx_util != null ? ` (${esc(this._util(p.tx_util))})` : ""}</span></div></div>
      <div><div class="sub" style="margin-bottom:6px">${esc(p.macs.length ? t("devicesAtPort") + " (" + p.macs.length + ")" : t("noDevices"))}</div>${macList}</div>
    </div></section>`;
  }

  _portsView(sw) {
    const t = this._t;
    const q = this._q.trim().toLowerCase();
    const chip = (id, label) => `<button class="chip" data-a="filter" data-v="${id}" aria-pressed="${this._filter === id}">${esc(label)}</button>`;
    const slow = sw.ports.filter((p) => p.up && p.speed > 0 && p.speed < 1000).length;
    return `<section class="card"><div class="card-h"><h2>${esc(t("ports"))}</h2><span class="live"><span class="dot"></span>${esc(t("live"))}</span></div>
      <div class="tools">${chip("all", t("allPorts"))}${chip("up", t("activeF"))}${chip("down", t("noLinkF"))}${chip("slow", t("slowF"))}${chip("err", t("errF"))}
        <label class="search">${icon("search")}<input id="q" value="${esc(this._q)}" placeholder="${esc(t("searchPorts"))}" aria-label="${esc(t("search"))}"></label></div>
      <div class="infobar"><span id="count"></span><span class="warnnote">${slow ? esc(t("slowNote", { n: slow })) : ""}</span></div>
      <div class="tablewrap"><table><thead><tr><th>${esc(t("port"))}</th><th>${esc(t("status"))}</th><th class="num">${esc(t("speed"))}</th><th class="num">${esc(t("rx"))}</th><th class="num">${esc(t("tx"))}</th><th class="num">${esc(t("errors"))}</th><th>${esc(t("devs"))}</th><th></th></tr></thead><tbody id="ptb"></tbody></table></div>
      <div class="empty" id="pempty" hidden>${esc(t("noPortMatches"))}</div></section>`;
  }

  _fillPorts(sw) {
    const t = this._t;
    const q = this._q.trim().toLowerCase();
    const test = { all: () => true, up: (p) => p.up, down: (p) => !p.up, slow: (p) => p.up && p.speed > 0 && p.speed < 1000, err: (p) => this._errors(p) > 0 }[this._filter];
    const rows = sw.ports.filter(test).filter((p) => !q || `port ${p.n} ${p.name} ${p.macs.map((m) => `${m.name || ""} ${m.mac}`).join(" ")}`.toLowerCase().includes(q));
    const peak = Math.max(1, ...sw.ports.map((p) => Math.max(p.rx_rate || 0, p.tx_rate || 0)));
    const bar = (p, v, color, util) => `<span class="bar" title="${esc(t("utilization"))}: ${esc(this._util(util) || t("noData"))}"><span class="b"><i style="width:${Math.min(100, ((v || 0) / peak) * 100)}%;background:${color}"></i></span><span class="mono">${p.up ? this._num(v) : "–"}</span>${p.up && util != null ? `<span class="sub">${esc(this._util(util))}</span>` : ""}</span>`;
    const shadow = this.shadowRoot;
    shadow.getElementById("ptb").innerHTML = rows
      .map((p) => {
        const names = p.macs.slice(0, 2).map((m) => esc(m.name || m.mac)).join(", ");
        return `<tr class="row ${p.up ? "" : "down"}"><td><span class="pn">${esc(t("port"))} ${p.n}<small>${esc(p.name || (p.up ? "" : t("free")))}</small></span></td>
        <td>${p.up ? `<span class="tag ok">${esc(t("linked"))}</span>` : `<span class="tag">${esc(t("noLink"))}</span>`}</td>
        <td class="num">${p.up ? `<span class="tag ${p.speed < 1000 ? "warn" : ""} mono">${p.speed} Mbit/s</span>` : "–"}</td>
        <td class="num">${bar(p, p.rx_rate, "var(--rx)", p.rx_util)}</td><td class="num">${bar(p, p.tx_rate, "var(--tx)", p.tx_util)}</td>
        <td class="num">${this._errors(p) ? `<span class="tag bad">${this._errors(p)}</span>` : '<span class="muted">0</span>'}</td>
        <td>${p.macs.length ? `<span class="tag acc">${esc(p.macs.length === 1 ? t("oneDevice") : t("nDevices", { n: p.macs.length }))}</span> <span class="sub">${names}${p.macs.length > 2 ? " …" : ""}</span>` : '<span class="muted">–</span>'}</td>
        <td><button class="rowbtn" data-a="goto" data-v="${p.n}" title="${esc(t("showOnOverview"))}" aria-label="${esc(t("showOnOverview"))}">${icon("next")}</button></td></tr>`;
      })
      .join("");
    shadow.getElementById("count").textContent = t("portsOf", { n: rows.length, total: sw.ports.length });
    shadow.getElementById("pempty").hidden = rows.length > 0;
  }

  _devicesView(sw) {
    const t = this._t;
    const chip = (id, label) => `<button class="chip" data-a="dfilter" data-v="${id}" aria-pressed="${this._dfilter === id}">${esc(label)}</button>`;
    return `<section class="card"><div class="card-h"><h2>${esc(t("devicesAtSwitch"))}</h2><span class="grow"></span><span class="sub">${esc(t("devicesHint"))}</span></div>
      <div class="tools">${chip("all", t("all"))}${chip("named", t("named"))}${chip("unknown", t("unknownF"))}
        <label class="search">${icon("search")}<input id="dq" value="${esc(this._dq)}" placeholder="${esc(t("searchDevices"))}" aria-label="${esc(t("search"))}"></label></div>
      <div class="tablewrap"><table><thead><tr><th>${esc(t("device"))}</th><th>${esc(t("mac"))}</th><th>${esc(t("vendor"))}</th><th>${esc(t("port"))}</th></tr></thead><tbody id="dtb"></tbody></table></div>
      <div class="empty" id="dempty" hidden>${esc(t("noDeviceMatches"))}</div></section>`;
  }

  _fillDevices(sw) {
    const t = this._t;
    const q = this._dq.trim().toLowerCase();
    const rows = this._allMacs(sw)
      .filter((d) => this._dfilter === "all" || (this._dfilter === "named" ? d.name : !d.name))
      .filter((d) => !q || `${d.name || ""} ${d.mac} ${d.manufacturer || ""} port ${d.port.n} ${d.port.name}`.toLowerCase().includes(q))
      .sort((a, b) => a.port.n - b.port.n);
    const shadow = this.shadowRoot;
    shadow.getElementById("dtb").innerHTML = rows
      .map((d) => `<tr class="row"><td>${d.name ? esc(d.name) : `<span class="muted">${esc(t("unknown"))}</span>`}</td><td class="mono">${esc(d.mac)}</td><td>${esc(d.manufacturer || "–")}</td>
        <td><span class="tag acc">${esc(t("port"))} ${d.port.n}</span> <span class="sub">${esc(d.port.name)}</span></td></tr>`)
      .join("");
    shadow.getElementById("dempty").hidden = rows.length > 0;
  }

  _diagView(sw) {
    const t = this._t;
    const rows = sw.ports.filter((p) => p.up || this._errors(p));
    return `<section class="card"><div class="card-h"><h2>${esc(t("errorCounters"))}</h2><span class="grow"></span><span class="sub">${esc(t("sinceStart"))}</span></div>
      <div class="tablewrap"><table><thead><tr><th>${esc(t("port"))}</th><th class="num">${esc(t("rxErrors"))}</th><th class="num">${esc(t("txErrors"))}</th><th class="num">${esc(t("rxDiscards"))}</th><th class="num">${esc(t("txDiscards"))}</th><th class="num">${esc(t("rxTotal"))}</th><th class="num">${esc(t("txTotal"))}</th><th>${esc(t("assessment"))}</th></tr></thead><tbody>
      ${rows.map((p) => `<tr class="row"><td><span class="pn">${esc(t("port"))} ${p.n}<small>${esc(p.name)}</small></span></td><td class="num mono">${p.rx_errors}</td><td class="num mono">${p.tx_errors}</td><td class="num mono">${p.rx_discards}</td><td class="num mono">${p.tx_discards}</td><td class="num mono">${esc(this._bytes(p.rx_bytes))}</td><td class="num mono">${esc(this._bytes(p.tx_bytes))}</td>
        <td>${this._errors(p) > 5 ? `<span class="tag warn">${esc(t("check"))}</span>` : `<span class="tag">${esc(t("fine"))}</span>`}</td></tr>`).join("")}
      </tbody></table></div></section>`;
  }

  // ---- events --------------------------------------------------------------------------------

  // The listeners sit on the shadow root once; the content below it is replaced on every render.
  _listen() {
    const root = this.shadowRoot;
    root.addEventListener("click", (event) => {
      // a click outside the open appearance menu closes it
      const outside = this._menuOpen && !event.composedPath().some((n) => n.classList?.contains("lookwrap"));
      if (outside) this._menuOpen = false;
      const el = event.target.closest("[data-a]");
      if (!el) {
        if (outside) this._render();
        return;
      }
      const v = el.dataset.v;
      switch (el.dataset.a) {
        case "look-toggle": this._menuOpen = !this._menuOpen; break;
        case "look": this._setLook({ [el.dataset.kind]: v }); break;
        case "tab": this._tab = v; this._editing = false; break;
        case "menu":
          this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
          if (outside) this._render();
          return;
        case "integration":
          history.pushState(null, "", `/config/integrations/integration/${DOMAIN}`);
          window.dispatchEvent(new CustomEvent("location-changed"));
          return;
        case "details": this._details = !this._details; break;
        case "port": this._sel = +v; this._editing = false; break;
        case "goto": this._sel = +v; this._tab = "overview"; this._editing = false; break;
        case "filter": this._filter = v; break;
        case "dfilter": this._dfilter = v; break;
        case "rename": this._editing = true; break;
        case "cancel": this._editing = false; break;
        case "save": this._saveName(); return;
        default:
          if (outside) this._render();
          return;
      }
      this._render();
    });
    root.addEventListener("change", (event) => {
      if (event.target.dataset?.a === "switch") {
        this._entry = event.target.value;
        this._sel = null;
        this._render();
      }
    });
    root.addEventListener("input", (event) => {
      const sw = this._switch;
      if (!sw) return;
      if (event.target.id === "q") {
        this._q = event.target.value;
        this._fillPorts(sw);
      } else if (event.target.id === "dq") {
        this._dq = event.target.value;
        this._fillDevices(sw);
      }
    });
    root.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && this._menuOpen) {
        this._menuOpen = false;
        this._render();
        this.shadowRoot.getElementById("lookBtn")?.focus();
        return;
      }
      if (event.target.id !== "portname") return;
      if (event.key === "Enter") this._saveName();
      if (event.key === "Escape") {
        this._editing = false;
        this._render();
      }
    });
  }

  _bind() {
    const sw = this._switch;
    if (sw && this._tab === "ports") this._fillPorts(sw);
    if (sw && this._tab === "devices") this._fillDevices(sw);
    if (this._editing) this.shadowRoot.getElementById("portname")?.focus();
  }

  async _saveName() {
    const sw = this._switch;
    const input = this.shadowRoot.getElementById("portname");
    if (!sw || !input) return;
    try {
      await this._hass.callWS({ type: `${DOMAIN}/set_port_name`, entry_id: sw.entry_id, port: this._sel, name: input.value });
    } catch (err) {
      this._error = err?.message || String(err);
    }
    this._editing = false;
    await this._load();
  }
}

customElements.define("tplink-switch-panel", TplinkSwitchPanel);
