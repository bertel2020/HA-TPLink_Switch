// Tests for the CSV the panel exports. Run with: node --test tests/js/*.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";

import { csvCell, csvNumber, csvText } from "../../custom_components/tplink_switch_snmp/frontend/csv.js";

test("plain values stay as they are, empty ones are empty", () => {
  assert.equal(csvCell("NAS"), "NAS");
  assert.equal(csvCell(12), "12");
  assert.equal(csvCell(null), "");
  assert.equal(csvCell(undefined), "");
});

test("semicolons, quotes and line breaks are quoted", () => {
  assert.equal(csvCell("a;b"), '"a;b"');
  assert.equal(csvCell('say "hi"'), '"say ""hi"""');
  assert.equal(csvCell("two\nlines"), '"two\nlines"');
});

test("a cell that looks like a formula is defused", () => {
  for (const evil of ["=1+1", "+SUM(A1)", "-2+3", "@cmd", "\tx", "=HYPERLINK(\"http://x\")"]) {
    assert.ok(csvCell(evil).replace(/^"/, "").startsWith("'"), evil);
  }
  assert.equal(csvCell("name-with-dash"), "name-with-dash");
});

test("German numbers get a decimal comma, others a point", () => {
  assert.equal(csvNumber(2.5, "de"), "2,5");
  assert.equal(csvNumber(2.5, "de-AT"), "2,5");
  assert.equal(csvNumber(2.5, "en"), "2.5");
  assert.equal(csvNumber(null, "de"), "");
  assert.equal(csvNumber(7, "de"), "7");
});

test("rows are joined with semicolons and CR LF", () => {
  assert.equal(csvText([["Port", "Name"], [1, "a;b"], [2, ""]]), 'Port;Name\r\n1;"a;b"\r\n2;');
});
