// Tests for the texts of the panel. Run with: node --test tests/js/*.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";

import { TEXTS, translator } from "../../custom_components/tplink_switch_snmp/frontend/texts.js";

const placeholders = (text) => [...String(text).matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

test("German and English have the same keys", () => {
  assert.deepEqual(Object.keys(TEXTS.de).sort(), Object.keys(TEXTS.en).sort());
});

test("a text has the same placeholders in both languages", () => {
  for (const key of Object.keys(TEXTS.de)) {
    assert.deepEqual(placeholders(TEXTS.de[key]), placeholders(TEXTS.en[key]), key);
  }
});

test("a text that counts has a form for exactly one", () => {
  for (const key of ["errorPorts", "slowPorts", "slowNote", "manyBroadcast", "linkChanges", "errorsN", "vlanCount"]) {
    for (const lang of ["de", "en"]) assert.ok(`${key}One` in TEXTS[lang], `${lang}.${key}One`);
  }
});

test("one gets the singular, every other number the plural", () => {
  const de = translator("de");
  assert.equal(de.count("errorPorts", 1), "1 Port mit Fehlern");
  assert.equal(de.count("errorPorts", 2), "2 Ports mit Fehlern");
  assert.equal(de.count("errorPorts", 0), "0 Ports mit Fehlern");
  const en = translator("en");
  assert.equal(en.count("errorPorts", 1), "1 port with errors");
  assert.equal(en.count("errorsN", 1), "1 error");
  assert.equal(en.count("errorsN", 12), "12 errors");
});

test("a text without a singular form falls back to the text itself", () => {
  assert.equal(translator("en").count("overview", 1), "Overview");
  assert.equal(translator("en").count("portsOf", 1, { total: 24 }), "1 of 24 ports");
});

test("placeholders are filled in, an unknown key shows its name", () => {
  assert.equal(translator("en")("portsOf", { n: 3, total: 24 }), "3 of 24 ports");
  assert.equal(translator("de")("doesNotExist"), "doesNotExist");
  assert.equal(translator("fr")("overview"), "Overview"); // another language: English
});
