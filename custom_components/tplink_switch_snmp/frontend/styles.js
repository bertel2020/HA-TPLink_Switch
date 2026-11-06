// The look of the panel: the "ocean" palette of the EnOcean panel, light and dark. The panel
// sets the attribute "dark" on its host when Home Assistant is in dark mode.
export const STYLES = `
:host { display: block; --fs: 1; min-height: 100%; --bg: #f4f6f9; --surface: #ffffff; --soft: #f5f7f9; --line: #e1e5ea; --line-2: #eef0f3; --input-line: #c3cbd5;
  --text: #1b1f24; --muted: #5b6270; --accent: #0a6aa8; --accent-hover: #07507f; --accent-soft: #eaf3fa; --on-accent: #fff;
  --neutral-soft: #eef1f4; --tag-text: #3a414c; --ok: #1e6b34; --ok-soft: #e6f4ea; --warn: #8a4b00; --warn-soft: #fff1de;
  --bad: #a1261b; --bad-soft: #fdecea; --focus: #7db8e0; --shadow-c: rgba(16,24,40,.06);
  --g1000: #2e9b57; --g100: #d98a1e; --gdown: #cfd5dc; --rx: #0a6aa8; --tx: #7b5cc9; color-scheme: light;
  background: var(--bg); color: var(--text); font: calc(14px * var(--fs)) / 1.45 Roboto, system-ui, -apple-system, "Segoe UI", sans-serif; }
* { box-sizing: border-box; }
button, input, select { font: inherit; color: inherit; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: max(10.5px, calc(12px * var(--fs))); white-space: nowrap; }
.muted { color: var(--muted); } .sub { color: var(--muted); font-size: max(10.5px, calc(12px * var(--fs))); }
svg { width: 20px; height: 20px; fill: currentColor; flex: none; }
.topbar { background: var(--surface); border-bottom: 1px solid var(--line); }
.topbar-in { max-width: 1280px; margin: 0 auto; padding: 10px 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.brand { display: flex; align-items: center; gap: 10px; font-size: max(10.5px, calc(18px * var(--fs))); font-weight: 500; margin-right: auto; }
.logo { width: 36px; height: 36px; border-radius: 9px; background: #14323f; color: #5fe0c8; display: grid; place-items: center; }
.logo svg { width: 22px; height: 22px; }
.menu { display: none; border: 0; background: none; cursor: pointer; border-radius: 50%; padding: 6px; color: var(--text); }
:host([narrow]) .menu { display: inline-flex; }
nav { display: flex; gap: 2px; flex-wrap: wrap; }
.tab { border: 0; background: none; border-radius: 20px; padding: 8px 16px; font-weight: 500; color: var(--muted); cursor: pointer; }
.tab:hover { color: var(--text); }
.tab[aria-selected="true"] { background: var(--accent-soft); color: var(--accent-hover); }
.burger { display: none; border: 0; background: none; cursor: pointer; border-radius: 50%; padding: 6px; color: var(--text); }
.burger:focus-visible, .menu:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.navwrap { display: contents; }
.btnlabel { display: none; }
@media (max-width: 700px) {
  .burger { display: inline-flex; }
  .navwrap { display: none; order: 10; width: 100%; flex-direction: column; align-items: stretch; gap: 8px; border-top: 1px solid var(--line); padding-top: 6px; }
  .navwrap.open { display: flex; }
  nav { flex-direction: column; gap: 0; }
  .tab { text-align: left; border-radius: 10px; padding: 12px 14px; }
  .navwrap .chip { align-self: flex-start; }
}
.chip { min-height: 32px; padding: 0 14px; border-radius: 18px; border: 1px solid var(--input-line); font-size: max(10.5px, calc(13px * var(--fs))); font-weight: 500; background: var(--surface); color: var(--text); cursor: pointer; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.chip:hover { background: var(--accent-soft); color: var(--accent-hover); }
.chip[aria-pressed="true"] { border-color: var(--accent); color: var(--accent-hover); background: var(--accent-soft); }
.chip.outline { color: var(--accent); border-color: var(--accent); }
.chip svg { width: 16px; height: 16px; }
.tab:focus-visible, .chip:focus-visible, .port:focus-visible, .rowbtn:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.app { max-width: 1280px; margin: 0 auto; padding: 16px 16px 40px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
.app > * { min-width: 0; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 1px 3px var(--shadow-c); }
.card-h { display: flex; align-items: center; gap: 10px; padding: 14px 20px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.card-h h2 { margin: 0; font-size: max(10.5px, calc(16px * var(--fs))); font-weight: 500; }
.grow { flex: 1; }
.live { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 12px; background: var(--ok-soft); color: var(--ok); font-size: max(10.5px, calc(12px * var(--fs))); font-weight: 500; }
.live.stale { background: var(--bad-soft); color: var(--bad); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.tag { display: inline-flex; align-items: center; gap: 4px; padding: 1px 8px; border-radius: 10px; font-size: max(10.5px, calc(11px * var(--fs))); background: var(--neutral-soft); color: var(--tag-text); white-space: nowrap; }
.tag.ok { background: var(--ok-soft); color: var(--ok); } .tag.warn { background: var(--warn-soft); color: var(--warn); }
.tag.bad { background: var(--bad-soft); color: var(--bad); } .tag.acc { background: var(--accent-soft); color: var(--accent); }
.sw { display: flex; align-items: center; gap: 16px; padding: 18px 20px; flex-wrap: wrap; }
.sw-icon { width: 44px; height: 44px; border-radius: 10px; background: var(--accent-soft); color: var(--accent); display: grid; place-items: center; }
.sw-icon svg { width: 26px; height: 26px; }
.sw-name { font-size: max(10.5px, calc(16px * var(--fs))); font-weight: 500; }
.sw-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: max(10.5px, calc(12px * var(--fs))); color: var(--muted); }
.sw-meta .on { color: var(--ok); font-weight: 500; display: inline-flex; align-items: center; gap: 6px; }
.sw-meta .off { color: var(--bad); font-weight: 500; display: inline-flex; align-items: center; gap: 6px; }
.sw-actions { margin-left: auto; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.statgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; padding: 0 20px 20px; }
.tile { background: var(--soft); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; display: grid; gap: 2px; align-content: start; min-width: 0; }
.tile .lbl { color: var(--muted); font-size: max(10.5px, calc(12px * var(--fs))); }
.tile .big { font-size: max(10.5px, calc(22px * var(--fs))); font-weight: 500; line-height: 1.25; }
.tile .big small { font-size: max(10.5px, calc(13px * var(--fs))); font-weight: 400; color: var(--muted); }
.tile.warn { background: var(--warn-soft); border-color: transparent; } .tile.warn .big { color: var(--warn); }
.tile.bad { background: var(--bad-soft); border-color: transparent; } .tile.bad .big { color: var(--bad); }
.details { padding: 0 20px 18px; }
.kv { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 6px 28px; border-top: 1px solid var(--line); padding-top: 14px; }
.kv div { display: flex; justify-content: space-between; gap: 12px; font-size: max(10.5px, calc(13px * var(--fs))); }
.kv span:first-child { color: var(--muted); }
.swpick { border: 1px solid var(--input-line); border-radius: 18px; background: var(--surface); padding: 4px 12px; min-height: 32px; }
.face { padding: 18px 20px 8px; }
.chassis { display: flex; align-items: stretch; gap: 14px; padding: 12px 16px; border-radius: 10px; overflow-x: auto; border: 1px solid #0d1013;
  background: linear-gradient(180deg, #454c55 0%, #30363d 8%, #262b31 100%); box-shadow: inset 0 1px 0 rgb(255 255 255 / 16%), inset 0 -2px 0 rgb(0 0 0 / 35%), 0 2px 8px rgb(16 24 40 / 22%); color-scheme: dark; }
.badge-plate { flex: none; width: 104px; display: grid; align-content: center; gap: 6px; padding-right: 14px; border-right: 1px solid rgb(255 255 255 / 12%); box-shadow: 1px 0 0 rgb(0 0 0 / 35%); color: #c8d0d9; }
.badge-plate b { font-size: max(10.5px, calc(13px * var(--fs))); letter-spacing: .08em; text-transform: uppercase; font-weight: 600; }
.badge-plate span { font-size: max(10.5px, calc(10px * var(--fs))); color: #8f99a5; line-height: 1.3; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.led { width: 7px; height: 7px; border-radius: 50%; background: #3a4149; box-shadow: inset 0 1px 1px rgb(0 0 0 / 60%); flex: none; }
.led.on { background: #3ddc84; box-shadow: 0 0 6px #3ddc84; } .led.amber { background: #ffb020; box-shadow: 0 0 6px #ffb020; }
.led.red { background: #ff5a4d; box-shadow: 0 0 6px #ff5a4d; }
.badge-plate .leds { display: flex; gap: 6px; align-items: center; font-size: max(10.5px, calc(9px * var(--fs))); letter-spacing: .06em; color: #8f99a5; }
.badge-plate .upt { color: #8f99a5; } .badge-plate .upt em { font-style: normal; color: #c8d0d9; font-weight: 500; white-space: nowrap; }
.statusline { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.statusline .tag { font-size: max(10.5px, calc(13px * var(--fs))); padding: 3px 11px; border-radius: 14px; } .statusline .tag b { font-weight: 500; }
.plate { flex: 1; min-width: 0; display: grid; gap: 6px; align-content: center; }
.plate-row { display: flex; gap: 12px; }
.grp { flex: 1; display: flex; gap: 4px; min-width: 0; }
.port { all: unset; box-sizing: border-box; cursor: pointer; flex: 1 1 0; min-width: 34px; display: grid; gap: 2px; justify-items: center; padding: 3px 2px 2px; border-radius: 6px; position: relative; }
.port .n { font-size: max(10.5px, calc(10px * var(--fs))); color: #aeb7c1; font-weight: 500; line-height: 1.1; }
.port .v { font-size: max(10.5px, calc(9px * var(--fs))); color: #8f99a5; height: 11px; line-height: 11px; }
.rj { position: relative; width: 100%; max-width: 40px; height: 26px; border-radius: 3px; border: 2px solid #8b95a0; background: linear-gradient(180deg, #08090b 0%, #1a1e23 100%); box-shadow: inset 0 3px 5px rgb(0 0 0 / 85%), 0 1px 0 rgb(255 255 255 / 10%); }
.rj::before { content: ""; position: absolute; left: 50%; top: -2px; width: 12px; height: 4px; transform: translateX(-50%); background: #262b31; border-radius: 0 0 2px 2px; }
.rj::after { content: ""; position: absolute; left: 4px; right: 4px; bottom: 2px; height: 5px; background: repeating-linear-gradient(90deg, #c9a24b 0 2px, transparent 2px 4px); opacity: .85; }
.rj .led { position: absolute; top: -9px; left: 2px; } .rj .led + .led { left: auto; right: 2px; }
.port:hover .rj { border-color: #c4ccd5; }
.port.s1000 .rj { border-color: color-mix(in srgb, var(--g1000) 70%, #8b95a0); box-shadow: inset 0 3px 5px rgb(0 0 0 / 85%), 0 0 7px color-mix(in srgb, var(--g1000) 55%, transparent); }
.port.s100 .rj { border-color: color-mix(in srgb, var(--g100) 70%, #8b95a0); box-shadow: inset 0 3px 5px rgb(0 0 0 / 85%), 0 0 7px color-mix(in srgb, var(--g100) 55%, transparent); }
.port.s10 .rj { border-color: var(--bad); }
.port.s1000 .led.link { background: #3ddc84; box-shadow: 0 0 6px #3ddc84; } .port.s100 .led.link { background: #ffb020; box-shadow: 0 0 6px #ffb020; } .port.s10 .led.link { background: #ff5a4d; box-shadow: 0 0 6px #ff5a4d; }
.port .led.act.on { background: #6cb8ff; box-shadow: 0 0 6px #6cb8ff; }
.port.sel { background: rgb(255 255 255 / 12%); box-shadow: 0 0 0 2px #fff; }
.port.sel .n { color: #fff; }
.tip { position: fixed; z-index: 10; width: max-content; max-width: min(320px, calc(100vw - 16px)); padding: 10px 12px; border-radius: 10px; background: var(--surface); color: var(--text); border: 1px solid var(--line); box-shadow: 0 6px 24px rgba(16,24,40,.22); display: grid; gap: 6px; pointer-events: none; font-size: max(10.5px, calc(13px * var(--fs))); }
.tip[hidden] { display: none; }
.tip-h { font-size: max(10.5px, calc(15px * var(--fs))); }
.tip-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.tip-rate { display: grid; grid-template-columns: 10px 1fr auto auto; gap: 8px; align-items: center; }
.tip-rate i { width: 10px; height: 10px; border-radius: 3px; }
.tip-sep { border-top: 1px solid var(--line-2); }
.tip-devs { display: grid; gap: 3px; }
.tip-devs > div { display: flex; justify-content: space-between; gap: 12px; }
.port.err::after { content: ""; position: absolute; top: 2px; right: 3px; width: 8px; height: 8px; border-radius: 50%; background: var(--bad); }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: max(10.5px, calc(12px * var(--fs))); color: var(--muted); margin-top: 12px; }
.legend i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: -2px; margin-right: 6px; border: 2px solid; }
.pd { padding: 16px 20px 20px; display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 20px; }
@media (max-width: 820px) { .pd { grid-template-columns: minmax(0, 1fr); } }
.pd h3 { margin: 0 0 4px; font-size: max(10.5px, calc(15px * var(--fs))); font-weight: 500; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.nameedit { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.check { display: inline-flex; align-items: center; gap: 6px; font-size: max(10.5px, calc(13px * var(--fs))); color: var(--muted); }
.nameedit input[type="checkbox"] { min-width: 0; min-height: 0; }
.nameedit input { border: 1px solid var(--input-line); border-radius: 18px; padding: 4px 12px; min-height: 32px; background: var(--surface); min-width: 220px; }
.spark { width: 100%; height: 96px; background: var(--soft); border: 1px solid var(--line); border-radius: 10px; display: block; }
.spark path.f { fill-opacity: .14; stroke: none; } .spark path.l { fill: none; stroke-width: 1.6; vector-effect: non-scaling-stroke; }
.nodata { height: 96px; display: grid; place-items: center; background: var(--soft); border: 1px dashed var(--line); border-radius: 10px; color: var(--muted); font-size: max(10.5px, calc(12px * var(--fs))); text-align: center; padding: 0 12px; }
.notice { margin: 4px 0 8px; padding: 8px 12px; border-radius: 10px; background: var(--bad-soft); color: var(--bad); font-size: max(10.5px, calc(13px * var(--fs))); }
.chip[disabled] { opacity: .5; cursor: not-allowed; }
.rangebar { display: flex; align-items: center; gap: 6px; padding: 0 20px 10px; flex-wrap: wrap; }
.plot { position: relative; margin-top: 8px; cursor: crosshair; }
.plot .spark { height: 52px; }
.plot .pcur { position: absolute; top: 0; bottom: 0; border-left: 1px solid var(--muted); pointer-events: none; display: none; }
.plot .pdot { position: absolute; width: 8px; height: 8px; border-radius: 50%; margin: -4px 0 0 -4px; pointer-events: none; display: none; }
.plot .ptip { position: absolute; bottom: calc(100% + 6px); transform: translateX(-50%); background: var(--surface); border: 1px solid var(--input-line); border-radius: 8px; padding: 2px 8px; font-size: max(10.5px, calc(12px * var(--fs))); white-space: nowrap; pointer-events: none; display: none; z-index: 3; box-shadow: 0 2px 6px var(--shadow-c); }
.plot .ptip span { color: var(--muted); }
.tile .ax { display: flex; justify-content: space-between; font-size: max(10.5px, calc(11px * var(--fs))); color: var(--muted); }
.tile .k { display: flex; justify-content: space-between; gap: 8px; font-size: max(10.5px, calc(12px * var(--fs))); margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--line); color: var(--muted); }
.tile .k b { font-weight: 500; color: var(--text); }
.histhead { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 4px 0 10px; flex-wrap: wrap; }
.rangepick { display: inline-flex; gap: 6px; }
.lg { display: flex; gap: 14px; font-size: max(10.5px, calc(12px * var(--fs))); color: var(--muted); margin-top: 6px; flex-wrap: wrap; }
.lg i { display: inline-block; width: 10px; height: 3px; border-radius: 2px; vertical-align: 3px; margin-right: 6px; }
.maclist { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; max-height: 280px; overflow-y: auto; }
.maclist div { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 7px 12px; border-top: 1px solid var(--line-2); font-size: max(10.5px, calc(13px * var(--fs))); }
.maclist div:first-child { border-top: 0; }
.tools { display: flex; gap: 8px; padding: 12px 16px; flex-wrap: wrap; border-bottom: 1px solid var(--line); align-items: center; }
.search { flex: 1 1 240px; min-width: 200px; display: flex; align-items: center; gap: 8px; border: 1px solid var(--input-line); border-radius: 18px; padding: 0 14px; min-height: 36px; background: var(--surface); }
.search input { all: unset; flex: 1; min-width: 0; }
.search svg { color: var(--muted); width: 18px; height: 18px; }
.infobar { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; font-size: max(10.5px, calc(12px * var(--fs))); color: var(--muted); border-bottom: 1px solid var(--line); gap: 12px; flex-wrap: wrap; }
.warnnote { color: var(--warn); font-weight: 500; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: max(10.5px, calc(11px * var(--fs))); letter-spacing: .04em; text-transform: uppercase; color: var(--muted); font-weight: 500; padding: 10px 12px; background: var(--soft); border-bottom: 1px solid var(--line); white-space: nowrap; }
td { padding: 10px 12px; border-bottom: 1px solid var(--line-2); vertical-align: middle; }
th:first-child, td:first-child { padding-left: 20px; } th:last-child, td:last-child { padding-right: 20px; }
tr.row:hover td { background: var(--soft); }
tr.link { cursor: pointer; } tr.link:focus-visible { outline: 2px solid var(--focus); outline-offset: -2px; }
tr.down td { color: var(--muted); }
td.num, th.num { text-align: right; }
.pn { font-weight: 500; } .pn small { display: block; font-weight: 400; color: var(--muted); font-size: max(10.5px, calc(12px * var(--fs))); }
.bar { display: flex; align-items: center; gap: 8px; justify-content: flex-end; }
.bar .b { width: 70px; height: 6px; border-radius: 3px; background: var(--neutral-soft); overflow: hidden; }
.bar .b i { display: block; height: 100%; border-radius: 3px; }
.bar .sub { white-space: nowrap; min-width: 3.4em; text-align: right; }
.thbtn { all: unset; cursor: pointer; font: inherit; text-transform: inherit; letter-spacing: inherit; color: inherit; white-space: nowrap; }
.thbtn:hover { color: var(--text); }
.thbtn:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; border-radius: 4px; }
th[aria-sort="ascending"] .thbtn::after { content: " ▲"; font-size: .8em; }
th[aria-sort="descending"] .thbtn::after { content: " ▼"; font-size: .8em; }
th[aria-sort]:not([aria-sort="none"]) { color: var(--text); }
table.diag { min-width: 0; }
table.diag .ghead th { padding: 8px 12px 2px; background: var(--soft); border-bottom: 0; font-size: max(10px, calc(10px * var(--fs))); letter-spacing: .06em; }
table.diag .ghead th + th { border-left: 1px solid var(--line); }
table.diag .ghead th.num { text-align: center; }
table.diag tr:not(.ghead) th { padding-top: 2px; }
table.diag .stick { position: sticky; left: 0; z-index: 1; background: var(--surface); }
table.diag th.stick { background: var(--soft); }
table.diag tr.row:hover td.stick { background: var(--soft); }
.nowrap { white-space: nowrap; }
td.zero { color: var(--muted); opacity: .55; }
td.hot { font-weight: 600; } td.hot.warn { color: var(--warn); } td.hot.bad { color: var(--bad); }
.volv { min-width: 5.5em; text-align: right; }
table.diag .bar .b { width: 30px; } table.diag .bar { gap: 6px; } table.diag td, table.diag th { padding-left: 8px; padding-right: 8px; } table.diag td.l, table.diag th.stick { padding-left: 20px; }
.rowbtn { all: unset; cursor: pointer; color: var(--muted); border-radius: 6px; padding: 4px; display: inline-flex; }
.rowbtn:hover { color: var(--accent); background: var(--accent-soft); }
.empty { padding: 36px; text-align: center; color: var(--muted); }
.error { padding: 20px; color: var(--bad); }
.twocol { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
@media (max-width: 900px) { .twocol { grid-template-columns: minmax(0, 1fr); } }
.toplist { padding: 6px 20px 14px; display: grid; gap: 10px; }
.toprow { all: unset; box-sizing: border-box; cursor: pointer; border-radius: 8px; padding: 4px 6px; margin: 0 -6px; display: grid; grid-template-columns: minmax(80px, 150px) 1fr 76px; gap: 12px; align-items: center; font-size: max(10.5px, calc(13px * var(--fs))); }
.toprow:hover { background: var(--soft); } .toprow:focus-visible { outline: 2px solid var(--focus); outline-offset: 1px; }
.toprow .b { height: 8px; border-radius: 4px; background: var(--neutral-soft); overflow: hidden; }
.toprow .b i { display: block; height: 100%; background: var(--accent); border-radius: 4px; }
.issues { padding: 6px 20px 16px; display: grid; gap: 8px; }
.issue { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 10px; font-size: max(10.5px, calc(13px * var(--fs))); }
.issue.warn { background: var(--warn-soft); color: var(--warn); } .issue.bad { background: var(--bad-soft, var(--warn-soft)); color: var(--bad); } .lh { margin-top: 12px; display: grid; gap: 6px; }
.lh-head { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; align-items: baseline; }
.lh-head b { font-weight: 500; } .chips { display: flex; gap: 6px; flex-wrap: wrap; }
.band { height: 14px; border-radius: 7px; background: var(--gdown); overflow: hidden; display: flex; }
.band i { display: block; height: 100%; min-width: 2px; }
.band i + i { box-shadow: -1px 0 0 var(--surface); }
.band .u { background: var(--g1000); } .band .s { background: var(--g100); } .band .d { background: var(--gdown); }
.band .x { background: repeating-linear-gradient(135deg, var(--soft) 0 4px, var(--line) 4px 6px); }
.lh .axis { display: flex; justify-content: space-between; color: var(--muted); font: max(10.5px, calc(10px * var(--fs))) ui-monospace, SFMono-Regular, Menlo, monospace; }
.ev { border: 1px solid var(--line); border-radius: 10px; overflow-y: auto; max-height: 128px; }
.ev > div { display: grid; grid-template-columns: 14px 1fr auto; gap: 10px; align-items: center; padding: 6px 12px; border-top: 1px solid var(--line-2); font-size: max(10.5px, calc(13px * var(--fs))); }
.ev > div:first-child { border-top: 0; } .ev > div i { width: 10px; height: 10px; border-radius: 50%; }
.ev .u i { background: var(--g1000); } .ev .s i { background: var(--g100); } .ev .d i { background: var(--soft); border: 2px solid var(--muted); }
.issue.info { background: var(--neutral-soft); color: var(--tag-text); } .issue.ok { background: var(--ok-soft); color: var(--ok); }
.issue svg { width: 18px; height: 18px; margin-top: 1px; }
.lookwrap { position: relative; }
.icon-btn { width: 40px; height: 40px; border-radius: 50%; display: inline-grid; place-items: center; color: var(--muted); border: 0; background: none; cursor: pointer; }
.icon-btn:hover, .icon-btn[aria-expanded="true"] { background: var(--accent-soft); color: var(--accent-hover); }
.icon-btn:focus-visible, .look-menu button:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.look-menu { position: absolute; right: 0; top: calc(100% + 4px); z-index: 5; display: grid; min-width: 260px; padding: 8px 0; gap: 4px;
  background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 6px 24px rgb(0 0 0 / 18%); }
.lookgroup { display: grid; padding: 4px 0; }
.lookgroup + .lookgroup { border-top: 1px solid var(--line-2); }
.lookhead { padding: 4px 16px; font-size: max(10.5px, calc(11px * var(--fs))); color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.look-menu button { display: flex; align-items: center; gap: 12px; min-height: 38px; padding: 0 16px; border: 0; background: none; cursor: pointer; text-align: left; white-space: nowrap; font-size: calc(14px * var(--fs)); }
.look-menu button:hover { background: var(--soft); }
.look-menu button[aria-checked="true"] { color: var(--accent-hover); background: var(--accent-soft); font-weight: 500; }
.look-menu .dot { width: 14px; height: 14px; border-radius: 50%; flex: none; border: 1px solid var(--line); }
.badge { font-size: max(10.5px, calc(11px * var(--fs))); color: var(--muted); border: 1px solid var(--line); border-radius: 10px; padding: 1px 8px; margin-left: 8px; white-space: nowrap; }
.vgrid { display: grid; grid-template-columns: repeat(var(--cols), minmax(17px, 1fr)); gap: 3px; min-width: 460px; }
.vaxis { font: 10px ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted); text-align: center; text-transform: none; letter-spacing: 0; }
.vt { height: 22px; border-radius: 5px; background: var(--soft); border: 1px solid var(--line-2); display: grid; place-items: center; font: 10px ui-monospace, SFMono-Regular, Menlo, monospace; color: transparent; }
.vt.u { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
.vt.g { background: var(--warn-soft); border: 1.5px solid var(--warn); color: var(--warn); }
tr.unused td, tr.unused .badge { color: var(--muted); } tr.unused .mono { opacity: .6; }
.vlegend { display: flex; gap: 18px; flex-wrap: wrap; align-items: center; padding: 12px 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: max(10.5px, calc(12px * var(--fs))); }
.vlegend .vt { display: inline-block; width: 14px; height: 14px; vertical-align: -3px; margin-right: 6px; }
@media (max-width: 700px) {
  .lookwrap { align-self: stretch; }
  .icon-btn { width: auto; padding: 0 14px; gap: 10px; border-radius: 20px; display: inline-flex; align-items: center; }
  .btnlabel { display: inline; font-weight: 500; }
  .look-menu { position: static; margin-top: 4px; min-width: 0; box-shadow: none; }
  .icon-btn { justify-content: flex-start; }
}
`;
