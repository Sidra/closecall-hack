/** Columns of the council-packet CSV, in file order. */
export const COUNCIL_PACKET_COLUMNS = [
  "id",
  "intersection",
  "PET_s",
  "road_users",
  "model_flag",
  "ai_label_blind",
  "explanation",
  "clip_url",
] as const;

export type CouncilPacketColumn = (typeof COUNCIL_PACKET_COLUMNS)[number];
export type CouncilPacketRow = Record<CouncilPacketColumn, string>;

// OWASP CSV-injection prefixes, including tab and carriage return.
const FORMULA_PREFIX = /^[=+\-@\t\r]/;

/** Quote a field for CSV and stop spreadsheet apps treating it as a formula. */
export function csvCell(value: string): string {
  let s = value;
  if (FORMULA_PREFIX.test(s)) s = `'${s}`;
  return `"${s.replace(/"/g, '""')}"`;
}

/** Build a council-packet CSV. Every field is quoted; rows are CRLF-separated. */
export function councilPacketCsv(rows: readonly CouncilPacketRow[]): string {
  const lines = [
    COUNCIL_PACKET_COLUMNS.map(csvCell).join(","),
    ...rows.map((row) => COUNCIL_PACKET_COLUMNS.map((col) => csvCell(row[col])).join(",")),
  ];
  return `${lines.join("\r\n")}\r\n`;
}
