import { test } from "node:test";
import assert from "node:assert/strict";
import { councilPacketCsv, type CouncilPacketRow } from "../lib/councilPacket.ts";

test("council packet CSV escapes quotes, commas, and newlines, and guards formula injection", () => {
  const row: CouncilPacketRow = {
    id: "pieix-1",
    intersection: 'Pie-IX, "Sherbrooke"',
    PET_s: "1.25",
    road_users: "bicycle then bus",
    model_flag: "=1+1",
    ai_label_blind: "+near_miss",
    explanation: "paths cross\nat the circle",
    clip_url: "-https://example.test/clips/a.mp4",
  };
  const injected: CouncilPacketRow = {
    id: "@SUM(A1)",
    intersection: "Plain",
    PET_s: "0.50",
    road_users: "car then person",
    model_flag: "near_miss",
    ai_label_blind: "not_near_miss",
    explanation: "clear",
    clip_url: "/clips/b.mp4",
  };

  const csv = councilPacketCsv([row, injected]);

  assert.equal(
    csv,
    [
      '"id","intersection","PET_s","road_users","model_flag","ai_label_blind","explanation","clip_url"',
      '"pieix-1","Pie-IX, ""Sherbrooke""","1.25","bicycle then bus","\'=1+1","\'+near_miss","paths cross\nat the circle","\'-https://example.test/clips/a.mp4"',
      '"\'@SUM(A1)","Plain","0.50","car then person","near_miss","not_near_miss","clear","/clips/b.mp4"',
      "",
    ].join("\r\n"),
  );
});

test("tab and carriage-return prefixes are neutralised too", () => {
  const base = { id: "x", intersection: "i", PET_s: "1", road_users: "r", model_flag: "f", ai_label_blind: "l", clip_url: "/c" };
  const csv = councilPacketCsv([{ ...base, explanation: "\t=HYPERLINK(1)" }, { ...base, explanation: "\r=1" }]);
  assert.ok(csv.includes('"\'\t=HYPERLINK(1)"'));
  assert.ok(csv.includes('"\'\r=1"'));
});
