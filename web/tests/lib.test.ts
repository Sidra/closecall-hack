import { test } from "node:test";
import assert from "node:assert/strict";
import { isIdentityQuery, keywordScore, cosine } from "../lib/search.ts";
import { mediaSrc } from "../lib/types.ts";

test("identity questions are refused", () => {
  for (const q of ["Who was driving the white car?", "read me its plate", "identify the cyclist", "licence number"]) assert.equal(isIdentityQuery(q), true, q);
  for (const q of ["turning car cutting across a pedestrian", "left-turn conflicts with cyclists"]) assert.equal(isIdentityQuery(q), false, q);
});

test("keyword fallback scores overlapping terms", () => {
  const row = { search_text: "car then person. turn vs pedestrian. The car turns across the crosswalk." } as never;
  assert.ok(keywordScore("pedestrian crosswalk", row) > 0.9);
  assert.equal(keywordScore("bus lane", row), 0);
});

test("cosine is 1 for identical vectors and 0 for orthogonal", () => {
  assert.equal(cosine([1, 2, 3], [1, 2, 3]).toFixed(6), "1.000000");
  assert.equal(cosine([1, 0], [0, 1]), 0);
});

test("mediaSrc only allows anonymised clips and keyframes", () => {
  assert.equal(mediaSrc("clips/pieix-1-2.mp4"), "/clips/pieix-1-2.mp4");
  assert.equal(mediaSrc("clips/pieix-1-2_k1.jpg"), "/clips/pieix-1-2_k1.jpg");
  for (const bad of ["../etc/passwd", "clips/../x.mp4", "javascript:alert(1)", "https://evil.example/x.mp4", "clips/x.svg", "", null])
    assert.equal(mediaSrc(bad as string), "", String(bad));
});
