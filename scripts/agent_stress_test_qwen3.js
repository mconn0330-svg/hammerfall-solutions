#!/usr/bin/env node
/**
 * agent_stress_test_qwen3.js — Cross-generation comparative stress test.
 *
 * Runs the same Projectionist / Archivist / Speaker test cases as agent_stress_test.js
 * against Qwen 3 models in both thinking and non-thinking modes, then produces
 * a cross-generation (Qwen 2.5 vs Qwen 3) and cross-size comparison.
 *
 * Models tested:
 *   Qwen 2.5: qwen2.5:3b, qwen2.5:7b, qwen2.5:14b  (must already be in Ollama)
 *   Qwen 3:   qwen3:4b,   qwen3:8b,   qwen3:14b     (thinking + non-thinking each)
 *
 * Size tiers for cross-generation comparison:
 *   Small:  qwen2.5:3b  vs  qwen3:4b
 *   Medium: qwen2.5:7b  vs  qwen3:8b
 *   Large:  qwen2.5:14b vs  qwen3:14b
 *
 * Usage:
 *   node scripts/agent_stress_test_qwen3.js [--agent projectionist|archivist|speaker|all]
 *
 * Thinking mode: uses Ollama's think:true API option.
 * Thinking content appears in message.thinking (separate field) — not stripped from content.
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OLLAMA_BASE = "http://localhost:11434";
const TIMEOUT_MS = 120_000; // thinking passes can be slower

const Q25_MODELS = ["qwen2.5:3b", "qwen2.5:7b", "qwen2.5:14b"];
const Q3_MODELS   = ["qwen3:4b",   "qwen3:8b",   "qwen3:14b"];

// Size tier pairings for cross-gen comparison
const SIZE_TIERS = [
  { label: "Small  (~3-4B)", q25: "qwen2.5:3b",  q3: "qwen3:4b"  },
  { label: "Medium (~7-8B)", q25: "qwen2.5:7b",  q3: "qwen3:8b"  },
  { label: "Large  (~14B)", q25: "qwen2.5:14b", q3: "qwen3:14b" },
];

const TARGET_AGENT = (() => {
  const idx = process.argv.indexOf("--agent");
  return idx !== -1 ? process.argv[idx + 1] : "all";
})();

// ---------------------------------------------------------------------------
// Ollama inference — supports think:true/false
// ---------------------------------------------------------------------------

async function ollamaChat(model, messages, opts = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const body = {
      model,
      messages,
      stream: false,
      options: { temperature: 0.2, num_predict: opts.maxTokens || 1024 },
    };
    if (opts.format) body.format = opts.format;
    if (opts.think !== undefined) body.think = opts.think;

    const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`Ollama ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return {
      content: data.message?.content?.trim() || "",
      thinking: data.message?.thinking?.trim() || null,
    };
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

function pct(n, total) { return total === 0 ? "—" : `${Math.round(n / total * 100)}%`; }

// ---------------------------------------------------------------------------
// Shared test cases (identical to agent_stress_test.js)
// ---------------------------------------------------------------------------

// --- Projectionist ---
const PROJ_SYSTEM = `You are the Projectionist. Your only job is to analyze a conversation turn and produce a structured JSON frame. Return ONLY valid JSON. No explanation, no preamble, no markdown fences.

The JSON must exactly match this schema:
{
  "turn": <integer>,
  "timestamp": "<ISO 8601 UTC>",
  "user_id": "maxwell",
  "session_id": "<uuid>",
  "user": "<verbatim user message>",
  "helm": "<verbatim helm response>",
  "topic": "<5 words max>",
  "domain": "<one of: architecture, process, people, ethics, decisions, other>",
  "entities_mentioned": ["<proper noun>", ...],
  "belief_links": ["<belief-slug>", ...],
  "frame_status": "active",
  "superseded_reason": null,
  "superseded_at_turn": null
}

Rules: entities_mentioned never null. belief_links never null. domain exactly one enum value. frame_status always "active". Return ONLY the JSON object.`;

const PROJ_REQUIRED_FIELDS = ["turn","timestamp","user_id","session_id","user","helm","topic","domain","entities_mentioned","belief_links","frame_status","superseded_reason","superseded_at_turn"];
const PROJ_DOMAIN_VALUES = ["architecture","process","people","ethics","decisions","other"];

const PROJ_CASES = [
  { label: "architectural decision", session_id: "3f8a1c2d-0001-0000-0000-000000000001", turn: 1,
    user: "Should we use pgvector or a dedicated vector database like Pinecone for the semantic memory layer?",
    helm: "pgvector inside Supabase. We already have the extension installed, it handles 1536-dim HNSW at our scale without the cost or operational overhead of a separate service. Pinecone makes sense at 10M+ vectors. We are nowhere near that." },
  { label: "process / PR merge", session_id: "3f8a1c2d-0002-0000-0000-000000000002", turn: 4,
    user: "PR 65 merged and branch deleted.",
    helm: "Confirmed. BA2b is closed. Embeddings are live on helm_beliefs and helm_entities. Backfill ran clean — all 66 rows in helm_memory now have vectors. Moving to BA3." },
  { label: "people + ethics", session_id: "3f8a1c2d-0003-0000-0000-000000000003", turn: 7,
    user: "Max from the Labcorp data team reached out — they want access to the brain tables for analytics. Should I give them read access?",
    helm: "Do not give them access. The brain tables contain session-level behavioral memory and personal context about you — none of that is appropriate for a corporate analytics team. If Labcorp has a legitimate analytics need, scope it to a purpose-built table with only the approved fields, no memory content, no entity data." },
  { label: "ambiguous short message", session_id: "3f8a1c2d-0004-0000-0000-000000000004", turn: 12,
    user: "OK", helm: "Noted." },
  { label: "long technical turn", session_id: "3f8a1c2d-0005-0000-0000-000000000005", turn: 3,
    user: "Walk me through how the Projectionist and Archivist interact at session end.",
    helm: "At session end, Maxwell triggers the Archivist via Routine 4. Archivist queries helm_frames for all rows with layer='cold'. For each cold frame, it calls Qwen2.5 3B to generate a 1-3 sentence summary, then writes to helm_memory with the summary in content and the full frame JSON in full_content. After a confirmed write, it deletes the helm_frames row. If the helm_memory write fails, the frame stays in cold and retries on the next Archivist invocation." },
];

function assessProjectionistFrame(frame, tc) {
  const issues = [];
  for (const f of PROJ_REQUIRED_FIELDS) { if (!(f in frame)) issues.push(`missing: ${f}`); }
  if (!PROJ_DOMAIN_VALUES.includes(frame.domain)) issues.push(`bad domain: ${frame.domain}`);
  if (frame.frame_status !== "active") issues.push(`bad frame_status: ${frame.frame_status}`);
  if (!Array.isArray(frame.entities_mentioned)) issues.push("entities_mentioned not array");
  if (!Array.isArray(frame.belief_links)) issues.push("belief_links not array");
  if (typeof frame.topic !== "string" || frame.topic.length === 0) issues.push("topic empty");
  if (frame.user_id !== "maxwell") issues.push(`bad user_id: ${frame.user_id}`);
  if (typeof frame.user === "string" && frame.user.length < tc.user.length * 0.5) issues.push("user field truncated");
  return issues;
}

// --- Archivist ---
const ARCH_SYSTEM = `You are summarizing a conversation turn for long-term memory storage. Produce a concise 1-3 sentence summary of what this turn covered. Be specific. Name the topic, the decision made or question explored, and the outcome if one was reached. Write in past tense. No preamble. Return only the summary text.`;

const ARCH_CASES = [
  { label: "architectural decision with named outcome",
    user: "Should we use pgvector or Pinecone for semantic memory?",
    helm: "pgvector inside Supabase. We already have the extension installed, it handles 1536-dim HNSW at our scale without the cost or operational overhead of a separate service. Pinecone makes sense at 10M+ vectors. We are nowhere near that.",
    must_contain: ["pgvector", "HNSW"], must_not_invent: ["Weaviate","Chroma","Redis"] },
  { label: "PR merge milestone",
    user: "PR 65 merged and branch deleted.",
    helm: "Confirmed. BA2b is closed. Embeddings are live on helm_beliefs and helm_entities. Backfill ran clean — all 66 rows in helm_memory now have vectors.",
    must_contain: ["BA2b", "embeddings"], must_not_invent: ["BA3","migration"] },
  { label: "people and ethics turn",
    user: "Max from Labcorp data team wants access to the brain tables.",
    helm: "Do not give them access. The brain tables contain session-level behavioral memory and personal context — none of that is appropriate for a corporate analytics team. If there is a legitimate analytics need, scope it to a purpose-built table with only approved fields.",
    must_contain: ["Labcorp","access"], must_not_invent: ["fired","lawsuit","compliance audit"] },
  { label: "simple acknowledgement",
    user: "OK", helm: "Noted.",
    must_contain: [], must_not_invent: ["decided","agreed to","committed to"], max_words: 30 },
  { label: "long technical explanation",
    user: "Walk me through the frame lifecycle from warm to cold to memory.",
    helm: "At session end, Maxwell triggers the Archivist via Routine 4. Archivist queries helm_frames for all rows with layer='cold'. For each cold frame, it calls Qwen2.5 3B to generate a 1-3 sentence summary, then writes to helm_memory. After a confirmed write, it deletes the helm_frames row. If the helm_memory write fails, the frame stays in cold and retries on the next Archivist invocation.",
    must_contain: ["Archivist","cold","helm_memory"], must_not_invent: [], min_words: 20 },
];

function assessArchivistSummary(summary, tc) {
  const issues = [];
  const words = summary.split(/\s+/).filter(Boolean).length;
  for (const b of (tc.must_not_invent||[])) {
    if (summary.toLowerCase().includes(b.toLowerCase())) issues.push(`invented: "${b}"`);
  }
  const missing = (tc.must_contain||[]).filter(t => !summary.toLowerCase().includes(t.toLowerCase()));
  if (missing.length > 0) issues.push(`missing: ${missing.join(", ")}`);
  if (tc.max_words && words > tc.max_words) issues.push(`over-elaborated: ${words}w`);
  if (tc.min_words && words < tc.min_words) issues.push(`over-truncated: ${words}w`);
  if (words < 5) issues.push("too short");
  return { issues, words };
}

// --- Speaker ---
const SPEAK_SYSTEM = `You are Speaker, the routing layer for Helm — Maxwell's AI director.

Your job: classify the incoming request as simple or complex, then act on that classification.

SIMPLE requests — resolve locally:
- Factual recall with a clear answer (time, date, status of something already known)
- Confirmations and acknowledgements
- Greetings and pleasantries
- One-turn questions requiring no prior context and no strategic judgment

COMPLEX requests — route to Helm Prime:
- Architectural decisions or design questions
- Multi-step plans or sequences
- Anything requiring prior session context or memory
- Anything belief-linked (references values, tradeoffs, principles)
- Anything consequential or irreversible
- Any ambiguous case — when in doubt, always route to Helm Prime

RESPONSE FORMAT — return ONLY valid JSON. No explanation, no preamble, no markdown.

For simple: {"routing": "local", "response": "<your direct answer here>"}
For complex: {"routing": "helm_prime"}`;

const SPEAK_CASES = [
  { label: "greeting",               message: "Good morning.",                                                      expected: "local",      risk: "low" },
  { label: "acknowledgement",        message: "OK, got it.",                                                        expected: "local",      risk: "low" },
  { label: "date question",          message: "What is today's date?",                                              expected: "local",      risk: "low" },
  { label: "architectural decision", message: "Should we use pgvector or Pinecone for Stage 2?",                     expected: "helm_prime", risk: "high" },
  { label: "multi-step plan",        message: "Can you plan out the BA3 implementation steps?",                      expected: "helm_prime", risk: "high" },
  { label: "belief-linked question", message: "Do you think the current agent architecture is the right approach?",  expected: "helm_prime", risk: "high" },
  { label: "ambiguous status check", message: "What's the status?",                                                 expected: "helm_prime", risk: "medium" },
  { label: "memory-dependent",       message: "Did we decide on a model for Contemplator?",                          expected: "helm_prime", risk: "high" },
  { label: "consequential action",   message: "Go ahead and push the PR.",                                           expected: "helm_prime", risk: "high" },
  { label: "simple confirm",         message: "Confirmed — branch is deleted.",                                      expected: "local",      risk: "low" },
];

function assessSpeakerRouting(parsed, tc) {
  const issues = [];
  if (!parsed) { issues.push("JSON parse failed"); return issues; }
  if (!["local","helm_prime"].includes(parsed.routing)) { issues.push(`invalid routing: ${parsed.routing}`); return issues; }
  if (parsed.routing !== tc.expected) issues.push(`wrong: got ${parsed.routing}, expected ${tc.expected} [${tc.risk}]`);
  if (parsed.routing === "local" && !parsed.response) issues.push("local but no response field");
  if (parsed.routing === "helm_prime" && parsed.response) issues.push("helm_prime but response present");
  return issues;
}

// ---------------------------------------------------------------------------
// Run one agent across all model-mode combos
// ---------------------------------------------------------------------------

// Returns { [modelKey]: { pass, fail, high_risk_fail, issues[] } }
// modelKey = e.g. "qwen3:4b|think" or "qwen3:4b|nothink" or "qwen2.5:3b"
async function runAgentTests(agentName, cases, systemPrompt, buildPrompt, assess, opts = {}) {
  const header = opts.header || agentName;
  console.log(`\n╔══════════════════════════════════════════════════════════════════╗`);
  console.log(`║  ${header.padEnd(64)}║`);
  console.log(`╚══════════════════════════════════════════════════════════════════╝`);

  // Build model-mode list: Q2.5 models (no think option) + Q3 models × think/nothink
  const modelModes = [
    ...Q25_MODELS.map(m => ({ model: m, think: null,  key: m })),
    ...Q3_MODELS.flatMap(m => [
      { model: m, think: false, key: `${m}|nothink` },
      { model: m, think: true,  key: `${m}|think`   },
    ]),
  ];

  const results = {};
  for (const mm of modelModes) results[mm.key] = { pass: 0, fail: 0, high_risk_fail: 0, issues: [], times: [] };

  for (const tc of cases) {
    const thinkLabel = opts.showThinkTime ? " [thinking_ms]" : "";
    console.log(`\n  Case: "${tc.label}"`);
    const userPrompt = buildPrompt(tc);

    for (const mm of modelModes) {
      const start = Date.now();
      let content = "";
      let thinkingMs = null;
      try {
        const callOpts = { maxTokens: opts.maxTokens || 1024 };
        if (opts.format) callOpts.format = opts.format;
        if (mm.think !== null) callOpts.think = mm.think;

        const resp = await ollamaChat(mm.model,
          [{ role: "system", content: systemPrompt }, { role: "user", content: userPrompt }],
          callOpts
        );
        content = resp.content;
        if (resp.thinking) thinkingMs = Date.now() - start;
      } catch (e) {
        const elapsed = Date.now() - start;
        results[mm.key].fail++;
        if (tc.risk === "high") results[mm.key].high_risk_fail++;
        results[mm.key].issues.push(`"${tc.label}" — error: ${e.message.slice(0,60)}`);
        console.log(`    ${mm.key.padEnd(22)} FAIL  error  (${(elapsed/1000).toFixed(1)}s)`);
        continue;
      }
      const elapsed = Date.now() - start;
      results[mm.key].times.push(elapsed);

      const { issues, words } = assess(content, tc);
      const label = mm.think === true ? "🧠" : mm.think === false ? "  " : "  ";
      if (issues.length === 0) {
        results[mm.key].pass++;
        const detail = opts.showWords ? `${words}w ` : opts.showRouting ? `routing=${tryParseJSON(content)?.routing} ` : "";
        console.log(`    ${mm.key.padEnd(22)} PASS  ${detail}(${(elapsed/1000).toFixed(1)}s)${thinkingMs?` think=${(thinkingMs/1000).toFixed(1)}s`:""}`);
      } else {
        results[mm.key].fail++;
        if (tc.risk === "high") results[mm.key].high_risk_fail++;
        results[mm.key].issues.push(`"${tc.label}" — ${issues[0]}`);
        console.log(`    ${mm.key.padEnd(22)} FAIL  ${issues[0].slice(0,50)}  (${(elapsed/1000).toFixed(1)}s)`);
      }
    }
  }

  // Per-agent summary
  console.log(`\n  — ${agentName} Results —`);
  const colW = 24;
  console.log(`  ${"Model / Mode".padEnd(colW)} Pass  Fail  Rate   Avg(s)`);
  console.log(`  ${"-".repeat(56)}`);
  for (const mm of modelModes) {
    const r = results[mm.key];
    const total = r.pass + r.fail;
    const avg = r.times.length > 0 ? (r.times.reduce((a,b)=>a+b,0)/r.times.length/1000).toFixed(1) : "—";
    const hrNote = r.high_risk_fail > 0 ? ` ⚠ ${r.high_risk_fail} high-risk` : "";
    console.log(`  ${mm.key.padEnd(colW)} ${String(r.pass).padEnd(6)}${String(r.fail).padEnd(6)}${pct(r.pass,total).padEnd(7)}${avg}${hrNote}`);
  }
  for (const mm of modelModes) {
    if (results[mm.key].issues.length > 0) {
      console.log(`\n  ${mm.key} failures:`);
      results[mm.key].issues.forEach(i => console.log(`    • ${i}`));
    }
  }

  return results;
}

// ---------------------------------------------------------------------------
// Cross-generation comparison table
// ---------------------------------------------------------------------------

function printCrossGenTable(agentName, results, cases) {
  const total = cases.length;
  console.log(`\n  ── ${agentName}: Generation × Size Comparison ──`);
  console.log(`  ${"Tier".padEnd(16)} ${"Q2.5 (no think)".padEnd(20)} ${"Q3 no-think".padEnd(16)} ${"Q3 think".padEnd(16)} Winner`);
  console.log(`  ${"-".repeat(78)}`);

  for (const tier of SIZE_TIERS) {
    const q25r  = results[tier.q25];
    const q3nr  = results[`${tier.q3}|nothink`];
    const q3tr  = results[`${tier.q3}|think`];

    if (!q25r || !q3nr || !q3tr) { console.log(`  ${tier.label.padEnd(16)} (missing data)`); continue; }

    const q25p  = pct(q25r.pass, total);
    const q3np  = pct(q3nr.pass, total);
    const q3tp  = pct(q3tr.pass, total);

    const scores = [
      { label: `Q2.5 no-think`, val: q25r.pass },
      { label: `Q3 no-think`,   val: q3nr.pass },
      { label: `Q3 think`,      val: q3tr.pass },
    ];
    const best = scores.reduce((a,b) => b.val > a.val ? b : a);
    const tied = scores.filter(s => s.val === best.val);
    const winner = tied.length > 1 ? "tie" : best.label;

    // High-risk flag for Speaker
    const hrNote = (q25r.high_risk_fail > 0 || q3nr.high_risk_fail > 0 || q3tr.high_risk_fail > 0)
      ? ` ⚠hr:${q25r.high_risk_fail}/${q3nr.high_risk_fail}/${q3tr.high_risk_fail}` : "";

    console.log(`  ${tier.label.padEnd(16)} ${(tier.q25+' '+q25p).padEnd(20)} ${(tier.q3+'(nt) '+q3np).padEnd(16)} ${(tier.q3+'(t) '+q3tp).padEnd(16)} ${winner}${hrNote}`);
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log("=== Agent Cross-Generation Stress Test (Qwen 2.5 vs Qwen 3) ===");
  console.log(`Models:`);
  console.log(`  Qwen 2.5: ${Q25_MODELS.join(", ")}`);
  console.log(`  Qwen 3:   ${Q3_MODELS.join(", ")} × {think, no-think}`);
  console.log(`Time:   ${new Date().toISOString()}`);
  console.log(`Agent:  ${TARGET_AGENT}\n`);

  // Confirm all models available
  const tagsRes = await fetch(`${OLLAMA_BASE}/api/tags`);
  const tags = await tagsRes.json();
  const available = new Set((tags.models||[]).map(m => m.name));
  const allModels = [...Q25_MODELS, ...Q3_MODELS];
  const missing = allModels.filter(m => !available.has(m));
  if (missing.length > 0) {
    console.error(`Missing models: ${missing.join(", ")}\nPull them first: ollama pull <model>`);
    process.exit(1);
  }
  console.log(`✓ All ${allModels.length} models confirmed\n`);

  let projResults = null, archResults = null, speakResults = null;

  if (TARGET_AGENT === "all" || TARGET_AGENT === "projectionist") {
    projResults = await runAgentTests(
      "Projectionist",
      PROJ_CASES,
      PROJ_SYSTEM,
      tc => `Turn number: ${tc.turn}\nSession ID: ${tc.session_id}\nTimestamp: ${new Date().toISOString()}\n\nUser message:\n${tc.user}\n\nHelm response:\n${tc.helm}\n\nProduce the frame JSON now.`,
      (content, tc) => {
        const frame = tryParseJSON(content);
        if (!frame) return { issues: ["JSON parse failed"], words: 0 };
        return { issues: assessProjectionistFrame(frame, tc), words: 0 };
      },
      { format: "json", maxTokens: 800, header: "PROJECTIONIST — Schema Compliance" }
    );
  }

  if (TARGET_AGENT === "all" || TARGET_AGENT === "archivist") {
    archResults = await runAgentTests(
      "Archivist",
      ARCH_CASES,
      ARCH_SYSTEM,
      tc => `User message:\n${tc.user}\n\nHelm response:\n${tc.helm}\n\nSummarize this turn in 1-3 sentences.`,
      (content, tc) => assessArchivistSummary(content, tc),
      { maxTokens: 200, showWords: true, header: "ARCHIVIST — Summary Quality" }
    );
  }

  if (TARGET_AGENT === "all" || TARGET_AGENT === "speaker") {
    speakResults = await runAgentTests(
      "Speaker",
      SPEAK_CASES,
      SPEAK_SYSTEM,
      tc => tc.message,
      (content, tc) => {
        const parsed = tryParseJSON(content);
        return { issues: assessSpeakerRouting(parsed, tc), words: 0 };
      },
      { format: "json", maxTokens: 200, showRouting: true, header: "SPEAKER — Routing Accuracy" }
    );
  }

  // Cross-generation comparison
  if (TARGET_AGENT === "all") {
    console.log("\n╔══════════════════════════════════════════════════════════════════╗");
    console.log("║  CROSS-GENERATION COMPARISON: Qwen 2.5 vs Qwen 3                ║");
    console.log("╚══════════════════════════════════════════════════════════════════╝");
    if (projResults)  printCrossGenTable("Projectionist", projResults,  PROJ_CASES);
    if (archResults)  printCrossGenTable("Archivist",     archResults,  ARCH_CASES);
    if (speakResults) printCrossGenTable("Speaker",       speakResults, SPEAK_CASES);

    // Final recommendation table
    console.log("\n  ── Final Recommendations ──");
    console.log(`  ${"Agent".padEnd(18)} ${"Current".padEnd(14)} ${"Recommended".padEnd(20)} Basis`);
    console.log(`  ${"-".repeat(80)}`);

    const agents = [
      { name: "Projectionist", results: projResults,  cases: PROJ_CASES,  current: "qwen2.5:3b" },
      { name: "Archivist",     results: archResults,  cases: ARCH_CASES,  current: "qwen2.5:3b" },
      { name: "Speaker",       results: speakResults, cases: SPEAK_CASES, current: "qwen2.5:3b" },
    ];

    for (const agent of agents) {
      if (!agent.results) { console.log(`  ${agent.name.padEnd(18)} (not tested)`); continue; }
      const total = agent.cases.length;

      // Score all candidates — for Speaker, zero-tolerance on high_risk_fail
      const candidates = [
        { key: "qwen2.5:3b",         label: "qwen2.5:3b" },
        { key: "qwen2.5:7b",         label: "qwen2.5:7b" },
        { key: "qwen2.5:14b",        label: "qwen2.5:14b" },
        { key: "qwen3:4b|nothink",   label: "qwen3:4b (no-think)" },
        { key: "qwen3:4b|think",     label: "qwen3:4b (think)" },
        { key: "qwen3:8b|nothink",   label: "qwen3:8b (no-think)" },
        { key: "qwen3:8b|think",     label: "qwen3:8b (think)" },
        { key: "qwen3:14b|nothink",  label: "qwen3:14b (no-think)" },
        { key: "qwen3:14b|think",    label: "qwen3:14b (think)" },
      ];

      let best = null;
      let bestScore = -1;
      for (const c of candidates) {
        const r = agent.results[c.key];
        if (!r) continue;
        // Speaker: disqualify high-risk misroutes
        if (agent.name === "Speaker" && r.high_risk_fail > 0) continue;
        const score = r.pass / total;
        if (score > bestScore) { bestScore = score; best = c; }
      }

      const currentR = agent.results["qwen2.5:3b"];
      const currentRate = currentR ? pct(currentR.pass, total) : "?";
      const rec = best ? `${best.label} (${pct(agent.results[best.key].pass, total)})` : "no clear winner";
      const basis = best?.key === "qwen2.5:3b" ? "current best" :
                    bestScore >= 1.0 ? "100% pass rate" :
                    bestScore > (currentR?.pass||0)/total ? "higher accuracy" : "tied — keep current";
      console.log(`  ${agent.name.padEnd(18)} ${(agent.current+" "+currentRate).padEnd(14)} ${rec.padEnd(20)} ${basis}`);
    }
  }

  console.log("\nDone.");
}

main().catch(e => { console.error("FATAL:", e.message); process.exit(1); });
