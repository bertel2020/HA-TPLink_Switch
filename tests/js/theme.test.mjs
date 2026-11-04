// Tests for the look of the panel: the palettes are complete and the styles only use colours
// that exist. Run with: node --test tests/js/*.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  DEFAULTS,
  MODES,
  SCHEMES,
  SIZES,
  cleanPrefs,
  isDark,
  tokens,
} from "../../custom_components/tplink_switch_snmp/frontend/theme.js";

const STYLES = readFileSync(
  new URL("../../custom_components/tplink_switch_snmp/frontend/styles.js", import.meta.url),
  "utf8",
);
// custom properties the styles define themselves
const LOCAL = new Set(["--cols", "--fs"]);

test("every scheme defines the same tokens, each for light and dark", () => {
  const names = Object.keys(SCHEMES.ocean).sort();
  for (const [scheme, palette] of Object.entries(SCHEMES)) {
    assert.deepEqual(Object.keys(palette).sort(), names, scheme);
    for (const [name, pair] of Object.entries(palette)) {
      assert.equal(pair.length, 2, `${scheme}.${name}`);
      assert.match(pair[0], /^#[0-9a-f]{6}$/i);
      assert.match(pair[1], /^#[0-9a-f]{6}$/i);
    }
  }
});

test("the styles use only colours and sizes that the theme provides", () => {
  const provided = new Set(Object.keys(tokens(DEFAULTS, false)));
  const used = new Set([...STYLES.matchAll(/var\((--[a-z0-9-]+)/g)].map((m) => m[1]));
  const missing = [...used].filter((name) => !provided.has(name) && !LOCAL.has(name));
  assert.deepEqual(missing, []);
});

test("light and dark differ in every scheme", () => {
  for (const scheme of Object.keys(SCHEMES)) {
    const light = tokens({ ...DEFAULTS, scheme }, false);
    const dark = tokens({ ...DEFAULTS, scheme }, true);
    assert.notEqual(light["--bg"], dark["--bg"], scheme);
    assert.notEqual(light["--text"], dark["--text"], scheme);
  }
});

test("receive follows the accent of the scheme, transmit does not", () => {
  const forest = tokens({ ...DEFAULTS, scheme: "forest" }, false);
  assert.equal(forest["--rx"], forest["--accent"]);
  assert.notEqual(forest["--tx"], forest["--accent"]);
});

test("the font size factor is relative to the normal size", () => {
  assert.equal(tokens({ ...DEFAULTS, size: "normal" }, false)["--fs"], "1");
  assert.ok(Number(tokens({ ...DEFAULTS, size: "small" }, false)["--fs"]) < 1);
  assert.ok(Number(tokens({ ...DEFAULTS, size: "large" }, false)["--fs"]) > 1);
  assert.deepEqual(Object.keys(SIZES), ["small", "normal", "large"]);
});

test("a stored choice that is not valid falls back to the defaults", () => {
  assert.deepEqual(cleanPrefs(null), DEFAULTS);
  assert.deepEqual(cleanPrefs({ scheme: "neon", mode: "sepia", size: "huge" }), DEFAULTS);
  assert.deepEqual(cleanPrefs({ scheme: "forest", mode: "dark", size: "large" }), {
    scheme: "forest",
    mode: "dark",
    size: "large",
  });
});

test("an explicit mode wins over Home Assistant's, auto follows it", () => {
  assert.ok(MODES.includes("auto"));
  assert.equal(isDark({ ...DEFAULTS, mode: "dark" }, false), true);
  assert.equal(isDark({ ...DEFAULTS, mode: "light" }, true), false);
  assert.equal(isDark({ ...DEFAULTS, mode: "auto" }, true), true);
  assert.equal(isDark({ ...DEFAULTS, mode: "auto" }, false), false);
});

test("no text is set in a fixed size that ignores the font size choice", () => {
  // every font-size goes through the factor; relative sizes (em, %) follow their parent's
  const fixed = [...STYLES.matchAll(/font-size:\s*(?!\s|max\(|calc\(|[\d.]+(?:em|%))([^;]+);/g)].map((m) => m[0]);
  assert.deepEqual(fixed, []);
});
