// Sidebar panel "Switch": a plain web component without a build step. It reads the websocket
// commands of the integration (websocket_api.py) and the history of the port rate sensors.
// Its parts are loaded with the query string of this file, so an update loads every part new.
const V = new URL(import.meta.url).search;
// The parts are loaded without a top-level await: Home Assistant creates the element as soon as this
// module has run, so the element has to be defined at once or the first visit stays blank.
let STYLES, translator, csvNumber, csvText, applyAppearance, cleanPrefs, DEFAULTS, MODES, SCHEMES, SIZES, tokens;
let loaded = false;
let loadError = null;
const ready = Promise.all([import(`./styles.js${V}`), import(`./texts.js${V}`), import(`./theme.js${V}`), import(`./csv.js${V}`)]).then(
  ([styles, texts, theme, csv]) => {
    ({ STYLES } = styles);
    ({ translator } = texts);
    ({ applyAppearance, cleanPrefs, DEFAULTS, MODES, SCHEMES, SIZES, tokens } = theme);
    ({ csvNumber, csvText } = csv);
    loaded = true;
  },
  (err) => {
    // Without its parts the panel cannot work; say so instead of staying blank.
    console.error("tplink_switch_snmp: the panel could not load its parts", err);
    loadError = err;
  },
);

const DOMAIN = "tplink_switch_snmp";
const LOOK_KEY = "tplink_switch_snmp_look";
// The server pushes every poll. This slow check only matters if the subscription is lost.
const FALLBACK_MS = 60000;
const STALE_MS = 5 * 60000;
const MAX_MACS = 50;
const WOBBLE = 3; // link changes in 24 hours from which a port counts as unstable
const BROADCAST_STORM = 500; // broadcast packets per second that look like a loop

