import "server-only";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import type { Eval, Memo, Row, Run } from "./types";

export type { Eval, Memo, Row, Run, Source } from "./types";
export { pretty } from "./types";

const dir = path.join(process.cwd(), "public", "data");
function load<T>(name: string, fallback: T): T {
  const p = path.join(dir, name);
  if (!existsSync(p)) return fallback;
  return JSON.parse(readFileSync(p, "utf8")) as T;
}
export const getRun = () => load<Run | null>("run.json", null);
export const getLedger = () => load<Row[]>("ledger.json", []);
export const getMemos = () => load<Memo[]>("memo.json", []);
export const getEval = () => load<Eval | null>("eval.json", null);
export const getVectors = () => load<Record<string, number[]>>("vectors.json", {});

