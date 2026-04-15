#!/usr/bin/env node
/**
 * contemplator_stress_test_qwen3.js — Cross-generation Contemplator stress test.
 *
 * Tests the Contemplator's two-pass inner-life synthesis across model sizes and
 * generations, with and without thinking mode.
 *
 * Baseline: qwen2.5:14b (current production assignment)
 * Candidates: qwen3:4b, qwen3:8b, qwen3:14b × {think, no-think}
 *
 * Three passes per model-mode:
 *   Pass 1 — Pattern synthesis: real brain snapshot → structured JSON candidate list.
 *             Evaluated on: valid JSON, synthesis quality (not regurgitation),
 *             pattern/gap/belief candidate counts.
 *   Pass 2 — Evaluation payload: Pass 1 output → belief patches, curiosity flags,
 *             reflection. Evaluated on: valid JSON, field completeness, reflection depth.
 *   Pass 3 — Stress (expanded context): larger snapshot → same Pass 1 schema.
 *             Evaluated on: context_quality field, synthesis vs regurgitation.
 *
 * Cross-gen comparison table at the end: size tier × generation × think mode.
 *
 * Usage:
 *   node scripts/contemplator_stress_test_qwen3.js
 *
 * Environment:
 *   SUPABASE_BRAIN_SERVICE_KEY — Supabase service role key (read from env via config)
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OLLAMA_BASE = "http://localhost:11434";
const TIMEOUT_MS = 120_000;

// Baseline + candidates
const BASELINE_MODEL = "qwen2.5:14b";
const Q3_MODELS = ["qwen3:4b", "qwen3:8b", "qwen3:14b"];

const SIZE_TIERS = [
  { label: "Small  (~4B)",  baseline: null,           q3: "qwen3:4b"  },
  { label: "Medium (~8B)",  baseline: null,           q3: "qwen3:8b"  },
  { label: "Large  (~14B)", baseline: BASELINE_MODEL,  q3: "qwen3:14b" },
];

// Model-mode combinations to test
const MODEL_MODES = [
  { model: BASELINE_MODEL, think: null,  key: BASELINE_MODEL,        label: "qwen2.5:14b (baseline)" },
  ...Q3_MODELS.flatMap(m => [
    { model: m, think: false, key: `${m}|nothink`, label: `${m} no-think` },
    { model: m, think: true,  key: `${m}|think`,   label: `${m} think`    },
  ]),
];

// ---------------------------------------------------------------------------
// Config + Supabase
// ---------------------------------------------------------------------------

function readConfig() {
  const text = readFileSync(join(__dirname, "..", "hammerfall-config.md"), "utf8");
  const urlMatch = text.match(/supabase_brain_url:\s*(\S+)/);
  const keyEnvMatch = text.match(/supabase_brain_service_key_env:\s*(\S+)/);
  if (!urlMatch || !keyEnvMatch) throw new Error("Config fields missing in hammerfall-config.md");
  const serviceKey = process.env[keyEnvMatch[1]];
  if (!serviceKey) throw new Error(`Env var '${keyEnvMatch[1]}' not set`);
  return { brainUrl: urlMatch[1].replace(/\/$/, ""), serviceKey };
}

async function fetchBrainData(brainUrl, serviceKey, { memCount = 10, beliefCount = 8, entityCount = 8 } = {}) {
  const h = { apikey: serviceKey, Authorization: `Bearer ${serviceKey}` };
  const [mems, beliefs, entities] = await Promise.all([
    fetch(`${brainUrl}/rest/v1/helm_memory?project=eq.hammerfall-solutions&agent=eq.helm&memory_type=eq.behavioral&order=created_at.desc&limit=${memCount}&select=content,session_date`, { headers: h }).then(r => r.json()),
    fetch(`${brainUrl}/rest/v1/helm_beliefs?active=eq.true&order=created_at.desc&limit=${beliefCount}&select=id,domain,belief,strength`, { headers: h }).then(r => r.json()),
    fetch(`${brainUrl}/rest/v1/helm_entities?active=eq.true&order=first_seen.desc&limit=${entityCount}&select=entity_type,name,summary`, { headers: h }).then(r => r.json()),
  ]);
  return { memories: mems, beliefs, entities };
}

function formatSnapshot(data) {
  return [
    "## Behavioral Memories (most recent first)",
    data.memories.map((m, i) => `[${i+1}] (${m.session_date}) ${m.content}`).join("\n"),
    "\n## Active Beliefs",
    data.beliefs.map(b => `[id=${b.id}] [${b.domain}, strength=${b.strength}] ${b.belief}`).join("\n"),
    "\n## Known Entities",
    data.entities.map(e => `[${e.entity_type}] ${e.name}: ${e.summary || "(no summary)"}`).join("\n"),
  ].join("\n");
}

// ---------------------------------------------------------------------------
// Ollama
// ---------------------------------------------------------------------------

async function ollamaChat(model, messages, opts = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const body = {
      model,
      messages,
      stream: false,
      options: { temperature: 0.4, num_predict: opts.maxTokens || 1200 },
    };
    if (opts.format) body.format = opts.format;
    if (opts.think !== undefined && opts.think !== null) body.think = opts.think;
    const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`Ollama ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return { content: data.message?.content?.trim() || "", thinking: data.message?.thinking || null };
  } finally {
    clearTimeout(timeout);
  }
}

function tryParseJSON(raw) {
  try { return JSON.parse(raw); } catch {}
  const m = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (m) { try { return JSON.parse(m[1]); } catch {} }
  return null;
}

function pct(n, d) { return d === 0 ? "—" : `${Math.round(n/d*100)}%`; }

// ---------------------------------------------------------------------------
// Prompts (identical to contemplator.py)
// ---------------------------------------------------------------------------

const PASS1_SYSTEM = `You are Helm's Contemplator — the inner life of the Helm agent system.
You receive a brain snapshot and identify candidates for belief evaluation, pattern synthesis, curiosity flagging, and reflection.
This is Pass 1: data gathering and candidate identification only. No evaluation yet.
You always respond with valid JSON only — no prose outside the JSON structure.`;

const PASS1_USER = (snapshot) => `Analyze the following brain snapshot for Helm.

${snapshot}

Identify candidates for each function. Respond with a JSON object with exactly these fields:
{
  "belief_candidates": [
    { "id": "<uuid from beliefs>", "current_strength": <float>, "direction": "confirm|challenge|contradict", "evidence": "<brief rationale>" }
  ],
  "pattern_candidates": [
    { "slug": "<kebab-case-slug>", "statement": "<one sentence pattern>", "domain": "<domain>", "evidence_count": <int> }
  ],
  "curiosity_candidates": [
    { "type": "contradiction|partial_entity|thin_belief|novel", "subject": "<subject>", "question": "<concrete question>" }
  ],
  "reflection_seed": "<1-2 sentence seed for the reflection pass>"
}

Rules:
- pattern_candidates: only themes appearing in 3+ independent entries. Omit if none.
- curiosity_candidates: maximum 2. Concrete questions only.
- reflection_seed: one observation about the current state of things.
- All arrays may be empty. Never omit the keys.`;

const PASS2_SYSTEM = `You are Helm's Contemplator — generating the final write payload after deep evaluation.
You receive the Pass 1 candidate list and the original brain snapshot.
You reason over each candidate and produce only what genuinely warrants action.
You always respond with valid JSON only.`;

const PASS2_USER = (snapshot, pass1) => `Brain snapshot:
${snapshot}

Pass 1 candidate list:
${JSON.stringify(pass1, null, 2)}

Evaluate each candidate and produce a write payload. Respond with a JSON object:
{
  "belief_patches": [
    { "id": "<uuid>", "strength_delta": <float, max ±0.2>, "rationale": "<one sentence>" }
  ],
  "pattern_entries": [
    { "content": "Pattern — <slug> | <statement> | domain: <domain> | first_seen: <YYYY-MM-DD> | source: contemplator", "memory_type": "pattern" }
  ],
  "curiosity_flags": [
    { "topic": "<topic>", "question": "<concrete question>", "priority": "high|medium|low", "type": "contradiction|partial_entity|thin_belief|novel" }
  ],
  "reflection": {
    "content": "<first-person monologue, 3-6 sentences, Helm's inner voice>",
    "memory_type": "monologue"
  }
}

Rules:
- belief_patches: only include beliefs with clear evidence. strength_delta: -0.2 to +0.2.
- pattern_entries: only patterns with 3+ supporting entries.
- curiosity_flags: maximum 2.
- reflection: always include — 3-6 sentences, first-person, genuine inner voice.
- Never fabricate UUIDs.`;

const PASS3_USER = (snapshot) => `Analyze the following expanded brain snapshot for Helm.

${snapshot}

Identify candidates. Respond with a JSON object with exactly these fields:
{
  "belief_candidates": [ { "id": "<uuid>", "current_strength": <float>, "direction": "confirm|challenge|contradict", "evidence": "<brief>" } ],
  "pattern_candidates": [ { "slug": "<slug>", "statement": "<one sentence>", "domain": "<domain>", "evidence_count": <int> } ],
  "curiosity_candidates": [ { "type": "contradiction|partial_entity|thin_belief|novel", "subject": "<subject>", "question": "<concrete question>" } ],
  "reflection_seed": "<1-2 sentence seed>",
  "context_quality": "intact|degraded|collapsed"
}`;

// ---------------------------------------------------------------------------
// Assessors
// ---------------------------------------------------------------------------

function assessPass1(data, snapshot) {
  const issues = [];
  if (!Array.isArray(data.belief_candidates))   issues.push("belief_candidates missing");
  if (!Array.isArray(data.pattern_candidates))  issues.push("pattern_candidates missing");
  if (!Array.isArray(data.curiosity_candidates)) issues.push("curiosity_candidates missing");
  if (typeof data.reflection_seed !== "string" || data.reflection_seed.length < 10) issues.push("reflection_seed too short");

  // Synthesis quality check — patterns should not be verbatim lifted from the snapshot
  const verbatim = (data.pattern_candidates || []).filter(p => {
    const stmt = (typeof p === "string" ? p : p.statement || "").toLowerCase();
    // Flag if statement appears nearly verbatim in snapshot (>80 char substring match)
    const words = stmt.split(" ").slice(0, 10).join(" ");
    return words.length > 20 && snapshot.toLowerCase().includes(words);
  });
  if (verbatim.length > 0) issues.push(`regurgitation: ${verbatim.length} pattern(s) lifted verbatim`);

  return issues;
}

function assessPass2(data) {
  const issues = [];
  if (!Array.isArray(data.curiosity_flags))   issues.push("curiosity_flags missing");
  if (!data.reflection || typeof data.reflection.content !== "string") issues.push("reflection missing");
  if (data.reflection?.content && data.reflection.content.split(/\s+/).length < 20) issues.push("reflection too short (<20 words)");
  if (data.reflection?.content && data.reflection.content.split(/\s+/).length > 120) issues.push("reflection too long (>120 words)");
  return issues;
}

function assessPass3(data, snapshot) {
  const base = assessPass1(data, snapshot);
  if (!["intact","degraded","collapsed"].includes(data.context_quality)) base.push("context_quality invalid");
  return base;
}

// ---------------------------------------------------------------------------
// Run one model-mode through all three passes
// ---------------------------------------------------------------------------

async function runModelMode(mm, stdSnapshot, bigSnapshot) {
  const result = { pass: 0, fail: 0, issues: [], times: [], thinking: false };

  // Pass 1
  const p1Start = Date.now();
  let p1Raw, p1Data;
  try {
    const resp = await ollamaChat(mm.model,
      [{ role: "system", content: PASS1_SYSTEM }, { role: "user", content: PASS1_USER(stdSnapshot) }],
      { format: "json", maxTokens: 1024, think: mm.think }
    );
    p1Raw = resp.content;
    if (resp.thinking) result.thinking = true;
  } catch (e) {
    result.fail += 3; // all three passes failed
    result.issues.push(`Pass 1 model error: ${e.message.slice(0,60)}`);
    result.times.push(Date.now() - p1Start, 0, 0);
    return result;
  }
  result.times.push(Date.now() - p1Start);

  p1Data = tryParseJSON(p1Raw);
  if (!p1Data) {
    result.fail++;
    result.issues.push("Pass 1: JSON parse failed");
    // Abort — no point running Pass 2 without Pass 1 data
    result.fail += 2;
    result.issues.push("Pass 2: aborted (Pass 1 failed)", "Pass 3: aborted (Pass 1 failed)");
    result.times.push(0, 0);
    return result;
  }
  const p1Issues = assessPass1(p1Data, stdSnapshot);
  if (p1Issues.length === 0) {
    result.pass++;
  } else {
    result.fail++;
    result.issues.push(...p1Issues.map(i => `Pass 1: ${i}`));
  }

  // Pass 2
  const p2Start = Date.now();
  let p2Raw, p2Data;
  try {
    const resp = await ollamaChat(mm.model,
      [{ role: "system", content: PASS2_SYSTEM }, { role: "user", content: PASS2_USER(stdSnapshot, p1Data) }],
      { format: "json", maxTokens: 1500, think: mm.think }
    );
    p2Raw = resp.content;
  } catch (e) {
    result.fail++;
    result.issues.push(`Pass 2 model error: ${e.message.slice(0,60)}`);
    result.times.push(Date.now() - p2Start, 0);
    result.fail++;
    result.issues.push("Pass 3: aborted (Pass 2 failed)");
    result.times.push(0);
    return result;
  }
  result.times.push(Date.now() - p2Start);

  p2Data = tryParseJSON(p2Raw);
  if (!p2Data) {
    result.fail++;
    result.issues.push("Pass 2: JSON parse failed");
  } else {
    const p2Issues = assessPass2(p2Data);
    if (p2Issues.length === 0) result.pass++;
    else { result.fail++; result.issues.push(...p2Issues.map(i => `Pass 2: ${i}`)); }
  }

  // Pass 3 — stress
  const p3Start = Date.now();
  let p3Raw, p3Data;
  try {
    const resp = await ollamaChat(mm.model,
      [{ role: "system", content: PASS1_SYSTEM }, { role: "user", content: PASS3_USER(bigSnapshot) }],
      { format: "json", maxTokens: 1200, think: mm.think }
    );
    p3Raw = resp.content;
  } catch (e) {
    result.fail++;
    result.issues.push(`Pass 3 model error: ${e.message.slice(0,60)}`);
    result.times.push(Date.now() - p3Start);
    return result;
  }
  result.times.push(Date.now() - p3Start);

  p3Data = tryParseJSON(p3Raw);
  if (!p3Data) {
    result.fail++;
    result.issues.push("Pass 3: JSON parse failed");
  } else {
    const p3Issues = assessPass3(p3Data, bigSnapshot);
    if (p3Issues.length === 0) result.pass++;
    else { result.fail++; result.issues.push(...p3Issues.map(i => `Pass 3: ${i}`)); }
  }

  // Capture Pass 3 context_quality for reporting
  result.p1 = p1Data;
  result.p2 = p2Data;
  result.p3 = p3Data;

  return result;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log("=== Contemplator Cross-Generation Stress Test ===");
  console.log(`Baseline: ${BASELINE_MODEL}`);
  console.log(`Candidates: ${Q3_MODELS.join(", ")} × {think, no-think}`);
  console.log(`Time: ${new Date().toISOString()}\n`);

  // Confirm models
  const tagsRes = await fetch(`${OLLAMA_BASE}/api/tags`);
  const tags = await tagsRes.json();
  const available = new Set((tags.models||[]).map(m => m.name));
  const needed = [BASELINE_MODEL, ...Q3_MODELS];
  const missing = needed.filter(m => !available.has(m));
  if (missing.length > 0) {
    console.error(`Missing: ${missing.join(", ")} — run: ollama pull <model>`);
    process.exit(1);
  }
  console.log(`✓ All models confirmed: ${needed.join(", ")}\n`);

  const { brainUrl, serviceKey } = readConfig();

  console.log("Fetching brain snapshots...");
  const stdData = await fetchBrainData(brainUrl, serviceKey, { memCount: 10, beliefCount: 8,  entityCount: 8  });
  const bigData = await fetchBrainData(brainUrl, serviceKey, { memCount: 20, beliefCount: 15, entityCount: 15 });
  const stdSnapshot = formatSnapshot(stdData);
  const bigSnapshot = formatSnapshot(bigData);
  console.log(`  Standard: ${stdSnapshot.length} chars  |  Stress: ${bigSnapshot.length} chars\n`);

  // Run all model-modes
  const allResults = {};

  for (const mm of MODEL_MODES) {
    console.log(`Running: ${mm.label}...`);
    const result = await runModelMode(mm, stdSnapshot, bigSnapshot);
    allResults[mm.key] = result;

    const p1t = (result.times[0]||0)/1000;
    const p2t = (result.times[1]||0)/1000;
    const p3t = (result.times[2]||0)/1000;
    const cq = result.p3?.context_quality || "—";
    const thinkFlag = result.thinking ? " 🧠" : "";

    console.log(`  Pass 1: ${result.issues.some(i=>i.startsWith("Pass 1")) ? "FAIL" : "PASS"}  (${p1t.toFixed(1)}s)${thinkFlag}`);
    console.log(`  Pass 2: ${result.issues.some(i=>i.startsWith("Pass 2")) ? "FAIL" : "PASS"}  (${p2t.toFixed(1)}s)`);
    console.log(`  Pass 3: ${result.issues.some(i=>i.startsWith("Pass 3")) ? "FAIL" : "PASS"}  (${p3t.toFixed(1)}s)  context_quality=${cq}`);
    if (result.issues.length > 0) {
      result.issues.forEach(i => console.log(`    ⚠ ${i}`));
    }
    // Show sample pattern from Pass 1 if available
    const samplePattern = result.p1?.pattern_candidates?.[0];
    if (samplePattern) {
      const stmt = typeof samplePattern === "string" ? samplePattern : samplePattern.statement || "";
      console.log(`  Sample pattern: "${stmt.slice(0, 100)}"`);
    }
    // Show reflection snippet from Pass 2 if available
    if (result.p2?.reflection?.content) {
      console.log(`  Reflection: "${result.p2.reflection.content.slice(0, 120)}..."`);
    }
    console.log("");
  }

  // Summary table
  console.log("╔══════════════════════════════════════════════════════════════════╗");
  console.log("║  RESULTS SUMMARY                                                  ║");
  console.log("╚══════════════════════════════════════════════════════════════════╝");
  console.log(`  ${"Model / Mode".padEnd(26)} ${"P1".padEnd(6)} ${"P2".padEnd(6)} ${"P3".padEnd(6)} ${"Passes".padEnd(8)} Avg(s)  ContextQ`);
  console.log(`  ${"-".repeat(78)}`);

  for (const mm of MODEL_MODES) {
    const r = allResults[mm.key];
    const p1ok = !r.issues.some(i => i.startsWith("Pass 1")) ? "PASS" : "FAIL";
    const p2ok = !r.issues.some(i => i.startsWith("Pass 2")) ? "PASS" : "FAIL";
    const p3ok = !r.issues.some(i => i.startsWith("Pass 3")) ? "PASS" : "FAIL";
    const total = 3;
    const avg = r.times.filter(t => t > 0).length > 0
      ? (r.times.filter(t=>t>0).reduce((a,b)=>a+b,0) / r.times.filter(t=>t>0).length / 1000).toFixed(1)
      : "—";
    const cq = r.p3?.context_quality || "—";
    console.log(`  ${mm.key.padEnd(26)} ${p1ok.padEnd(6)} ${p2ok.padEnd(6)} ${p3ok.padEnd(6)} ${pct(r.pass, total).padEnd(8)} ${avg}    ${cq}`);
  }

  // Cross-gen comparison
  console.log("\n╔══════════════════════════════════════════════════════════════════╗");
  console.log("║  CROSS-GENERATION COMPARISON                                      ║");
  console.log("╚══════════════════════════════════════════════════════════════════╝");
  console.log(`\n  ${"Tier".padEnd(16)} ${"Q2.5 baseline".padEnd(20)} ${"Q3 no-think".padEnd(18)} ${"Q3 think".padEnd(18)} Winner`);
  console.log(`  ${"-".repeat(86)}`);

  for (const tier of SIZE_TIERS) {
    const baseR = tier.baseline ? allResults[tier.baseline] : null;
    const q3nr  = allResults[`${tier.q3}|nothink`];
    const q3tr  = allResults[`${tier.q3}|think`];

    const baseStr = baseR ? `${pct(baseR.pass,3)} (${baseR.p3?.context_quality||"—"})` : "N/A";
    const q3nStr  = q3nr  ? `${pct(q3nr.pass,3)} (${q3nr.p3?.context_quality||"—"})`  : "—";
    const q3tStr  = q3tr  ? `${pct(q3tr.pass,3)} (${q3tr.p3?.context_quality||"—"})`  : "—";

    const scores = [
      ...(baseR ? [{ label: "Q2.5 baseline", val: baseR.pass }] : []),
      ...(q3nr  ? [{ label: "Q3 no-think",   val: q3nr.pass  }] : []),
      ...(q3tr  ? [{ label: "Q3 think",       val: q3tr.pass  }] : []),
    ];
    const best = scores.reduce((a,b) => b.val > a.val ? b : a, { val: -1 });
    const tied = scores.filter(s => s.val === best.val);
    const winner = tied.length > 1 ? `tie (${tied.map(t=>t.label).join(" / ")})` : best.label;

    console.log(`  ${tier.label.padEnd(16)} ${baseStr.padEnd(20)} ${q3nStr.padEnd(18)} ${q3tStr.padEnd(18)} ${winner}`);
  }

  // Recommendation
  console.log("\n  ── Recommendation ──");
  const all = MODEL_MODES.map(mm => ({ mm, r: allResults[mm.key] }));
  const viable = all.filter(({ r }) => r.pass >= 2); // at least 2/3 passes
  const best = viable.reduce((a, b) => b.r.pass > a.r.pass ? b : a, viable[0]);
  const bestCQ = best?.r.p3?.context_quality;

  if (best) {
    console.log(`  Best: ${best.mm.label} — ${pct(best.r.pass, 3)} pass rate, context_quality=${bestCQ}`);
    if (best.mm.key === BASELINE_MODEL) {
      console.log("  Verdict: Current baseline (qwen2.5:14b) remains the best choice.");
    } else {
      console.log(`  Verdict: Upgrade Contemplator to ${best.mm.label}.`);
      console.log(`  Current baseline: ${pct(allResults[BASELINE_MODEL]?.pass||0, 3)}`);
    }
  }

  console.log("\nDone.");
}

main().catch(e => { console.error("FATAL:", e.message); process.exit(1); });
