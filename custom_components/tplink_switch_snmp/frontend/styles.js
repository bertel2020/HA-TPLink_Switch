// The look of the panel: the "ocean" palette of the EnOcean panel, light and dark. The panel
// sets the attribute "dark" on its host when Home Assistant is in dark mode.
export const STYLES = `
:host { display: block; min-height: 100%; --bg: #f4f6f9; --surface: #ffffff; --soft: #f5f7f9; --line: #e1e5ea; --line-2: #eef0f3; --input-line: #c3cbd5;
  --text: #1b1f24; --muted: #5b6270; --accent: #0a6aa8; --accent-hover: #07507f; --accent-soft: #eaf3fa; --on-accent: #fff;
  --neutral-soft: #eef1f4; --tag-text: #3a414c; --ok: #1e6b34; --ok-soft: #e6f4ea; --warn: #8a4b00; --warn-soft: #fff1de;
  --bad: #a1261b; --bad-soft: #fdecea; --focus: #7db8e0; --shadow-c: rgba(16,24,40,.06);
  --g1000: #2e9b57; --g100: #d98a1e; --gdown: #cfd5dc; --rx: #0a6aa8; --tx: #7b5cc9; color-scheme: light;
  background: var(--bg); color: var(--text); font: 14px/1.45 Roboto, system-ui, -apple-system, "Segoe UI", sans-serif; }
:host([dark]) { --bg: #0f1216; --surface: #1b1f24; --soft: #22272e; --line: #2d333b; --line-2: #262c33; --input-line: #3a424c;
  --text: #e6e9ed; --muted: #9aa4b1; --accent: #5bb2ea; --accent-hover: #8ccaf2; --accent-soft: #16324a; --on-accent: #0b1a26;
  --neutral-soft: #2a3038; --tag-text: #c5ccd5; --ok: #7fd49a; --ok-soft: #173a24; --warn: #f2c27a; --warn-soft: #3a2a12;
  --bad: #f2a29a; --bad-soft: #3d1c19; --shadow-c: rgba(0,0,0,.4);
  --g1000: #5fc283; --g100: #f0a24f; --gdown: #3a424c; --rx: #5bb2ea; --tx: #a78bf0; color-scheme: dark; }
* { box-sizing: border-box; }
button, input, select { font: inherit; color: inherit; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; white-space: nowrap; }
.muted { color: var(--muted); } .sub { color: var(--muted); font-size: 12px; }
svg { width: 20px; height: 20px; fill: currentColor; flex: none; }
.topbar { background: var(--surface); border-bottom: 1px solid var(--line); }
.topbar-in { max-width: 1280px; margin: 0 auto; padding: 10px 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.brand { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 500; margin-right: auto; }
.logo { width: 36px; height: 36px; border-radius: 9px; background: #14323f; color: #5fe0c8; display: grid; place-items: center; }
.logo svg { width: 22px; height: 22px; }
.menu { display: none; border: 0; background: none; cursor: pointer; border-radius: 50%; padding: 6px; color: var(--text); }
:host([narrow]) .menu { display: inline-flex; }
nav { display: flex; gap: 2px; flex-wrap: wrap; }
.tab { border: 0; background: none; border-radius: 20px; padding: 8px 16px; font-weight: 500; color: var(--muted); cursor: pointer; }
.tab:hover { color: var(--text); }
.tab[aria-selected="true"] { background: var(--accent-soft); color: var(--accent-hover); }
.chip { min-height: 32px; padding: 0 14px; border-radius: 18px; border: 1px solid var(--input-line); font-size: 13px; font-weight: 500; background: var(--surface); color: var(--text); cursor: pointer; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.chip:hover { background: var(--accent-soft); color: var(--accent-hover); }
.chip[aria-pressed="true"] { border-color: var(--accent); color: var(--accent-hover); background: var(--accent-soft); }
.chip.outline { color: var(--accent); border-color: var(--accent); }
.chip svg { width: 16px; height: 16px; }
.tab:focus-visible, .chip:focus-visible, .port:focus-visible, .rowbtn:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.app { max-width: 1280px; margin: 0 auto; padding: 16px 16px 40px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
.app > * { min-width: 0; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 1px 3px var(--shadow-c); }
.card-h { display: flex; align-items: center; gap: 10px; padding: 14px 20px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.card-h h2 { margin: 0; font-size: 16px; font-weight: 500; }
.grow { flex: 1; }
.live { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 12px; background: var(--ok-soft); color: var(--ok); font-size: 12px; font-weight: 500; }
.live.stale { background: var(--bad-soft); color: var(--bad); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.tag { display: inline-flex; align-items: center; gap: 4px; padding: 1px 8px; border-radius: 10px; font-size: 11px; background: var(--neutral-soft); color: var(--tag-text); white-space: nowrap; }
.tag.ok { background: var(--ok-soft); color: var(--ok); } .tag.warn { background: var(--warn-soft); color: var(--warn); }
.tag.bad { background: var(--bad-soft); color: var(--bad); } .tag.acc { background: var(--accent-soft); color: var(--accent); }
.sw { display: flex; align-items: center; gap: 16px; padding: 18px 20px; flex-wrap: wrap; }
.sw-icon { width: 44px; height: 44px; border-radius: 10px; background: var(--accent-soft); color: var(--accent); display: grid; place-items: center; }
.sw-icon svg { width: 26px; height: 26px; }
.sw-name { font-size: 16px; font-weight: 500; }
.sw-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: var(--muted); }
.sw-meta .on { color: var(--ok); font-weight: 500; display: inline-flex; align-items: center; gap: 6px; }
.sw-meta .off { color: var(--bad); font-weight: 500; display: inline-flex; align-items: center; gap: 6px; }
.stats { margin-left: auto; display: flex; flex-wrap: wrap; align-items: center; }
.stat { padding: 0 20px; border-left: 1px solid var(--line); min-width: 112px; }
.stat b { font-size: 17px; font-weight: 500; } .stat span { font-size: 12px; color: var(--muted); }
.stat .sub { display: block; }
.details { padding: 0 20px 18px; }
.kv { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 6px 28px; border-top: 1px solid var(--line); padding-top: 14px; }
.kv div { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; }
.kv span:first-child { color: var(--muted); }
.swpick { border: 1px solid var(--input-line); border-radius: 18px; background: var(--surface); padding: 4px 12px; min-height: 32px; }
.face { padding: 18px 20px 20px; }
.plate { background: var(--soft); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; display: grid; gap: 8px; overflow-x: auto; }
.plate-row { display: grid; grid-template-columns: repeat(var(--cols, 12), minmax(46px, 1fr)); gap: 8px; min-width: 640px; }
.port { all: unset; box-sizing: border-box; cursor: pointer; border-radius: 8px; border: 1px solid var(--line); background: var(--surface); padding: 5px 4px 6px; text-align: center; display: grid; gap: 3px; position: relative; }
.port:hover { border-color: var(--accent); }
.port .n { font-size: 11px; color: var(--muted); }
.port .jack { height: 18px; border-radius: 4px; border: 2px solid var(--gdown); background: color-mix(in srgb, var(--gdown) 25%, transparent); }
.port.s1000 .jack { border-color: var(--g1000); background: color-mix(in srgb, var(--g1000) 28%, transparent); }
.port.s100 .jack { border-color: var(--g100); background: color-mix(in srgb, var(--g100) 28%, transparent); }
.port.s10 .jack { border-color: var(--bad); background: color-mix(in srgb, var(--bad) 22%, transparent); }
.port .v { font-size: 10px; color: var(--muted); height: 12px; }
.port.sel { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft), 0 0 0 3px var(--accent); }
.port.err::after { content: ""; position: absolute; top: 4px; right: 4px; width: 8px; height: 8px; border-radius: 50%; background: var(--bad); }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--muted); margin-top: 12px; }
.legend i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: -2px; margin-right: 6px; border: 2px solid; }
.pd { padding: 16px 20px 20px; display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 20px; }
@media (max-width: 820px) { .pd { grid-template-columns: minmax(0, 1fr); } .stats { margin-left: 0; } .stat:first-child { border-left: 0; padding-left: 0; } }
.pd h3 { margin: 0 0 4px; font-size: 15px; font-weight: 500; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.nameedit { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.nameedit input { border: 1px solid var(--input-line); border-radius: 18px; padding: 4px 12px; min-height: 32px; background: var(--surface); min-width: 220px; }
.spark { width: 100%; height: 96px; background: var(--soft); border: 1px solid var(--line); border-radius: 10px; display: block; }
.spark path.f { fill-opacity: .14; stroke: none; } .spark path.l { fill: none; stroke-width: 1.6; vector-effect: non-scaling-stroke; }
.nodata { height: 96px; display: grid; place-items: center; background: var(--soft); border: 1px dashed var(--line); border-radius: 10px; color: var(--muted); font-size: 12px; text-align: center; padding: 0 12px; }
.lg { display: flex; gap: 14px; font-size: 12px; color: var(--muted); margin-top: 6px; flex-wrap: wrap; }
.lg i { display: inline-block; width: 10px; height: 3px; border-radius: 2px; vertical-align: 3px; margin-right: 6px; }
.maclist { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; max-height: 280px; overflow-y: auto; }
.maclist div { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 7px 12px; border-top: 1px solid var(--line-2); font-size: 13px; }
.maclist div:first-child { border-top: 0; }
.tools { display: flex; gap: 8px; padding: 12px 16px; flex-wrap: wrap; border-bottom: 1px solid var(--line); align-items: center; }
.search { flex: 1 1 240px; min-width: 200px; display: flex; align-items: center; gap: 8px; border: 1px solid var(--input-line); border-radius: 18px; padding: 0 14px; min-height: 36px; background: var(--surface); }
.search input { all: unset; flex: 1; min-width: 0; }
.search svg { color: var(--muted); width: 18px; height: 18px; }
.infobar { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; font-size: 12px; color: var(--muted); border-bottom: 1px solid var(--line); gap: 12px; flex-wrap: wrap; }
.warnnote { color: var(--warn); font-weight: 500; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); font-weight: 500; padding: 10px 12px; background: var(--soft); border-bottom: 1px solid var(--line); white-space: nowrap; }
td { padding: 10px 12px; border-bottom: 1px solid var(--line-2); vertical-align: middle; }
th:first-child, td:first-child { padding-left: 20px; } th:last-child, td:last-child { padding-right: 20px; }
tr.row:hover td { background: var(--soft); }
tr.down td { color: var(--muted); }
td.num, th.num { text-align: right; }
.pn { font-weight: 500; } .pn small { display: block; font-weight: 400; color: var(--muted); font-size: 12px; }
.bar { display: flex; align-items: center; gap: 8px; justify-content: flex-end; }
.bar .b { width: 70px; height: 6px; border-radius: 3px; background: var(--neutral-soft); overflow: hidden; }
.bar .b i { display: block; height: 100%; border-radius: 3px; }
.bar .sub { white-space: nowrap; min-width: 3.4em; text-align: right; }
.rowbtn { all: unset; cursor: pointer; color: var(--muted); border-radius: 6px; padding: 4px; display: inline-flex; }
.rowbtn:hover { color: var(--accent); background: var(--accent-soft); }
.empty { padding: 36px; text-align: center; color: var(--muted); }
.error { padding: 20px; color: var(--bad); }
.twocol { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
@media (max-width: 900px) { .twocol { grid-template-columns: minmax(0, 1fr); } }
.toplist { padding: 6px 20px 14px; display: grid; gap: 10px; }
.toprow { display: grid; grid-template-columns: minmax(80px, 150px) 1fr 76px; gap: 12px; align-items: center; font-size: 13px; }
.toprow .b { height: 8px; border-radius: 4px; background: var(--neutral-soft); overflow: hidden; }
.toprow .b i { display: block; height: 100%; background: var(--accent); border-radius: 4px; }
.issues { padding: 6px 20px 16px; display: grid; gap: 8px; }
.issue { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 10px; font-size: 13px; }
.issue.warn { background: var(--warn-soft); color: var(--warn); } .issue.ok { background: var(--ok-soft); color: var(--ok); }
.issue svg { width: 18px; height: 18px; margin-top: 1px; }
`;
