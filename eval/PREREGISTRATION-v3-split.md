# Pre-registration: dev/test split for verifier development (v3+)

Committed before any v3 variant is run. Labels are unchanged.

- **Split:** `eval/split.json`, seed 20261002, **stratified by (clip, label)**: each clip's events of each label are shuffled with the seed and alternated between dev and test.
- **Why not a pure by-clip split:** there are only 4 clips, and 3 of the 4 labelled near-misses come from one clip (Tyumen, Profsoyuznaya). A by-clip split would leave the test set with 0 or 1 positives, and nothing could be measured. **The cost:** dev and test share scenes, so a variant tuned on dev may look better on test than it would on a new intersection. This is stated next to every test number.
- **Protocol:**
  - Every variant (input format × model × rule) is tuned and compared on **dev only**.
  - The chosen variant is committed (prompt, model, rule, threshold) **before** it runs on test.
  - **Test** is reported once. A separate, labelled line reports all 51.
- **Prior runs:** v1 and v2 ran on all 51 before this split existed. They stay reported as full-set results.
