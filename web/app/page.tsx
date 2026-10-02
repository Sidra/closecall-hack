import Link from "next/link";
import { getRun, getEval, getLedger } from "@/lib/data";
import { mediaSrc } from "@/lib/types";
import { Headline } from "@/components/Headline";
import { HumanLine } from "@/components/HumanLine";
import { reviewSummary } from "@/lib/review";

export const dynamic = "force-dynamic";

export default function Home() {
  const run = getRun();
  const ev = getEval();
  const t = run?.totals;
  const human = reviewSummary();
  // Hero = an AI-labelled near-miss (blind, pre-registered label); its model verdict is shown as-is.
  const hero = getLedger().filter((r) => r.label === "near_miss")
    .sort((a, b) => Number(b.verdict === "near_miss") - Number(a.verdict === "near_miss") || a.pet_s - b.pet_s)[0];
  return (
    <>
      <section className="section">
        <div className="wrap fade hero">
          <div>
          <div className="eyebrow">A flight recorder for intersections</div>
          <h1 style={{ marginTop: 14, maxWidth: 900 }}>From intersection video to an auditable safety decision.</h1>
          {run && <div style={{ marginTop: 16 }}><Headline ev={ev} run={run} /><HumanLine s={human} /></div>}
          <div style={{ display: "flex", gap: 10, marginTop: 22, flexWrap: "wrap" }}>
            <Link className="btn primary" href="/demo">▶ Run the demo</Link>
            <Link className="btn" href="/ledger">Open the ledger</Link>
            <Link className="btn" href="/play">🎮 Spot the near-miss</Link>
          </div>
          <p className="muted" style={{ marginTop: 18, fontSize: 14.5, maxWidth: 620 }}>
            CloseCall finds possible near-misses in traffic-camera video for an engineer to review: a tracker measures every
            close pass, vision models triage the clips for an engineer to review, and the fix memo cites the labelled near-misses.
            Heads and plates are pixelated in tracked boxes; untracked people may not be. No identity is ever extracted.
          </p>
          </div>
          {hero && (
            <figure className="hud">
              <video src={mediaSrc(hero.clip)} poster={mediaSrc(hero.keyframes[1] ?? hero.keyframes[0])} autoPlay muted loop playsInline />
              <div className="hud-tag"><span className="dot" /> AI-LABELLED NEAR-MISS · PET {hero.pet_s.toFixed(2)} s</div>
              <figcaption><b style={{ color: "var(--amber)" }}>A {hero.a_cls}</b> → <b style={{ color: "var(--cyan)" }}>B {hero.b_cls}</b> · {hero.intersection}<br />
                <span className="muted">Label: near-miss (AI, blind, pre-registered). Model ({hero.verifier_version ?? "v1"}): <b>{hero.verdict === "near_miss" ? "flagged it" : hero.verdict === "unclear" ? "unclear" : "missed it"}</b> · “{hero.explanation}”</span><br />
                <span className="faint mono" style={{ fontSize: 12 }}>{hero.verifier_model.split("/").pop()} · heads + plates pixelated in tracked boxes</span></figcaption>
            </figure>
          )}
        </div>
        <div className="wrap">
          {t && (
            <div className="funnel" style={{ marginTop: 40 }}>
              <div><div className="k">Footage watched</div><div className="big">{Math.round(t.duration_s)}s</div><div className="muted">{Object.keys(run!.funnel).length} intersections · {t.tracks} tracks</div></div>
              <div><div className="k">Naive flags (PET &lt; 4 s)</div><div className="big">{t.naive}</div><div className="muted">what a pixel tracker alone reports</div></div>
              <div><div className="k">Plausible conflicts</div><div className="big">{t.events}</div><div className="muted">crossing paths, both moving</div></div>
              <div><div className="k">Flagged for review</div><div className="big" style={{ color: "var(--red)" }}>{t.verified}</div><div className="muted">{t.confirmed_and_flagged ?? 0} of the {t.confirmed ?? 0} AI-labelled near-misses are among them</div></div>
            </div>
          )}
          {t && <p className="faint mono" style={{ fontSize: 12, marginTop: 10, lineHeight: 1.4 }}>Measured on this run ({run!.generated_at}). Footage: CC BY-SA 4.0 public intersection clips from Wikimedia Commons, not a live city feed.</p>}
        </div>
      </section>

      <section className="section">
        <div className="wrap grid g2" style={{ gap: 28 }}>
          <div>
            <div className="eyebrow">01 · The problem</div>
            <h2 style={{ marginTop: 10 }}>Crash data only arrives after someone is hurt.</h2>
            <p className="muted" style={{ marginTop: 12 }}>
              A city traffic engineer asking council to redesign an intersection “where nobody has died” has no evidence
              yet. The camera on the pole has recorded every close call for years, but nobody watches it: near-miss
              studies mean a person reviewing hours of video by hand, so they are rare and expensive.
            </p>
          </div>
          <div>
            <div className="eyebrow">02 · The solution</div>
            <h2 style={{ marginTop: 10 }}>Measure every close call. Triage the likely ones.</h2>
            <p className="muted" style={{ marginTop: 12 }}>
              A cheap first stage (YOLO26 tracking + post-encroachment time) flags every pair of road users that
              passed through the same spot within 4 seconds. Only those clips go to vision models, which reject most screen-space illusions and flag the likely conflicts, in plain words, for an engineer to review.
            </p>
          </div>
          <div>
            <div className="eyebrow">03 · Why it matters</div>
            <h2 style={{ marginTop: 10 }}>Evidence before the funeral, not after.</h2>
            <p className="muted" style={{ marginTop: 12 }}>
              Near-misses happen far more often than crashes, so they show a dangerous design in weeks instead of years.
              The ledger turns them into evidence a council can read: the clip, the timing, the explanation, the fix.
            </p>
          </div>
          <div>
            <div className="eyebrow">04 · How it’s used</div>
            <h2 style={{ marginTop: 10 }}>Ask in plain words. Get the clips and the memo.</h2>
            <p className="muted" style={{ marginTop: 12 }}>
              The engineer (or the consultancy doing the study) types “turning cars cutting across pedestrians”, gets the
              matching clips with timing and explanation, and exports a fix memo that cites every clip. Every step is
              traced in W&amp;B Weave so the result can be audited.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <div className="eyebrow">How it works</div>
          <div className="grid g4" style={{ marginTop: 18 }}>
            {[
              ["YOLO26 + ByteTrack", "Tracks every car, bus, truck, cyclist and pedestrian; computes post-encroachment time per pair."],
              ["NVIDIA Nemotron + embeddings", "Nemotron-3 Omni was the video verifier in v1 and v2; nemotron-3-embed-1b powers plain-language search; the memo model is Nemotron-3.5."],
              ["VAST Data (adapter, stand-in)", "Stand-in on this run: the VastStore adapter (clips, ledger rows, vectors, VSS ingest with a near-miss prompt) is written but not yet run against VAST."],
              ["W&B Inference + Weave", "Runs the triage vote (Qwen3.6, MiniMax-M3, Gemma-4) on CoreWeave GPUs, drafts the memo, traces every call and scores each verifier against blind labels."],
            ].map(([h, p]) => (
              <div className="card" key={h}><h3>{h}</h3><p className="muted" style={{ margin: "8px 0 0", fontSize: 14 }}>{p}</p></div>
            ))}
          </div>
          {ev && ev.precision !== null && (
            <p style={{ marginTop: 18 }} className="muted">
              Measured precision of the verifier on this run: <b className="mono" style={{ color: "var(--ink)" }}>{Math.round(ev.precision * 100)}%</b> versus <b className="mono" style={{ color: "var(--ink)" }}>{Math.round((ev.baseline_precision ?? 0) * 100)}%</b> if every stage-1 flag were reported. <Link href="/evals">See the eval, misses included →</Link>
            </p>
          )}
        </div>
      </section>
    </>
  );
}
