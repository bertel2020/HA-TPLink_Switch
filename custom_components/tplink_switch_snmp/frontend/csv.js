// CSV the way a spreadsheet reads it: semicolons, quoted where needed, a decimal comma in German.

/** One cell. A cell that starts like a formula gets a quote in front, so it is not run. */
export function csvCell(value) {
  let text = value == null ? "" : String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return /[";\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

/** A number as text, with a decimal comma for German. */
export function csvNumber(value, language) {
  if (value == null) return "";
  return String(language).startsWith("de") ? String(value).replace(".", ",") : String(value);
}

/** Rows of cells as one CSV text; lines end with CR LF. */
export function csvText(rows) {
  return rows.map((row) => row.map(csvCell).join(";")).join("\r\n");
}