// Material Design Icons (Apache 2.0)
const ICON = {
  download: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
  palette: "M12,3A9,9 0 0,0 3,12A9,9 0 0,0 12,21A1.5,1.5 0 0,0 13.5,19.5C13.5,19.11 13.35,18.76 13.11,18.5C12.88,18.23 12.75,17.88 12.75,17.5A1.5,1.5 0 0,1 14.25,16H16A5,5 0 0,0 21,11C21,6.58 16.97,3 12,3M6.5,12A1.5,1.5 0 0,1 5,10.5A1.5,1.5 0 0,1 6.5,9A1.5,1.5 0 0,1 8,10.5A1.5,1.5 0 0,1 6.5,12M9.5,8A1.5,1.5 0 0,1 8,6.5A1.5,1.5 0 0,1 9.5,5A1.5,1.5 0 0,1 11,6.5A1.5,1.5 0 0,1 9.5,8M14.5,8A1.5,1.5 0 0,1 13,6.5A1.5,1.5 0 0,1 14.5,5A1.5,1.5 0 0,1 16,6.5A1.5,1.5 0 0,1 14.5,8M17.5,12A1.5,1.5 0 0,1 16,10.5A1.5,1.5 0 0,1 17.5,9A1.5,1.5 0 0,1 19,10.5A1.5,1.5 0 0,1 17.5,12Z",
  lan: "M10,2C8.89,2 8,2.89 8,4V7C8,8.11 8.89,9 10,9H11V11H2V13H6V15H5C3.89,15 3,15.89 3,17V20C3,21.11 3.89,22 5,22H9C10.11,22 11,21.11 11,20V17C11,15.89 10.11,15 9,15H8V13H16V15H15C13.89,15 13,15.89 13,17V20C13,21.11 13.89,22 15,22H19C20.11,22 21,21.11 21,20V17C21,15.89 20.11,15 19,15H18V13H22V11H13V9H14C15.11,9 16,8.11 16,7V4C16,2.89 15.11,2 14,2H10Z",
  search: "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",
  open: "M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z",
  menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
  warn: "M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z",
  info: "M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
  ok: "M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M10,17L5,12L6.41,10.58L10,14.17L17.59,6.58L19,8L10,17Z",
  next: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
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
    this._t = null;
    this._lang = "";
    this._started = false;
    this._pending = false;
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
    this._notice = null;
    this._history = new Map(); // port and range -> {at, rx, tx}
    this._range = "24h";
    this._plots = {};
    this._timer = null;
    this._loading = false;
    this._unsub = null;
    this._subscribing = false;
    this._sort = { ports: { key: "n", dir: 1 }, devices: { key: "port", dir: 1 }, diag: { key: "n", dir: 1 } };
    this._look = null;
    this._lookKey = null;
    this._menuOpen = false;
    this._navOpen = false; // the tabs in the burger menu of a narrow screen
    this._lastData = 0;
    this._tipPort = null;
    this._reveal = false; // scroll the port card into view after the next draw
    this._adopt();
  }

  // Home Assistant may have set a property before the element was defined: it then sits on the
  // object itself and hides the setter, so it is handed to the setter again.
  _adopt() {
    for (const key of ["hass", "narrow", "panel"]) {
      if (Object.prototype.hasOwnProperty.call(this, key)) {
        const value = this[key];
        delete this[key];
        this[key] = value;
      }
    }
  }

  set hass(hass) {
    this._hass = hass;
    if (!loaded) {
      // the parts are still loading (first visit): start as soon as they are there
      if (!this._pending) {
        this._pending = true;
        ready.then(() => {
          this._pending = false;
          if (loadError) {
            this.textContent = `Switch panel: could not load its files (${loadError?.message || loadError}). Reload the page with Ctrl+Shift+R.`;
            this.style.cssText = "display:block;padding:24px;font:14px sans-serif;color:var(--primary-text-color)";
          } else if (this._hass) {
            this.hass = this._hass;
            if (this.isConnected) this._load();
          }
        });
      }
      return;
    }
    const first = !this._started;
    this._started = true;
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
    if (first) {
      // menu and tabs stand at once; the data follow
      this._render();
      this._load();
    }
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
      // right after the start the connection may not be ready: try again soon
      if (!this._data) setTimeout(() => this._load(), 3000);
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
    const key = `${sw.entry_id}:${port.n}:${this._range}`;
    const cached = this._history.get(key);
    if (cached && Date.now() - cached.at < 60000) return;
    this._history.set(key, { ...cached, at: Date.now() });
    try {
      const res = await this._hass.callWS({ type: `${DOMAIN}/history`, entry_id: sw.entry_id, port: port.n, range: this._range });
      this._history.set(key, {
        at: Date.now(),
        t0: res.start * 1000,
        t1: res.end * 1000,
        rx: res.points.map(([t, rx]) => ({ t: t * 1000, v: rx })),
        tx: res.points.map(([t, , tx]) => ({ t: t * 1000, v: tx })),
        link: res.link || null,
      });
    } catch {
      this._history.set(key, { at: Date.now(), rx: [], tx: [], t0: Date.now() - 86400000, t1: Date.now() });
    }
    if (this._tab === "overview" && this._sel === port.n) this._render();
  }

  // the rates of the whole switch, the active ports and the learned MAC addresses over 24 h,
  // 7 days and 30 days, for the charts in the tiles
  async _loadSummary(sw) {
    const cached = this._summary?.get(sw.entry_id);
    if (cached && Date.now() - cached.at < 60000) return;
    this._summary ||= new Map();
    this._summary.set(sw.entry_id, { ...cached, at: Date.now() });
    let data = {};
    try {
      data = await this._hass.callWS({ type: `${DOMAIN}/history_summary`, entry_id: sw.entry_id });
    } catch { /* the tiles show no charts */ }
    this._summary.set(sw.entry_id, { at: Date.now(), data });
    if (this._tab === "overview") this._render();
  }

  // A chart with a cursor: series is [{color, pts: [{t, v}]}], the same time axis for all plots.
  // The plot is remembered by id so that the pointer over any plot shows the same time in all.
  _plot(id, series, t0, t1, bucket, { height = 52, zero = true, fmt, cls = "" }) {
    const all = series.flatMap((s) => s.pts.map((p) => p.v));
    if (!all.length) return `<div class="nodata" style="height:${height}px">${esc(this._t("noHistory"))}</div>`;
    let lo = zero ? 0 : Math.min(...all);
    let hi = Math.max(...all);
    if (!zero) {
      const pad = (hi - lo) * 0.15 || 1;
      lo -= pad;
      hi += pad;
    } else hi = Math.max(0.01, hi) * 1.15;
    const x = (t) => Math.min(1, Math.max(0, (t - t0) / (t1 - t0)));
    const y = (v) => 1 - (v - lo) / (hi - lo);
    const paths = series.map((s) => {
      if (!s.pts.length) return "";
      const xy = s.pts.map((p) => `${(x(p.t) * 300).toFixed(1)},${(2 + y(p.v) * (height - 4)).toFixed(1)}`);
      const first = xy[0].split(",")[0];
      const last = xy[xy.length - 1].split(",")[0];
      return `<path class="f" fill="${s.color}" d="M${first},${height} L${xy.join(" L")} L${last},${height} Z"/><path class="l" stroke="${s.color}" d="M${xy.join(" L")}"/>`;
    }).join("");
    this._plots[id] = { t0, t1, bucket, height, fmt, lo, hi, series };
    const dots = series.map((s) => `<b class="pdot" style="background:${s.color}"></b>`).join("");
    return `<div class="plot ${cls}" data-p="${id}"><svg class="spark" style="height:${height}px" viewBox="0 0 300 ${height}" preserveAspectRatio="none" role="img" aria-label="${esc(this._t(id === "port" ? this._rangeKey() : "statRange"))}">${paths}</svg><i class="pcur"></i>${dots}<div class="ptip"></div></div>`;
  }

  _rangeKey() { return { "24h": "history", "7d": "history7d", "30d": "history30d" }[this._range]; }

  _when(ms) {
    const d = new Date(ms);
    const lang = this._hass?.locale?.language;
    const time = d.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" });
    return this._range === "24h" ? time : `${d.toLocaleDateString(lang, { day: "2-digit", month: "2-digit" })}, ${time}`;
  }

  // Shows the cursor at the time under the pointer (or hides it); x is a share of the width.
  _hoverAt(source, share) {
    const root = this.shadowRoot;
    const src = this._plots[source];
    const time = share == null || !src ? null : src.t0 + share * (src.t1 - src.t0);
    root.querySelectorAll(".plot[data-p]").forEach((el) => {
      const plot = this._plots[el.dataset.p];
      const cur = el.querySelector(".pcur");
      const tip = el.querySelector(".ptip");
      const dots = el.querySelectorAll(".pdot");
      const hide = () => { cur.style.display = tip.style.display = "none"; dots.forEach((d) => (d.style.display = "none")); };
      if (!plot || time == null) return hide();
      const near = plot.series.map((s) => s.pts.reduce((best, p) => (best == null || Math.abs(p.t - time) < Math.abs(best.t - time) ? p : best), null));
      const first = near[0];
      if (!first || Math.abs(first.t - time) > plot.bucket * 1.5) return hide();
      const w = el.clientWidth;
      const px = Math.min(1, Math.max(0, (first.t - plot.t0) / (plot.t1 - plot.t0))) * w;
      cur.style.display = tip.style.display = "block";
      cur.style.left = `${px}px`;
      near.forEach((p, i) => {
        if (!p) { dots[i].style.display = "none"; return; }
        dots[i].style.display = "block";
        dots[i].style.left = `${px}px`;
        dots[i].style.top = `${2 + (1 - (p.v - plot.lo) / (plot.hi - plot.lo)) * (plot.height - 4)}px`;
      });
      tip.innerHTML = `<span>${esc(this._when(first.t))}</span> ${near.map((p) => (p ? esc(plot.fmt(p.v)) : "")).join(" · ")}`;
      const half = tip.offsetWidth / 2;
      tip.style.left = `${Math.max(half, Math.min(w - half, px))}px`;
    });
  }

  _chart(sw, port) {
    const h = this._history.get(`${sw.entry_id}:${port.n}:${this._range}`);
    const t = this._t;
    if (!h || !h.rx || (!h.rx.length && !h.tx.length)) return `<div class="nodata">${esc(t("noHistory"))}</div>`;
    const bucket = this._bucket();
    const fmt = (v) => `${this._num(v)} Mbit/s`;
    return this._plot("port", [{ color: "var(--rx)", pts: h.rx }, { color: "var(--tx)", pts: h.tx }], h.t0, h.t1, bucket, {
      height: 96,
      fmt,
      cls: "big",
    });
  }

  _bucket() { return { "24h": 300, "7d": 3600, "30d": 7200 }[this._range] * 1000; }

  // ---- rendering -----------------------------------------------------------------------------

  _render() {
    if (!this._started) return; // the parts are not loaded yet
    try {
      this._draw();
    } catch (err) {
      // a failure in drawing must not leave the panel blank
      console.error("tplink_switch_snmp: the panel could not be drawn", err);
      this.shadowRoot.innerHTML = `<style>${STYLES}</style><main class="app"><div class="card error">${esc(this._t("loadError", { e: err?.message || String(err) }))}</div></main>`;
    }
  }

  _draw() {
    const root = this.shadowRoot;
    const active = root.activeElement;
    const focus = active && active.id ? { id: active.id, start: active.selectionStart, end: active.selectionEnd } : null;
    const t = this._t;
    const sw = this._switch;
    if (sw && !sw.ports.some((p) => p.n === this._sel)) this._sel = null; // no port is chosen until one is clicked
    root.innerHTML = `<style>${STYLES}</style>${this._header()}<div class="tip" id="tip" role="tooltip" hidden></div><main class="app">${
      this._error && !this._data ? `<div class="card error">${esc(t("loadError", { e: this._error }))}</div>` : !this._data ? `<div class="card empty">${esc(t("loading"))}</div>` : !sw ? `<div class="card empty">${esc(t("noSwitch"))}</div>` : this._switchCard(sw) + this._view(sw)
    }</main>`;
    this._bind();
    this._showTip();
    if (this._tab === "overview" && sw) {
      const port = sw.ports.find((p) => p.n === this._sel);
      if (port) this._loadHistory(sw, port); // also without a link: the band shows when it was there
    }
    if (this._reveal) {
      this._reveal = false;
      root.getElementById("portcard")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    if (focus) {
      const el = root.getElementById(focus.id);
      if (el) {
        el.focus();
        if (focus.start != null && el.setSelectionRange) el.setSelectionRange(focus.start, focus.end);
      }
    }
  }

  // ---- tooltip of a port ---------------------------------------------------------------------

  // What is known about a port, shown when the pointer or the keyboard focus is on its tile.
  _tipHtml(sw, p) {
    const t = this._t;
    const rate = (label, value, util, color) =>
      `<div class="tip-rate"><i style="background:${color}"></i><span>${esc(label)}</span><b class="mono">${p.up ? this._num(value) : "–"} Mbit/s</b><span class="sub">${p.up && util != null ? esc(this._util(util)) : ""}</span></div>`;
    const tags = [
      `<span class="tag ${p.up ? "ok" : ""}">${esc(p.up ? this._speedText(p) : t("noLink"))}</span>`,
      p.admin_up === false ? `<span class="tag bad">${esc(t("switchedOff"))}</span>` : "",
      this._fixed(p) ? `<span class="tag warn">${esc(t("fixedMode", { mode: t("mode_" + p.mode) }))}</span>` : "",
      this._secFull(p) ? `<span class="tag warn">${esc(t("secFull"))}</span>` : "",
      this._stpBlocked(p) ? `<span class="tag warn">${esc(t("stp_" + p.stp_state))}</span>` : "",
      p.mirror ? `<span class="tag warn">${esc(t("mirror_" + p.mirror))}</span>` : "",
      p.isolated ? `<span class="tag">${esc(t("isolated"))}</span>` : "",
      p.lag ? `<span class="tag">${esc(t("lagN", { lag: p.lag }))}</span>` : "",
      p.loop ? `<span class="tag bad">${esc(t(p.loop_blocked ? "loopBlocked" : "loopFound"))}</span>` : "",
      p.up && p.speed > 0 && p.speed < 1000 ? `<span class="tag warn">${esc(t("only100"))}</span>` : "",
      (p.link_changes || 0) >= WOBBLE ? `<span class="tag warn">${esc(t("linkCount", { n: p.link_changes }))}</span>` : "",
      this._errors(p) ? `<span class="tag bad">${esc(t.count("errorsN", this._errors(p)))}</span>` : "",
    ].join("");
    const when = this._changedAt(sw, p);
    const shown = p.macs.slice(0, 4);
    const devices = shown.length
      ? `<div class="tip-devs">${shown.map((m) => `<div><span>${m.name ? esc(m.name) : `<span class="muted">${esc(t("unknown"))}</span>`}</span><span class="mono muted">${esc(m.mac)}</span></div>`).join("")}${p.macs.length > shown.length ? `<div class="muted">${esc(t("moreN", { n: p.macs.length - shown.length }))}</div>` : ""}</div>`
      : `<div class="sub">${esc(t("noDevices"))}</div>`;
    return `<div class="tip-h"><b>${esc(t("port"))} ${p.n}</b>${p.name ? `<span class="muted"> · ${esc(p.name)}</span>` : ""}</div>
      <div class="tip-tags">${tags}</div>
      ${p.up ? rate(t("receive"), p.rx_rate, p.rx_util, "var(--rx)") + rate(t("send"), p.tx_rate, p.tx_util, "var(--tx)") : ""}
      ${this._settings(p)}
      ${when ? `<div class="sub">${esc(t("linkChangedAgo", { when: this._ago(when) }))}</div>` : ""}
      <div class="tip-sep"></div>${devices}`;
  }

  // Fills the tooltip for the port under the pointer and puts it above the tile, or below it
  // when there is no room; it is called again after every draw because that replaces the content.
  _showTip() {
    const tip = this.shadowRoot.getElementById("tip");
    const sw = this._switch;
    const tile = this._tipPort != null ? this.shadowRoot.querySelector(`.port[data-v="${this._tipPort}"]`) : null;
    const port = sw?.ports.find((p) => p.n === this._tipPort);
    if (!tip || !tile || !port) {
      if (tip) tip.hidden = true;
      return;
    }
    tip.innerHTML = this._tipHtml(sw, port);
    tip.hidden = false;
    const r = tile.getBoundingClientRect();
    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    const left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    const top = r.top - h - 8 >= 8 ? r.top - h - 8 : r.bottom + 8;
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
  }

  _setTip(number) {
    if (this._tipPort === number) return;
    this._tipPort = number;
    this._showTip();
  }

  _header() {
    const t = this._t;
    const tab = (id, label) => `<button class="tab" role="tab" aria-selected="${this._tab === id}" data-a="tab" data-v="${id}">${esc(label)}</button>`;
    return `<header class="topbar"><div class="topbar-in">
      <button class="menu" data-a="menu" aria-label="${esc(t("menu"))}">${icon("menu")}</button>
      <div class="brand"><div class="logo">${icon("lan")}</div>${esc(t("title"))}</div>
      <button class="burger" data-a="nav-toggle" aria-label="${esc(t("tabsMenu"))}" aria-expanded="${this._navOpen}">${icon("menu")}</button>
      <div class="navwrap${this._navOpen ? " open" : ""}"><nav role="tablist">${tab("overview", t("overview"))}${tab("ports", t("ports"))}${tab("devices", t("devices"))}${tab("diag", t("diag"))}${tab("config", t("config"))}</nav>
      <span class="lookwrap">
        <button class="icon-btn" id="lookBtn" data-a="look-toggle" title="${esc(t("lookTitle"))}" aria-label="${esc(t("lookTitle"))}" aria-haspopup="true" aria-expanded="${this._menuOpen}">${icon("palette")}<span class="btnlabel">${esc(t("lookTitle"))}</span></button>
        ${this._menuOpen ? this._lookMenu() : ""}
      </span>
      <button class="chip outline" data-a="integration">${icon("open")}${esc(t("integration"))}</button>
      </div>
    </div></header>`;
  }

  _switchCard(sw) {
    const t = this._t;
    const picker =
      this._data.length > 1
        ? `<select class="swpick" data-a="switch" aria-label="${esc(t("switchLabel"))}">${this._data.map((s) => `<option value="${esc(s.entry_id)}" ${s.entry_id === sw.entry_id ? "selected" : ""}>${esc(s.title)}</option>`).join("")}</select>`
        : "";
    const status = sw.last_update_success ? `<span class="on"><span class="dot"></span>${esc(t("connected"))}</span>` : `<span class="off"><span class="dot"></span>${esc(t("unreachable"))}</span>`;
    return `<section class="card"><div class="sw">
      <div class="sw-icon">${icon("lan")}</div>
      <div><div class="sw-name">${esc(sw.title)}</div>
        <div class="sw-meta">${status}<span>${esc(sw.description)}</span><span class="mono">${esc(sw.mac)} · ${esc(sw.host)}</span></div></div>
      <div class="sw-actions">${picker}<button class="chip" data-a="details" aria-expanded="${this._details}">${esc(this._details ? t("detailsOpen") : t("detailsClosed"))}</button></div>
      </div>
      ${this._details ? `<div class="details"><div class="kv">
        <div><span>${esc(t("vendor"))}</span><span>${esc(sw.manufacturer || t("noData"))}</span></div><div><span>${esc(t("model"))}</span><span>${esc(sw.model || t("noData"))}</span></div>
        <div><span>${esc(t("poll"))}</span><span>${esc(t("pollValue", { s: sw.interval }))}</span></div><div><span>${esc(t("address"))}</span><span class="mono">${esc(sw.host)}</span></div>
        <div><span>${esc(t("macAddress"))}</span><span class="mono">${esc(sw.mac)}</span></div>
        <div><span>${esc(t("hardware"))}</span><span>${esc(sw.hw_version || t("noData"))}</span></div><div><span>${esc(t("firmware"))}</span><span>${esc(sw.sw_version || t("noData"))}</span></div>
        <div><span>${esc(t("location"))}</span><span>${esc(sw.location || t("noData"))}</span></div><div><span>${esc(t("contact"))}</span><span>${esc(sw.contact || t("noData"))}</span></div></div></div>` : ""}
    </section>`;
  }

  _view(sw) {
    return { overview: () => this._overview(sw), ports: () => this._portsView(sw), devices: () => this._devicesView(sw), diag: () => this._diagView(sw), config: () => this._configView(sw) }[this._tab]();
  }

  // The switch as it looks from the front: a dark housing, the sockets in groups of four in two
  // rows (odd ports above, even ports below, as on the device) and the LEDs of each port.
  _plate(sw) {
    const odd = sw.ports.filter((p) => p.n % 2 === 1);
    const even = sw.ports.filter((p) => p.n % 2 === 0);
    const t = this._t;
    const jack = (p) => {
      const speed = p.up ? (p.speed >= 1000 ? "1G" : p.speed >= 100 ? "100M" : "10M") : "";
      const sel = p.n === this._sel;
      return `<button class="port ${this._linkClass(p)} ${this._errors(p) ? "err" : ""} ${sel ? "sel" : ""}" data-a="port" data-v="${p.n}" aria-pressed="${sel}" aria-label="${esc(`${t("port")} ${p.n}, ${this._speedText(p)}`)}"><span class="n">${p.n}</span><span class="rj"><i class="led link"></i><i class="led act ${p.up && this._total(p) > 0 ? "on" : ""}"></i></span><span class="v">${speed}</span></button>`;
    };
    const row = (ports) => {
      const groups = [];
      for (let i = 0; i < ports.length; i += 4) groups.push(`<div class="grp">${ports.slice(i, i + 4).map(jack).join("")}</div>`);
      return `<div class="plate-row">${groups.join("")}</div>`;
    };
    const upt = this._uptime(sw.uptime);
    return `<div class="chassis"><div class="badge-plate"><b>${esc(sw.manufacturer || t("title"))}</b><span>${esc(sw.model || sw.title)}</span><span class="upt">${esc(t("uptime"))} <em>${esc(`${upt.big} ${upt.unit}`)}</em></span><div class="leds"><i class="led ${sw.last_update_success ? "on" : "red"}"></i>${esc(t("ledPower"))}</div></div><div class="plate">${row(odd)}${row(even)}</div></div>`;
  }

  // errors and slow links as chips below the picture: green when there are none, else with the ports
  _status(sw) {
    const t = this._t;
    const errs = sw.ports.filter((p) => this._errors(p));
    const slow = sw.ports.filter((p) => p.up && p.speed > 0 && p.speed < 1000);
    const list = (ps) => ps.map((p) => p.n).join(", ");
    const chip = (cls, text) => `<span class="tag ${cls}"><i class="dot"></i>${text}</span>`;
    return `<div class="statusline">${errs.length ? chip("bad", `<b>${esc(t.count("errorPorts", errs.length))}</b>: ${esc(list(errs))}`) : chip("ok", esc(t("noErrors")))}${slow.length ? chip("warn", `<b>${esc(t.count("slowPortsShort", slow.length))}</b>: ${esc(list(slow))}`) : ""}</div>`;
  }

  // the numbers of the whole switch, below its picture; three of them with a chart of the period
  _stats(sw) {
    const t = this._t;
    const up = sw.ports.filter((p) => p.up).length;
    const rx = sw.ports.reduce((s, p) => s + (p.rx_rate || 0), 0);
    const tx = sw.ports.reduce((s, p) => s + (p.tx_rate || 0), 0);
    const macs = sw.ports.reduce((s, p) => s + p.macs.length, 0);
    this._loadSummary(sw);
    this._plots = {};
    const range = this._summary?.get(sw.entry_id)?.data?.[this._range];
    const chart = (id, kind, color, opts) => {
      if (!range) return "";
      const pts = range[kind].map(([at, ...v]) => ({ t: at * 1000, v: v.reduce((a, b) => a + b, 0) }));
      const values = pts.map((p) => p.v);
      const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
      const stat = (label, value) => `<span>${esc(label)} <b>${esc(value)}</b></span>`;
      const foot = !values.length ? "" : opts.peak
        ? `${stat(t("avg"), this._num(avg))}${stat(t("peak"), `${this._num(Math.max(...values))} Mbit/s`)}`
        : `${stat(t("statMin"), this._num(Math.min(...values), 0))}${stat(t("avg"), this._num(avg, 1))}${stat(t("statMax"), this._num(Math.max(...values), 0))}`;
      return `${this._plot(id, [{ color, pts }], range.start * 1000, range.end * 1000, range.bucket * 1000, { zero: !!opts.peak, fmt: opts.fmt })}
        <div class="ax"><span>${esc(t(`ago${this._range}`))}</span><span>${esc(t("now"))}</span></div><div class="k">${foot}</div>`;
    };
    const tile = (label, big, unit, extra = "", cls = "", plot = "") => `<div class="tile ${cls}"><span class="lbl">${esc(label)}</span><span class="big">${big}${unit ? ` <small>${esc(unit)}</small>` : ""}</span>${extra ? `<span class="sub">${extra}</span>` : ""}${plot}</div>`;
    const picker = `<div class="rangebar" role="group" aria-label="${esc(t("statRange"))}"><span class="sub">${esc(t("statRange"))}</span>${["24h", "7d", "30d"].map((r) => `<button class="chip small" data-a="range" data-v="${r}" aria-pressed="${this._range === r}">${esc(t(`range${r}`))}</button>`).join("")}</div>`;
    return `${picker}<div class="statgrid">${[
      tile(`${t("ports")} ${t("active")}`, up, t("activePorts", { total: sw.ports.length }), "", "", chart("active", "active", "var(--rx)", { fmt: (v) => `${Math.round(v)} ${t("activeShort")}` })),
      tile(t("throughput"), this._num(rx + tx), "Mbit/s", `${esc(t("receive"))} ${this._num(rx)} · ${esc(t("send"))} ${this._num(tx)}`, "", chart("throughput", "throughput", "var(--g1000)", { peak: true, fmt: (v) => `${this._num(v)} Mbit/s` })),
      tile(t("devicesLearned"), macs, t("devs"), "", "", chart("macs", "macs", "var(--tx)", { fmt: (v) => `${Math.round(v)} ${t("devs")}` })),
    ].join("")}</div>`;
  }

  // the RMON counters that are not zero, as "CRC 5 · Kollisionen 2"; oversize packets are
  // well formed (jumbo frames, VLAN tags) and so no error: the sensor has them, the card does not
  _detailText(p) {
    const t = this._t;
    return Object.entries(p.error_details || {})
      .filter(([kind, n]) => n > 0 && kind !== "oversize_packets")
      .map(([kind, n]) => `${t("err_" + kind)} ${n}`)
      .join(" · ");
  }

  // what the numbers point to: collisions mean a duplex mismatch, the rest a bad cable
  _assess(p) {
    const d = p.error_details || {};
    if ((d.collisions || 0) > 0) return "checkDuplex";
    if ((d.crc_errors || 0) + (d.fragments || 0) + (d.jabbers || 0) > 0) return "checkCable";
    return "check";
  }

  // "128 kbit/s" or "10 Mbit/s"
  _kbit(k) {
    return k >= 1000 ? `${k / 1000} Mbit/s` : `${k} kbit/s`;
  }

  // lines for the tooltip about what is set at the switch: flow control, port security, storm control
  _settings(p) {
    const t = this._t;
    const lines = [];
    const detail = this._detailText(p);
    if (detail) lines.push(detail);
    if (p.pvid != null) {
      const list = (v) => v.join(", ");
      const parts = [`PVID ${p.pvid}`];
      if (p.vlans_untagged?.length) parts.push(`${t("vlanUntagged")} ${list(p.vlans_untagged)}`);
      if (p.vlans_tagged?.length) parts.push(`${t("vlanTagged")} ${list(p.vlans_tagged)}`);
      lines.push(`VLAN: ${parts.join(" · ")}`);
    }
    const igmp = Object.entries(p.igmp || {}).filter(([, n]) => n > 0).map(([kind, n]) => `${t("igmp_" + kind)} ${n}`);
    if (igmp.length) lines.push(`IGMP: ${igmp.join(" · ")}`);
    else if (p.igmp_snooping) lines.push(t("igmpOn"));
    if (p.isolated && p.isolation_forward?.length) lines.push(t("isolatedTo", { ports: p.isolation_forward.join(", ") }));
    if (p.qos_priority) lines.push(t("qosPriority", { n: p.qos_priority }));
    if (p.flow_control) lines.push(t("flowOn"));
    if (p.dhcp_trusted) lines.push(t("dhcpTrusted"));
    if (p.arp_trusted) lines.push(t("arpTrusted"));
    if (p.arp_illegal > 0) lines.push(t("arpIllegal", { n: p.arp_illegal }));
    if (p.security_max != null) lines.push(t("secCount", { n: p.security_learned ?? "–", max: p.security_max }));
    const storm = Object.entries(p.storm || {}).map(([kind, k]) => `${t("storm_" + kind)} ${this._kbit(k)}`);
    if (storm.length) lines.push(`${t("stormLimit")}: ${storm.join(", ")}`);
    return lines.map((l) => `<div class="sub">${esc(l)}</div>`).join("");
  }

  // port security is on and the port cannot learn another address
  _secFull(p) {
    return p.security_max != null && p.security_learned != null && p.security_learned >= p.security_max;
  }

  // a port with a cable that the spanning tree does not use (yet): not forwarding
  _stpBlocked(p) {
    return p.up && !!p.stp_state && !["forwarding", "disabled"].includes(p.stp_state);
  }

  // a port that is set to a fixed speed and not to auto negotiation
  _fixed(p) {
    return !!p.mode && p.mode !== "auto";
  }

  _overview(sw) {
    const t = this._t;
    const live = sw.last_update_success ? `<span class="live"><span class="dot"></span>${esc(t("live"))}</span>` : `<span class="live stale"><span class="dot"></span>${esc(t("stale"))}</span>`;
    const top = sw.ports.filter((p) => p.up && this._total(p) > 0).sort((a, b) => this._total(b) - this._total(a)).slice(0, 5);
    const max = top.length ? this._total(top[0]) : 1;
    const slow = sw.ports.filter((p) => p.up && p.speed > 0 && p.speed < 1000);
    const errs = sw.ports.filter((p) => this._errors(p));
    const loud = sw.ports.filter((p) => (p.rx_bcast_pps ?? 0) >= BROADCAST_STORM);
    const loops = sw.ports.filter((p) => p.loop);
    const fixed = sw.ports.filter((p) => this._fixed(p));
    const secFull = sw.ports.filter((p) => this._secFull(p));
    const stp = sw.ports.filter((p) => this._stpBlocked(p));
    const arp = sw.ports.filter((p) => p.arp_illegal > 0);
    const mirrored = (sw.mirror || []).filter((m) => m.monitor != null);
    const day = Date.now() - 86400000;
    const wobbly = sw.ports.filter((p) => (p.link_changes || 0) >= WOBBLE);
    const flips = sw.ports.filter((p) => (p.link_changes || 0) < WOBBLE && (this._changedAt(sw, p) ?? 0) > day);
    const note = (cls, ic, title, text) => `<div class="issue ${cls}">${icon(ic)}<div><b>${esc(title)}</b><br>${esc(text)}</div></div>`;
    const issues = [
      loops.length ? note("bad", "warn", t.count("loopPorts", loops.length), t("loopPortsText", { ports: loops.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      errs.length ? note("warn", "warn", t.count("errorPorts", errs.length), t("errorPortsText", { ports: errs.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      slow.length ? note("warn", "warn", t.count("slowPorts", slow.length), t("slowPortsText", { ports: slow.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      loud.length ? note("warn", "warn", t.count("manyBroadcast", loud.length), t("manyBroadcastText", { ports: loud.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      arp.length ? note("bad", "warn", t.count("arpPorts", arp.length), t("arpPortsText", { ports: arp.map((p) => `${t("port")} ${p.n} (${p.arp_illegal})`).join(", ") })) : "",
      mirrored.length ? note("warn", "warn", t.count("mirrorOn", mirrored.length), t("mirrorOnText", { groups: mirrored.map((m) => `${t("port")} ${m.monitor} ← ${[...new Set([...m.ingress, ...m.egress])].join(", ") || "–"}`).join("; ") })) : "",
      stp.length ? note("warn", "warn", t.count("stpPorts", stp.length), t("stpPortsText", { ports: stp.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      secFull.length ? note("warn", "warn", t.count("secFullPorts", secFull.length), t("secFullPortsText", { ports: secFull.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      fixed.length ? note("warn", "warn", t.count("fixedPorts", fixed.length), t("fixedPortsText", { ports: fixed.map((p) => `${t("port")} ${p.n} (${t("mode_" + p.mode)})`).join(", ") })) : "",
      wobbly.length ? note("warn", "warn", t.count("wobblyPorts", wobbly.length), t("wobblyPortsText", { ports: wobbly.map((p) => `${t("port")} ${p.n} (${p.link_changes}×)`).join(", ") })) : "",
      flips.length ? note("info", "info", t.count("linkChanges", flips.length), t("linkChangesText", { ports: flips.map((p) => `${t("port")} ${p.n}`).join(", ") })) : "",
      !errs.length && !slow.length && !wobbly.length && !loud.length && !loops.length && !fixed.length && !secFull.length && !stp.length && !arp.length && !mirrored.length ? note("ok", "ok", t("allFine"), t("allFineText")) : "",
    ].join("");
    return `<section class="card"><div class="card-h"><h2>${esc(t("faceplate"))}</h2>${live}<span class="grow"></span><span class="sub">${esc(t("clickPort"))}</span></div>
      <div class="face">${this._plate(sw)}<div class="legend">
        <span><i style="border-color:var(--g1000);background:color-mix(in srgb,var(--g1000) 28%,transparent)"></i>${esc(t("l1000"))}</span>
        <span><i style="border-color:var(--g100);background:color-mix(in srgb,var(--g100) 28%,transparent)"></i>${esc(t("l100"))}</span>
        <span><i style="border-color:var(--gdown);background:color-mix(in srgb,var(--gdown) 25%,transparent)"></i>${esc(t("noLink"))}</span>
        <span><i style="border:0;border-radius:50%;width:8px;height:8px;background:var(--bad);vertical-align:0"></i>${esc(t("errorsSinceStart"))}</span></div>${this._status(sw)}</div>${this._stats(sw)}</section>
      ${this._detail(sw)}
      <div class="twocol">
        <section class="card"><div class="card-h"><h2>${esc(t("mostLoad"))}</h2><span class="grow"></span><span class="sub">${esc(t("mostLoadSub"))}</span></div>
          <div class="toplist">${top.map((p) => `<button class="toprow" data-a="goto" data-v="${p.n}" title="${esc(t("showPort"))}"><span>${esc(t("port"))} ${p.n}<span class="sub"> ${esc(this._portLabel(p))}</span></span><span class="b"><i style="width:${(this._total(p) / max) * 100}%"></i></span><span class="mono" style="text-align:right">${this._num(this._total(p))}</span></button>`).join("") || `<span class="sub">${esc(t("noData"))}</span>`}</div></section>
        <section class="card"><div class="card-h"><h2>${esc(t("notes"))}</h2></div><div class="issues">${issues}</div></section>
      </div>`;
  }

  // Turning a port on or off, when the integration may write; a protected port cannot be turned off.
  _toggleButton(sw, p) {
    if (!sw.can_write) return "";
    const t = this._t;
    const off = p.admin_up !== false;
    const blocked = off && p.protected;
    return `<button class="chip small" data-a="toggle" data-v="${p.n}" ${blocked ? "disabled" : ""} title="${esc(blocked ? t("protectedHint") : "")}">${esc(t(off ? "portOff" : "portOn"))}</button>`;
  }

  async _togglePort(sw, number) {
    const port = sw.ports.find((p) => p.n === number);
    if (!port) return;
    const enable = port.admin_up === false;
    if (!enable && !confirm(this._t("confirmOff", { n: number }))) return;
    this._notice = null;
    try {
      await this._hass.callWS({ type: `${DOMAIN}/set_port_enabled`, entry_id: sw.entry_id, port: number, enabled: enable });
    } catch (err) {
      this._notice = this._t("writeFailed", { e: err?.message || String(err) });
    }
    await this._load();
  }

  // How long a duration is, in the two largest units that fit: "2 Std.", "4 Min.", "3 Tage".
  _dur(ms) {
    const t = this._t;
    const m = Math.round(ms / 60000);
    if (m >= 2880) return `${Math.round(m / 1440)} ${t("days")}`;
    if (m >= 120) return `${Math.round(m / 60)} ${t("hours")}`;
    return `${Math.max(m, 1)} ${t("minutes")}`;
  }

  // The link of a port over the shown range as a band that shares the time axis of the chart:
  // green with 1 Gbit/s, orange slower, grey without a link, hatched before the recording began.
  // Below it the events (newest first); four rows show, the rest scrolls.
  _linkHistory(sw, p) {
    const t = this._t;
    const h = this._history.get(`${sw.entry_id}:${p.n}:${this._range}`);
    const link = h?.link;
    if (!link) return "";
    const now = h.t1;
    const t0 = h.t0;
    const span = now - t0;
    const events = (link.events || []).map(([at, up, speed]) => ({ at: at * 1000, up: !!up, speed })).filter((e) => e.at >= t0).sort((a, b) => a.at - b.at);
    const known = Math.min(Math.max(link.since ? link.since * 1000 : t0, t0), now);
    const kind = (up, speed) => (!up ? "d" : speed > 0 && speed < 1000 ? "s" : "u");
    // the state when the range began: the opposite of the first change, else the current state
    let state = events.length ? { up: !events[0].up, speed: events[0].up ? 0 : 1000 } : { up: !!link.up, speed: link.speed };
    const segs = [];
    if (known > t0) segs.push({ from: t0, to: known, cls: "x" });
    let from = known;
    for (const e of events) {
      if (e.at > from) segs.push({ from, to: e.at, cls: kind(state.up, state.speed) });
      from = Math.max(from, e.at);
      state = e;
    }
    segs.push({ from, to: now, cls: kind(state.up, state.speed) });
    const title = { u: t("l1000"), s: t("slowerLink"), d: t("noLink"), x: t("notRecorded") };
    const band = segs
      .filter((s) => s.to > s.from)
      .map((s) => `<i class="${s.cls}" style="width:${(((s.to - s.from) / span) * 100).toFixed(3)}%" title="${esc(`${title[s.cls]} · ${this._when(s.from)} – ${this._when(s.to)}`)}"></i>`)
      .join("");
    const total = segs.filter((s) => s.cls !== "x").reduce((n, s) => n + (s.to - s.from), 0);
    const online = segs.filter((s) => s.cls === "u" || s.cls === "s").reduce((n, s) => n + (s.to - s.from), 0);
    const pct = total > 0 ? Math.min(100, (online / total) * 100) : null;
    const outages = events.filter((e) => !e.up).length;
    const slow = events.filter((e) => e.up && e.speed > 0 && e.speed < 1000).length;
    const chips = [
      pct != null ? `<span class="tag ${pct >= 99.9 ? "ok" : ""}">${esc(t("onlinePct", { p: this._num(pct, 1) }))}</span>` : "",
      outages ? `<span class="tag bad">${esc(t.count("outagesN", outages))}</span>` : "",
      slow ? `<span class="tag warn">${esc(t("slowN", { n: slow }))}</span>` : "",
    ].join("");
    const ticks = [0, 0.25, 0.5, 0.75].map((f) => `<span>${esc(this._when(t0 + span * f))}</span>`).join("") + `<span>${esc(t("now"))}</span>`;
    const rows = [...events].reverse().map((e, i, all) => {
      // how long a gap lasted: until the next event of the other kind, or until now
      const next = events[events.length - 1 - i + 1];
      const label = e.up ? t("linkUp", { speed: e.speed >= 1000 ? t("l1000") : e.speed >= 100 ? t("l100") : t("l10") }) : t("linkDown");
      const dur = !e.up ? ` · ${this._dur((next ? next.at : now) - e.at)}` : "";
      return `<div class="${e.up ? (e.speed > 0 && e.speed < 1000 ? "s" : "u") : "d"}"><i></i><span>${esc(label)}${esc(dur)}</span><span class="sub mono" title="${esc(this._when(e.at))}">${esc(this._ago(e.at))}</span></div>`;
    });
    return `<div class="lh"><div class="lh-head"><span><b>${esc(t("link"))}</b> <span class="sub">${esc(t("availability"))}</span></span><span class="chips">${chips}</span></div>
      <div class="band" role="img" aria-label="${esc(t("link"))}">${band}</div><div class="axis">${ticks}</div>
      ${rows.length ? `<div class="ev">${rows.join("")}</div>` : `<div class="sub">${esc(t("noLinkEvents"))}</div>`}</div>`;
  }

  _detail(sw) {
    const t = this._t;
    const p = sw.ports.find((x) => x.n === this._sel);
    if (!p) return "";
    const title = this._editing
      ? `<div class="nameedit"><b>${esc(t("port"))} ${p.n}</b><input id="portname" maxlength="40" value="${esc(p.name)}" placeholder="${esc(t("portName"))}" aria-label="${esc(t("portName"))}">${sw.can_write ? `<label class="check"><input type="checkbox" id="toswitch"> ${esc(t("alsoAtSwitch"))}</label>` : ""}<button class="chip" data-a="save">${esc(t("save"))}</button><button class="chip" data-a="cancel">${esc(t("cancel"))}</button></div>`
      : `<h3>${esc(t("port"))} ${p.n}${p.name ? " · " + esc(p.name) : ""} <button class="rowbtn" data-a="rename" title="${esc(t("rename"))}" aria-label="${esc(t("rename"))}">${icon("edit")}</button>${this._toggleButton(sw, p)}
          ${p.admin_up === false ? `<span class="tag bad">${esc(t("switchedOff"))}</span>` : ""}<span class="tag ${p.up ? "ok" : ""}">${p.up ? esc(t("link")) + " " + esc(this._speedText(p)) : esc(t("noLink"))}</span>${p.up && p.speed > 0 && p.speed < 1000 ? `<span class="tag warn">${esc(t("only100"))}</span>` : ""}${this._errors(p) ? `<span class="tag bad">${esc(t.count("errorsN", this._errors(p)))}</span>` : ""}<button class="rowbtn" data-a="deselect" title="${esc(t("closePort"))}" aria-label="${esc(t("closePort"))}" style="margin-left:auto">${icon("close")}</button></h3>`;
    const macs = p.macs.slice(0, MAX_MACS);
    const macList = macs.length
      ? `<div class="maclist">${macs.map((m) => `<div><span>${m.name ? esc(m.name) : `<span class="muted">${esc(t("unknown"))}</span>`}</span><span class="mono muted">${esc(m.mac)}</span></div>`).join("")}${p.macs.length > MAX_MACS ? `<div><span class="muted">${esc(t("moreN", { n: p.macs.length - MAX_MACS }))}</span></div>` : ""}</div>`
      : "";
    return `<section class="card" id="portcard"><div class="pd">
      <div>${title}${this._notice ? `<div class="notice" role="alert">${esc(this._notice)}</div>` : ""}<div class="histhead"><span class="sub">${esc(t({ "24h": "history", "7d": "history7d", "30d": "history30d" }[this._range]))}</span></div>
        ${p.up ? this._chart(sw, p) : `<div class="nodata">${esc(t("noLink"))}</div>`}
        ${this._linkHistory(sw, p)}
        ${this._changedAt(sw, p) ? `<div class="sub" style="margin-top:6px">${esc(t("linkChangedAgo", { when: this._ago(this._changedAt(sw, p)) }))}${p.link_changes ? " · " + esc(t("linkCount", { n: p.link_changes })) : ""}</div>` : ""}
        <div class="lg"><span><i style="background:var(--rx)"></i>${esc(t("receive"))} ${this._num(p.rx_rate)} Mbit/s${p.rx_util != null ? ` (${esc(this._util(p.rx_util))})` : ""}</span><span><i style="background:var(--tx)"></i>${esc(t("send"))} ${this._num(p.tx_rate)} Mbit/s${p.tx_util != null ? ` (${esc(this._util(p.tx_util))})` : ""}</span></div></div>
      <div><div class="sub" style="margin-bottom:6px">${esc(p.macs.length ? t("devicesAtPort") + " (" + p.macs.length + ")" : t("noDevices"))}</div>${macList}</div>
    </div></section>`;
  }

  // A column header that sorts the table; a second click turns the order around.
  _head(table, key, label, cls = "", first = 1) {
    const sort = this._sort[table];
    const aria = sort.key === key ? (sort.dir > 0 ? "ascending" : "descending") : "none";
    return `<th class="${cls}" aria-sort="${aria}"><button class="thbtn" data-a="sort" data-table="${table}" data-v="${key}" data-first="${first}">${esc(label)}</button></th>`;
  }

  _sorted(rows, table, values) {
    const { key, dir } = this._sort[table];
    const get = values[key];
    return [...rows].sort((a, b) => {
      const x = get(a);
      const y = get(b);
      // an empty value goes last in either order
      if ((x == null) !== (y == null)) return x == null ? 1 : -1;
      const order = typeof x === "string" ? x.localeCompare(y, this._lang) : (x ?? 0) - (y ?? 0);
      return order * dir || (a.n ?? a.port?.n ?? 0) - (b.n ?? b.port?.n ?? 0);
    });
  }

  // the ports the filter and the search leave, in the order of the sorted column
  _portRows(sw) {
    const q = this._q.trim().toLowerCase();
    const test = { all: () => true, up: (p) => p.up, down: (p) => !p.up, slow: (p) => p.up && p.speed > 0 && p.speed < 1000, err: (p) => this._errors(p) > 0 }[this._filter];
    const rows = sw.ports.filter(test).filter((p) => !q || `port ${p.n} ${p.name} ${p.macs.map((m) => `${m.name || ""} ${m.mac}`).join(" ")}`.toLowerCase().includes(q));
    return this._sorted(rows, "ports", {
      n: (p) => p.n,
      status: (p) => (p.up ? 0 : 1),
      speed: (p) => (p.up ? p.speed : null),
      rx: (p) => p.rx_rate,
      tx: (p) => p.tx_rate,
      errors: (p) => this._errors(p),
      devs: (p) => p.macs.length,
    });
  }

  _deviceRows(sw) {
    const q = this._dq.trim().toLowerCase();
    const rows = this._allMacs(sw)
      .filter((d) => this._dfilter === "all" || (this._dfilter === "named" ? d.name : !d.name))
      .filter((d) => !q || `${d.name || ""} ${d.mac} ${d.manufacturer || ""} port ${d.port.n} ${d.port.name}`.toLowerCase().includes(q));
    return this._sorted(rows, "devices", {
      name: (d) => d.name?.toLowerCase() || null,
      mac: (d) => d.mac,
      vendor: (d) => d.manufacturer?.toLowerCase() || null,
      port: (d) => d.port.n,
    });
  }

  _portsView(sw) {
    const t = this._t;
    const chip = (id, label) => `<button class="chip" data-a="filter" data-v="${id}" aria-pressed="${this._filter === id}">${esc(label)}</button>`;
    const slow = sw.ports.filter((p) => p.up && p.speed > 0 && p.speed < 1000).length;
    return `<section class="card"><div class="card-h"><h2>${esc(t("ports"))}</h2><span class="live"><span class="dot"></span>${esc(t("live"))}</span></div>
      <div class="tools">${chip("all", t("allPorts"))}${chip("up", t("activeF"))}${chip("down", t("noLinkF"))}${chip("slow", t("slowF"))}${chip("err", t("errF"))}
        <label class="search">${icon("search")}<input id="q" value="${esc(this._q)}" placeholder="${esc(t("searchPorts"))}" aria-label="${esc(t("search"))}"></label>
        <button class="chip" data-a="csv" data-v="ports" title="${esc(t("csvHint"))}">${icon("download")}CSV</button></div>
      <div class="infobar"><span id="count"></span><span class="warnnote">${slow ? esc(t.count("slowNote", slow)) : ""}</span></div>
      <div class="tablewrap"><table><thead><tr>${this._head("ports", "n", t("port"))}${this._head("ports", "status", t("status"))}${this._head("ports", "speed", t("speed"), "num")}${this._head("ports", "rx", t("rx"), "num")}${this._head("ports", "tx", t("tx"), "num")}${this._head("ports", "errors", t("errors"), "num")}${this._head("ports", "devs", t("devs"))}<th></th></tr></thead><tbody id="ptb"></tbody></table></div>
      <div class="empty" id="pempty" hidden>${esc(t("noPortMatches"))}</div></section>`;
  }

  _fillPorts(sw) {
    const t = this._t;
    const rows = this._portRows(sw);
    const peak = Math.max(1, ...sw.ports.map((p) => Math.max(p.rx_rate || 0, p.tx_rate || 0)));
    const bar = (p, v, color, util) => `<span class="bar" title="${esc(t("utilization"))}: ${esc(this._util(util) || t("noData"))}"><span class="b"><i style="width:${Math.min(100, ((v || 0) / peak) * 100)}%;background:${color}"></i></span><span class="mono">${p.up ? this._num(v) : "–"}</span>${p.up && util != null ? `<span class="sub">${esc(this._util(util))}</span>` : ""}</span>`;
    const shadow = this.shadowRoot;
    shadow.getElementById("ptb").innerHTML = rows
      .map((p) => {
        const names = p.macs.slice(0, 2).map((m) => esc(m.name || m.mac)).join(", ");
        return `<tr class="row link ${p.up ? "" : "down"}" data-a="goto" data-v="${p.n}" tabindex="0" title="${esc(t("showOnOverview"))}"><td><span class="pn">${esc(t("port"))} ${p.n}<small>${esc(p.name || (p.up ? "" : t("free")))}</small></span></td>
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
        <label class="search">${icon("search")}<input id="dq" value="${esc(this._dq)}" placeholder="${esc(t("searchDevices"))}" aria-label="${esc(t("search"))}"></label>
        <button class="chip" data-a="csv" data-v="devices" title="${esc(t("csvHint"))}">${icon("download")}CSV</button></div>
      <div class="tablewrap"><table><thead><tr>${this._head("devices", "name", t("device"))}${this._head("devices", "mac", t("mac"))}${this._head("devices", "vendor", t("vendor"))}${this._head("devices", "port", t("port"))}</tr></thead><tbody id="dtb"></tbody></table></div>
      <div class="empty" id="dempty" hidden>${esc(t("noDeviceMatches"))}</div></section>`;
  }

  _fillDevices(sw) {
    const t = this._t;
    const rows = this._deviceRows(sw);
    const shadow = this.shadowRoot;
    shadow.getElementById("dtb").innerHTML = rows
      .map((d) => `<tr class="row link" data-a="goto" data-v="${d.port.n}" tabindex="0" title="${esc(t("showOnOverview"))}"><td>${d.name ? esc(d.name) : `<span class="muted">${esc(t("unknown"))}</span>`}</td><td class="mono">${esc(d.mac)}</td><td>${esc(d.manufacturer || "–")}</td>
        <td><span class="tag acc">${esc(t("port"))} ${d.port.n}</span> <span class="sub">${esc(d.port.name)}</span></td></tr>`)
      .join("");
    shadow.getElementById("dempty").hidden = rows.length > 0;
  }

  // ---- CSV export: what the filter and the sort leave, as Excel reads it -----------------------

  _csv(kind) {
    const sw = this._switch;
    const t = this._t;
    const n = (v) => csvNumber(v, this._lang);
    const lines = [];
    if (kind === "ports") {
      lines.push([t("port"), t("portName"), t("status"), `${t("speed")} Mbit/s`, `${t("rx")} Mbit/s`, `${t("tx")} Mbit/s`, `${t("utilization")} ${t("rx")} %`, `${t("utilization")} ${t("tx")} %`, t("rxErrors"), t("txErrors"), t("rxDiscards"), t("txDiscards"), t("devs")]);
      for (const p of this._portRows(sw)) {
        lines.push([p.n, p.name, p.up ? t("linked") : t("noLink"), p.up ? p.speed : "", n(p.rx_rate), n(p.tx_rate), n(p.rx_util), n(p.tx_util), p.rx_errors, p.tx_errors, p.rx_discards, p.tx_discards, p.macs.length]);
      }
    } else {
      lines.push([t("device"), t("mac"), t("vendor"), t("port"), t("portName")]);
      for (const d of this._deviceRows(sw)) lines.push([d.name || "", d.mac, d.manufacturer || "", d.port.n, d.port.name]);
    }
    return csvText(lines);
  }

  _download(name, text) {
    // the marker at the start makes Excel read the file as UTF-8
    const url = URL.createObjectURL(new Blob(["\ufeff", text], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    this.shadowRoot.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }

  // Errors, packet rates, discards and volume per port: grouped columns, every one sortable.
  _diagView(sw) {
    const t = this._t;
    const rows = this._sorted(sw.ports.filter((p) => p.up || this._errors(p)), "diag", {
      n: (p) => p.n,
      rxe: (p) => p.rx_errors || 0,
      txe: (p) => p.tx_errors || 0,
      rxp: (p) => p.rx_pps || 0,
      txp: (p) => p.tx_pps || 0,
      bc: (p) => p.rx_bcast_pps || 0,
      mc: (p) => p.rx_mcast_pps || 0,
      rxd: (p) => p.rx_discards || 0,
      txd: (p) => p.tx_discards || 0,
      rxb: (p) => p.rx_bytes || 0,
      txb: (p) => p.tx_bytes || 0,
      state: (p) => (this._errors(p) > 5 ? 1 : 0),
    });
    const maxRx = Math.max(1, ...rows.map((p) => p.rx_bytes || 0));
    const maxTx = Math.max(1, ...rows.map((p) => p.tx_bytes || 0));
    const h = (key, label) => this._head("diag", key, label, "num", -1);
    // a zero is quiet, anything else is in colour
    const count = (v, level = "warn") => {
      const n = v || 0;
      return `<td class="num mono ${n ? "hot " + level : "zero"}">${n.toLocaleString(this._lang)}</td>`;
    };
    const rate = (v) => `<td class="num mono ${v ? "" : "zero"}">${this._num(v, 1)}</td>`;
    const vol = (v, max, color) => `<td class="num"><span class="bar"><span class="b"><i style="width:${Math.min(100, ((v || 0) / max) * 100)}%;background:${color}"></i></span><span class="mono volv">${esc(this._bytes(v))}</span></span></td>`;
    const body = rows
      .map((p) => `<tr class="row link" data-a="goto" data-v="${p.n}" tabindex="0" title="${esc(t("showOnOverview"))}"><td class="stick"><span class="pn nowrap">${esc(t("port"))} ${p.n}<small>${esc(p.name || (p.up ? "" : t("free")))}</small></span></td>
        ${count(p.rx_errors, "bad")}${count(p.tx_errors, "bad")}${rate(p.rx_pps)}${rate(p.tx_pps)}${rate(p.rx_bcast_pps)}${rate(p.rx_mcast_pps)}${count(p.rx_discards)}${count(p.tx_discards)}${vol(p.rx_bytes, maxRx, "var(--rx)")}${vol(p.tx_bytes, maxTx, "var(--tx)")}
        <td>${this._errors(p) > 5 ? `<span class="tag warn">${esc(t(this._assess(p)))}</span>` : `<span class="tag ok">${esc(t("fine"))}</span>`}</td></tr>`)
      .join("");
    return `<section class="card"><div class="card-h"><h2>${esc(t("errorCounters"))}</h2><span class="grow"></span><span class="sub">${esc(t("sinceStart"))}</span></div>
      <div class="tablewrap"><table class="diag"><thead>
        <tr class="grp"><th class="stick"></th><th class="num" colspan="2">${esc(t("grpErrors"))}</th><th class="num" colspan="4">${esc(t("grpPackets"))}</th><th class="num" colspan="2">${esc(t("grpDiscards"))}</th><th class="num" colspan="2">${esc(t("grpVolume"))}</th><th></th></tr>
        <tr>${this._head("diag", "n", t("port"), "stick")}${h("rxe", t("rx"))}${h("txe", t("tx"))}${h("rxp", t("rx"))}${h("txp", t("tx"))}${h("bc", "Broadcast")}${h("mc", "Multicast")}${h("rxd", t("rx"))}${h("txd", t("tx"))}${h("rxb", t("rx"))}${h("txb", t("tx"))}${this._head("diag", "state", t("assessment"), "", -1)}</tr></thead>
      <tbody>${body}</tbody></table></div></section>`;
  }

  // ---- configuration of the switch -----------------------------------------------------------

  _configView(sw) {
    return this._actionsCard(sw) + this._functionsCard(sw) + this._vlanCard(sw);
  }

  // Which functions of the switch are on: IGMP snooping, DSCP priority, DoS defense, DHCP snooping,
  // 802.1X and port mirroring (with the groups that run).
  _functionsCard(sw) {
    const t = this._t;
    const names = Object.keys(sw.features || {});
    const info = (label, value) => `<div><span>${esc(label)}</span><span>${esc(value)}</span></div>`;
    const groups = (sw.mirror || []).filter((m) => m.monitor != null);
    const mirror = (m) => `${t("port")} ${m.monitor} ← ${[...new Set([...m.ingress, ...m.egress])].join(", ") || "–"}`;
    const row = (name) => {
      const on = sw.features[name];
      const extra = name === "mirror" && on && groups.length ? ` <span class="muted">${esc(groups.map(mirror).join("; "))}</span>` : "";
      return `<div><span>${esc(t("feature_" + name))}</span><span><span class="tag ${on ? "ok" : ""}">${esc(t(on ? "on" : "off"))}</span>${extra}</span></div>`;
    };
    const root = sw.stp_root_port ? sw.ports.find((p) => p.n === sw.stp_root_port) : null;
    const more = [
      sw.qos_mode ? info(t("qosScheduler"), t("qos_" + sw.qos_mode)) : "",
      sw.stp_changes != null ? info(t("stpChanges"), sw.stp_changes) : "",
      sw.stp_root_port ? info(t("stpRoot"), `${t("port")} ${sw.stp_root_port}${root?.name ? " · " + root.name : ""}`) : "",
    ].join("");
    if (!names.length && !more) return "";
    return `<section class="card"><div class="card-h"><h2>${esc(t("functions"))}</h2></div><div class="details"><div class="kv">${names.map(row).join("")}${more}</div></div></section>`;
  }

  // Saving the configuration (so that a restart keeps it) and restarting, when the integration may write.
  _actionsCard(sw) {
    if (!sw.can_act) return "";
    const t = this._t;
    return `<section class="card"><div class="card-h"><h2>${esc(t("actions"))}</h2></div><div class="details">
      ${this._notice ? `<div class="notice" role="alert">${esc(this._notice)}</div>` : ""}
      <button class="chip" data-a="act" data-v="save_config">${esc(t("saveConfig"))}</button>
      <button class="chip" data-a="act" data-v="reboot">${esc(t("rebootSwitch"))}</button>
      <div class="sub" style="margin-top:8px">${esc(t("actionsHint"))}</div></div></section>`;
  }

  async _act(sw, action) {
    const t = this._t;
    if (action === "reboot" && !confirm(t("confirmReboot"))) return;
    this._notice = null;
    try {
      await this._hass.callWS({ type: `${DOMAIN}/action`, entry_id: sw.entry_id, action });
      this._notice = t(action === "reboot" ? "rebootSent" : "configSaved");
    } catch (err) {
      this._notice = t("writeFailed", { e: err?.message || String(err) });
    }
    this._render();
  }

  // The VLANs of the switch as a grid: one tile per port, filled when the port is untagged in the
  // VLAN, outlined when it is tagged. A VLAN without a port is dimmed.
  _vlanCard(sw) {
    const t = this._t;
    const ids = Object.keys(sw.vlans || {}).map(Number).sort((a, b) => a - b);
    if (!ids.length) return "";
    const last = sw.ports.length - 1;
    const axis = sw.ports.map((p, i) => `<span>${i === 0 || p.n % 5 === 0 || i === last ? p.n : ""}</span>`).join("");
    const grid = (id) => {
      let count = 0;
      const tiles = sw.ports
        .map((p) => {
          const untagged = (p.vlans_untagged || []).includes(id);
          const tagged = (p.vlans_tagged || []).includes(id);
          if (untagged || tagged) count++;
          const kind = untagged ? "u" : tagged ? "g" : "";
          const state = untagged ? t("vlanUntagged") : tagged ? t("vlanTagged") : t("vlanNone");
          const pvid = p.pvid === id ? ` · PVID ${id}` : "";
          return `<span class="vt ${kind}" title="${esc(`${t("port")} ${p.n}: ${state}${pvid}`)}">${p.n}</span>`;
        })
        .join("");
      return { count, tiles };
    };
    const rows = ids
      .map((id) => {
        const { count, tiles } = grid(id);
        const name = `${esc(sw.vlans[id] || "")}<span class="badge">${esc(count ? t.count("vlanPorts", count) : t("vlanUnused"))}</span>`;
        const cell = count ? `<div class="vgrid" style="--cols:${sw.ports.length}">${tiles}</div>` : `<span class="muted">${esc(t("vlanNoPorts"))}</span>`;
        return `<tr class="row${count ? "" : " unused"}"><td class="num mono">${id}</td><td>${name}</td><td>${cell}</td></tr>`;
      })
      .join("");
    return `<section class="card"><div class="card-h"><h2>${esc(t("vlans"))}</h2><span class="grow"></span><span class="sub">${esc(t.count("vlanCount", ids.length))}</span></div>
      <div class="tablewrap"><table><thead><tr><th class="num">${esc(t("vlanId"))}</th><th>${esc(t("vlanName"))}</th><th><div class="vgrid vaxis" style="--cols:${sw.ports.length}">${axis}</div></th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="vlegend"><span><i class="vt u"></i>${esc(t("vlanUntagged"))}</span><span><i class="vt g"></i>${esc(t("vlanTagged"))}</span><span><i class="vt"></i>${esc(t("vlanNone"))}</span><span>${esc(t("vlanHover"))}</span></div></section>`;
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
        case "sort": {
          const sort = this._sort[el.dataset.table];
          sort.dir = sort.key === v ? -sort.dir : Number(el.dataset.first) || 1;
          sort.key = v;
          break;
        }
        case "csv": {
          const sw = this._switch;
          if (sw) this._download(`${sw.title.replace(/[^\w.-]+/g, "_")}-${v}.csv`, this._csv(v));
          if (outside) this._render();
          return;
        }
        case "range": this._range = v; break;
        case "toggle": {
          const sw = this._switch;
          if (sw) this._togglePort(sw, Number(v));
          return;
        }
        case "act": {
          const sw = this._switch;
          if (sw) this._act(sw, v);
          return;
        }
        case "look-toggle": this._menuOpen = !this._menuOpen; break;
        case "look": this._setLook({ [el.dataset.kind]: v }); break;
        case "nav-toggle": this._navOpen = !this._navOpen; break;
        case "tab": this._navOpen = false; this._tab = v; this._editing = false; this._notice = null; break;
        case "menu":
          this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
          if (outside) this._render();
          return;
        case "integration":
          history.pushState(null, "", `/config/integrations/integration/${DOMAIN}`);
          window.dispatchEvent(new CustomEvent("location-changed"));
          return;
        case "details": this._details = !this._details; break;
        case "port": this._sel = this._sel === +v ? null : +v; this._editing = false; this._notice = null; this._reveal = this._sel != null; break;
        case "deselect": this._sel = null; this._editing = false; this._notice = null; break;
        case "goto": this._sel = +v; this._tab = "overview"; this._editing = false; this._notice = null; this._reveal = true; break;
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
    const tileOf = (event) => event.target.closest?.(".port[data-v]");
    root.addEventListener("mouseover", (event) => this._setTip(tileOf(event) ? Number(tileOf(event).dataset.v) : null));
    root.addEventListener("mouseleave", () => { this._setTip(null); this._hoverAt(null); });
    root.addEventListener("mousemove", (event) => {
      const plot = event.composedPath().find((n) => n.classList?.contains("plot"));
      if (!plot) return this._hoverAt(null);
      const box = plot.getBoundingClientRect();
      this._hoverAt(plot.dataset.p, (event.clientX - box.left) / box.width);
    });
    root.addEventListener("focusin", (event) => this._setTip(tileOf(event) ? Number(tileOf(event).dataset.v) : null));
    root.addEventListener("focusout", () => this._setTip(null));
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
      // a table row that opens a port acts on Enter like a button
      if (event.key === "Enter" && event.target.matches?.("tr.link")) {
        event.target.click();
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
      await this._hass.callWS({ type: `${DOMAIN}/set_port_name`, entry_id: sw.entry_id, port: this._sel, name: input.value, to_switch: !!this.shadowRoot.getElementById("toswitch")?.checked });
    } catch (err) {
      this._error = err?.message || String(err);
    }
    this._editing = false;
    await this._load();
  }
}

customElements.define("tplink-switch-panel", TplinkSwitchPanel);
