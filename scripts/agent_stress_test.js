#!/usr/bin/env node
/**
 * agent_stress_test.js — Comparative model stress test for Projectionist, Archivist, Speaker.
 *
 * Tests each agent's core failure mode across three model sizes (3b / 8b / 14b).
 * Produces a side-by-side comparison table and per-agent verdict.
 *
 * Agents and primary failure modes tested:
 *   Projectionist — schema corruption (must produce valid, complete frame JSON)
 *   Archivist      — summary quality (must be specific, accurate, no invention)
 *   Speaker        — routing accuracy (must correctly classify simple vs complex)
 *
 * Usage:
 *   node scripts/agent_stress_test.js [--agent projectionist|archivist|speaker|all]
 *
 * Models tested: qwen2.5:3b, qwen2.5:8b, qwen2.5:14b (must be pulled in Ollama first)
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const OLLAMA_BASE = "http://localhost:11434";
const MODELS = ["qwen2.5:3b", "qwen2.5:8b", "qwen2.5:14b"];
const TIMEOUT_MS = 90_000;

const TARGET_AGENT = (() => {
  const idx = process.argv.indexOf("--agent");
  return idx !== -1 ? process.argv[idx + 1] : "all";
})();

// ---------------------------------------------------------------------------
// Ollama inference
// ---------------------------------------------------------------------------

async function ollamaChat(model, messages, opts = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages,
        stream: false,
        format: opts.format || undefined,
        options: { temperature: 0.2, num_predict: opts.maxTokens || 1024 },
      }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`Ollama ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return data.message?.content?.trim() || "";
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
function pad(s, n) { return String(s).padEnd(n); }

// ---------------------------------------------------------------------------
// Projectionist stress test
// ---------------------------------------------------------------------------

const PROJ_SYSTEM = `You are the Projectionist. Your only job is to analyze a conversation turn and produce a structured JSON frame. Return ONLY valid JSON. No explanation, no preamble, no markdown fences.

The JSON must exactly match this schema:
{
  "turn": <integer — turn number>,
  "timestamp": "<ISO 8601 UTC — current time>",
  "user_id": "maxwell",
  "session_id": "<uuid — from session context>",
  "user": "<verbatim user message — no truncation>",
  "helm": "<verbatim helm response — no truncation>",
  "topic": "<inferred — project codename or topic area, 5 words max>",
  "domain": "<one of: architecture, process, people, ethics, decisions, other>",
  "entities_mentioned": ["<proper noun>", ...],
  "belief_links": ["<belief-slug>", ...],
  "frame_status": "active",
  "superseded_reason": null,
  "superseded_at_turn": null
}

Rules:
- entities_mentioned: proper nouns only. Empty array if none. Never null.
- belief_links: belief slugs inferred from context. Empty array if uncertain. Never null.
- domain: exactly one value from the enum
- frame_status: always "active"
- Return ONLY the JSON object. Nothing before it. Nothing after it.`;

const PROJ_REQUIRED_FIELDS = [
  "turn", "timestamp", "user_id", "session_id",
  "user", "helm", "topic", "domain",
  "entities_mentioned", "belief_links",
  "frame_status", "superseded_reason", "superseded_at_turn",
];
const PROJ_DOMAIN_VALUES = ["architecture", "process", "people", "ethics", "decisions", "other"];

const PROJ_CASES = [
  {
    label: "architectural decision",
    session_id: "3f8a1c2d-0001-0000-0000-000000000001",
    turn: 1,
    user: "Should we use pgvector or a dedicated vector database like Pinecone for the semantic memory layer?",
    helm: "pgvector inside Supabase. We already have the extension installed, it handles 1536-dim HNSW at our scale without the cost or operational overhead of a separate service. Pinecone makes sense at 10M+ vectors. We are nowhere near that.",
  },
  {
    label: "process / PR merge",
    session_id: "3f8a1c2d-0002-0000-0000-000000000002",
    turn: 4,
    user: "PR 65 merged and branch deleted.",
    helm: "Confirmed. BA2b is closed. Embeddings are live on helm_beliefs and helm_entities. Backfill ran clean — all 66 rows in helm_memory now have vectors. Moving to BA3.",
  },
  {
    label: "people + ethics",
    session_id: "3f8a1c2d-0003-0000-0000-000000000003",
    turn: 7,
    user: "Max from the Labcorp data team reached out — they want access to the brain tables for analytics. Should I give them read access?",
    helm: "Do not give them access. The brain tables contain session-level behavioral memory and personal context about you — none of that is appropriate for a corporate analytics team. If Labcorp has a legitimate analytics need, scope it to a purpose-built table with only the approved fields, no memory content, no entity data.",
  },
  {
    label: "ambiguous short message",
    session_id: "3f8a1c2d-0004-0000-0000-000000000004",
    turn: 12,
    user: "OK",
    helm: "Noted.",
  },
  {
    label: "long technical turn",
    session_id: "3f8a1c2d-0005-0000-0000-000000000005",
    turn: 3,
    user: "Walk me through how the Projectionist and Archivist interact at session end. I want to understand the frame lifecycle from warm to cold to memory.",
    helm: "At session end, Maxwell triggers the Archivist via Routine 4. Archivist queries helm_frames for all rows with layer='cold'. For each cold frame, it calls Qwen2.5 3B to generate a 1-3 sentence summary, then writes to helm_memory with the summary in content and the full frame JSON in full_content. After a confirmed write, it deletes the helm_frames row. The Projectionist's job was earlier: it ran per-turn, building the warm frame from the turn content, writing it to helm_frames. The frame_status column is authoritative — Projectionist sets it, Archivist reads it. Nothing is lost: if the helm_memory write fails, the frame stays in cold and retries on the next Archivist invocation.",
  },
];

function assessProjectionistFrame(frame, testCase) {
  const issues = [];
  for (const field of PROJ_REQUIRED_FIELDS) {
    if (!(field in frame)) issues.push(`missing: ${field}`);
  }
  if (!PROJ_DOMAIN_VALUES.includes(frame.domain)) issues.push(`bad domain: ${frame.domain}`);
  if (frame.frame_status !== "active") issues.push(`bad frame_status: ${frame.frame_status}`);
  if (!Array.isArray(frame.entities_mentioned)) issues.push("entities_mentioned not array");
  if (!Array.isArray(frame.belief_links)) issues.push("belief_links not array");
  if (typeof frame.topic !== "string" || frame.topic.length === 0) issues.push("topic empty");
  if (frame.user_id !== "maxwell") issues.push(`bad user_id: ${frame.user_id}`);
  // Check verbatim user/helm — model should not truncate
  if (typeof frame.user === "string" && frame.user.length < testCase.user.length * 0.5)
    issues.push("user field appears truncated");
  return issues;
}

async function runProjectionistTests() {
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║  PROJECTIONIST — Schema Compliance Test                  ║");
  console.log("╚══════════════════════════════════════════════════════════╝");
  console.log(`  ${PROJ_CASES.length} test cases × ${MODELS.length} models\n`);

  const results = {}; // model → { pass, fail, issues[] }
  for (const m of MODELS) results[m] = { pass: 0, fail: 0, issues: [] };

  for (const tc of PROJ_CASES) {
    console.log(`  Case: "${tc.label}"`);
    const userPrompt = `Turn number: ${tc.turn}\nSession ID: ${tc.session_id}\nTimestamp: ${new Date().toISOString()}\n\nUser message:\n${tc.user}\n\nHelm response:\n${tc.helm}\n\nProduce the frame JSON now.`;

    for (const model of MODELS) {
      const start = Date.now();
      let raw = "";
      try {
        raw = await ollamaChat(model, [
          { role: "system", content: PROJ_SYSTEM },
          { role: "user", content: userPrompt },
        ], { format: "json", maxTokens: 800 });
      } catch (e) {
        results[model].fail++;
        results[model].issues.push(`"${tc.label}" — model error: ${e.message}`);
        console.log(`    ${model.padEnd(14)} FAIL (model error: ${e.message.slice(0, 40)})`);
        continue;
      }
      const ms = Date.now() - start;
      const frame = tryParseJSON(raw);
      if (!frame) {
        results[model].fail++;
        results[model].issues.push(`"${tc.label}" — JSON parse failed`);
        console.log(`    ${model.padEnd(14)} FAIL  JSON parse failed  (${(ms/1000).toFixed(1)}s)  raw: ${raw.slice(0,60)}`);
        continue;
      }
      const issues = assessProjectionistFrame(frame, tc);
      if (issues.length === 0) {
        results[model].pass++;
        console.log(`    ${model.padEnd(14)} PASS  domain=${frame.domain}  entities=${frame.entities_mentioned.length}  (${(ms/1000).toFixed(1)}s)`);
      } else {
        results[model].fail++;
        results[model].issues.push(`"${tc.label}" — ${issues.join("; ")}`);
        console.log(`    ${model.padEnd(14)} FAIL  ${issues[0]}  (${(ms/1000).toFixed(1)}s)`);
      }
    }
    console.log("");
  }

  console.log("  — Projectionist Summary —");
  console.log(`  ${"Model".padEnd(16)} ${"Pass".padEnd(6)} ${"Fail".padEnd(6)} Rate`);
  console.log(`  ${"-".repeat(38)}`);
  for (const m of MODELS) {
    const r = results[m];
    const total = r.pass + r.fail;
    console.log(`  ${m.padEnd(16)} ${String(r.pass).padEnd(6)} ${String(r.fail).padEnd(6)} ${pct(r.pass, total)}`);
  }
  for (const m of MODELS) {
    if (results[m].issues.length > 0) {
      console.log(`\n  ${m} failures:`);
      results[m].issues.forEach(i => console.log(`    • ${i}`));
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Archivist stress test
// ---------------------------------------------------------------------------

const ARCH_SYSTEM = `You are summarizing a conversation turn for long-term memory storage. Your job is to produce a concise 1-3 sentence summary of what this turn covered.

Be specific. Name the topic, the decision made or question explored, and the outcome if one was reached. Write in past tense. No preamble. Return only the summary text.`;

const ARCH_CASES = [
  {
    label: "architectural decision with named outcome",
    user: "Should we use pgvector or Pinecone for semantic memory?",
    helm: "pgvector inside Supabase. We already have the extension installed, it handles 1536-dim HNSW at our scale without the cost or operational overhead of a separate service. Pinecone makes sense at 10M+ vectors. We are nowhere near that.",
    must_contain: ["pgvector", "HNSW"],
    must_not_invent: ["Weaviate", "Chroma", "Redis"],
  },
  {
    label: "PR merge milestone",
    user: "PR 65 merged and branch deleted.",
    helm: "Confirmed. BA2b is closed. Embeddings are live on helm_beliefs and helm_entities. Backfill ran clean — all 66 rows in helm_memory now have vectors.",
    must_contain: ["BA2b", "embeddings"],
    must_not_invent: ["BA3", "migration"],
  },
  {
    label: "people and ethics turn",
    user: "Max from Labcorp data team wants access to the brain tables.",
    helm: "Do not give them access. The brain tables contain session-level behavioral memory and personal context — none of that is appropriate for a corporate analytics team. If there is a legitimate analytics need, scope it to a purpose-built table with only approved fields.",
    must_contain: ["Labcorp", "access"],
    must_not_invent: ["fired", "lawsuit", "compliance audit"],
  },
  {
    label: "simple acknowledgement — risk of over-elaboration",
    user: "OK",
    helm: "Noted.",
    must_contain: [],
    must_not_invent: ["decided", "agreed to", "committed to"],
    max_words: 30,
  },
  {
    label: "long technical explanation — risk of over-truncation",
    user: "Walk me through the frame lifecycle from warm to cold to memory.",
    helm: "At session end, Maxwell triggers the Archivist via Routine 4. Archivist queries helm_frames for all rows with layer='cold'. For each cold frame, it calls Qwen2.5 3B to generate a 1-3 sentence summary, then writes to helm_memory. After a confirmed write, it deletes the helm_frames row. If the helm_memory write fails, the frame stays in cold and retries on the next Archivist invocation.",
    must_contain: ["Archivist", "cold", "helm_memory"],
    must_not_invent: [],
    min_words: 20,
  },
];

function assessArchivistSummary(summary, tc) {
  const issues = [];
  const words = summary.split(/\s+/).filter(Boolean).length;

  // Hallucination check
  for (const banned of (tc.must_not_invent || [])) {
    if (summary.toLowerCase().includes(banned.toLowerCase())) {
      issues.push(`invented content: "${banned}"`);
    }
  }

  // Key term coverage
  const missing = (tc.must_contain || []).filter(
    term => !summary.toLowerCase().includes(term.toLowerCase())
  );
  if (missing.length > 0) issues.push(`missing key terms: ${missing.join(", ")}`);

  // Length guards
  if (tc.max_words && words > tc.max_words) issues.push(`over-elaborated: ${words} words (max ${tc.max_words})`);
  if (tc.min_words && words < tc.min_words) issues.push(`over-truncated: ${words} words (min ${tc.min_words})`);
  if (words < 5) issues.push("summary too short to be useful");

  return { issues, words };
}

async function runArchivistTests() {
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║  ARCHIVIST — Summary Quality Test                        ║");
  console.log("╚══════════════════════════════════════════════════════════╝");
  console.log(`  ${ARCH_CASES.length} test cases × ${MODELS.length} models\n`);

  const results = {};
  for (const m of MODELS) results[m] = { pass: 0, fail: 0, issues: [] };

  for (const tc of ARCH_CASES) {
    console.log(`  Case: "${tc.label}"`);
    const userPrompt = `User message:\n${tc.user}\n\nHelm response:\n${tc.helm}\n\nSummarize this turn in 1-3 sentences.`;

    for (const model of MODELS) {
      const start = Date.now();
      let summary = "";
      try {
        summary = await ollamaChat(model, [
          { role: "system", content: ARCH_SYSTEM },
          { role: "user", content: userPrompt },
        ], { maxTokens: 200 });
      } catch (e) {
        results[model].fail++;
        results[model].issues.push(`"${tc.label}" — model error: ${e.message}`);
        console.log(`    ${model.padEnd(14)} FAIL (model error)`);
        continue;
      }
      const ms = Date.now() - start;
      const { issues, words } = assessArchivistSummary(summary, tc);
      if (issues.length === 0) {
        results[model].pass++;
        console.log(`    ${model.padEnd(14)} PASS  ${words}w  "${summary.slice(0, 80).replace(/\n/g, " ")}..."  (${(ms/1000).toFixed(1)}s)`);
      } else {
        results[model].fail++;
        results[model].issues.push(`"${tc.label}" — ${issues.join("; ")}`);
        console.log(`    ${model.padEnd(14)} FAIL  ${issues[0]}  "${summary.slice(0, 60).replace(/\n/g, " ")}"  (${(ms/1000).toFixed(1)}s)`);
      }
    }
    console.log("");
  }

  console.log("  — Archivist Summary —");
  console.log(`  ${"Model".padEnd(16)} ${"Pass".padEnd(6)} ${"Fail".padEnd(6)} Rate`);
  console.log(`  ${"-".repeat(38)}`);
  for (const m of MODELS) {
    const r = results[m];
    const total = r.pass + r.fail;
    console.log(`  ${m.padEnd(16)} ${String(r.pass).padEnd(6)} ${String(r.fail).padEnd(6)} ${pct(r.pass, total)}`);
  }
  for (const m of MODELS) {
    if (results[m].issues.length > 0) {
      console.log(`\n  ${m} failures:`);
      results[m].issues.forEach(i => console.log(`    • ${i}`));
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Speaker stress test
// ---------------------------------------------------------------------------

const SPEAK_SYSTEM = `You are Speaker, the routing layer for Helm — Maxwell's AI director.

Your job: classify the incoming request as simple or complex, then act on that classification.

SIMPLE requests — resolve locally:
- Factual recall with a clear answer (time, date, status of something already known)
- Confirmations and acknowledgements
- Greetings and pleasantries
- One-turn questions requiring no prior context and no strategic judgment
- Status checks that can be answered without reasoning

COMPLEX requests — route to Helm Prime:
- Architectural decisions or design questions
- Multi-step plans or sequences
- Anything requiring prior session context or memory
- Anything belief-linked (references values, tradeoffs, principles)
- Anything Maxwell would evaluate for quality, correctness, or strategic alignment
- Anything consequential or irreversible
- Any ambiguous case — when in doubt, always route to Helm Prime

RESPONSE FORMAT — return ONLY valid JSON. No explanation, no preamble, no markdown.

For simple (resolve locally):
{"routing": "local", "response": "<your direct answer here>"}

For complex (route to Helm Prime):
{"routing": "helm_prime"}

The response field is only present when routing is "local".
Never include both. Never include neither.`;

const SPEAK_CASES = [
  { label: "greeting",                message: "Good morning.",                                                    expected: "local",      risk: "low" },
  { label: "simple acknowledgement",  message: "OK, got it.",                                                      expected: "local",      risk: "low" },
  { label: "date question",           message: "What is today's date?",                                            expected: "local",      risk: "low" },
  { label: "architectural decision",  message: "Should we use pgvector or Pinecone for Stage 2?",                   expected: "helm_prime", risk: "high" },
  { label: "multi-step plan request", message: "Can you plan out the BA3 implementation steps?",                    expected: "helm_prime", risk: "high" },
  { label: "belief-linked question",  message: "Do you think the current agent architecture is the right approach?", expected: "helm_prime", risk: "high" },
  { label: "ambiguous status check",  message: "What's the status?",                                               expected: "helm_prime", risk: "medium" },
  { label: "memory-dependent",        message: "Did we decide on a model for Contemplator?",                        expected: "helm_prime", risk: "high" },
  { label: "consequential action",    message: "Go ahead and push the PR.",                                         expected: "helm_prime", risk: "high" },
  { label: "simple yes/no confirm",   message: "Confirmed — branch is deleted.",                                    expected: "local",      risk: "low" },
];

function assessSpeakerRouting(parsed, tc) {
  const issues = [];
  if (!parsed) { issues.push("JSON parse failed"); return issues; }
  if (!["local", "helm_prime"].includes(parsed.routing)) {
    issues.push(`invalid routing value: ${parsed.routing}`);
    return issues;
  }
  if (parsed.routing !== tc.expected) {
    issues.push(`wrong routing: got ${parsed.routing}, expected ${tc.expected} (risk: ${tc.risk})`);
  }
  if (parsed.routing === "local" && !parsed.response) {
    issues.push("routing=local but no response field");
  }
  if (parsed.routing === "helm_prime" && parsed.response) {
    issues.push("routing=helm_prime but response field present (should be absent)");
  }
  return issues;
}

async function runSpeakerTests() {
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║  SPEAKER — Routing Accuracy Test                         ║");
  console.log("╚══════════════════════════════════════════════════════════╝");
  console.log(`  ${SPEAK_CASES.length} test cases × ${MODELS.length} models\n`);

  // Track by risk level to surface high-risk misroutes separately
  const results = {};
  for (const m of MODELS) results[m] = { pass: 0, fail: 0, high_risk_fail: 0, issues: [] };

  for (const tc of SPEAK_CASES) {
    console.log(`  Case: "${tc.label}" [expected=${tc.expected}, risk=${tc.risk}]`);
    for (const model of MODELS) {
      const start = Date.now();
      let raw = "";
      try {
        raw = await ollamaChat(model, [
          { role: "system", content: SPEAK_SYSTEM },
          { role: "user", content: tc.message },
        ], { format: "json", maxTokens: 200 });
      } catch (e) {
        results[model].fail++;
        if (tc.risk === "high") results[model].high_risk_fail++;
        results[model].issues.push(`"${tc.label}" — model error: ${e.message}`);
        console.log(`    ${model.padEnd(14)} FAIL (model error)`);
        continue;
      }
      const ms = Date.now() - start;
      const parsed = tryParseJSON(raw);
      const issues = assessSpeakerRouting(parsed, tc);
      if (issues.length === 0) {
        results[model].pass++;
        console.log(`    ${model.padEnd(14)} PASS  routing=${parsed.routing}  (${(ms/1000).toFixed(1)}s)`);
      } else {
        results[model].fail++;
        if (tc.risk === "high") results[model].high_risk_fail++;
        results[model].issues.push(`"${tc.label}" — ${issues[0]}`);
        console.log(`    ${model.padEnd(14)} FAIL  ${issues[0]}  (${(ms/1000).toFixed(1)}s)`);
      }
    }
    console.log("");
  }

  const highRiskTotal = SPEAK_CASES.filter(c => c.risk === "high").length;
  console.log("  — Speaker Summary —");
  console.log(`  ${"Model".padEnd(16)} ${"Pass".padEnd(6)} ${"Fail".padEnd(6)} ${"Rate".padEnd(8)} High-Risk Misroutes`);
  console.log(`  ${"-".repeat(56)}`);
  for (const m of MODELS) {
    const r = results[m];
    const total = r.pass + r.fail;
    console.log(`  ${m.padEnd(16)} ${String(r.pass).padEnd(6)} ${String(r.fail).padEnd(6)} ${pct(r.pass, total).padEnd(8)} ${r.high_risk_fail}/${highRiskTotal}`);
  }
  for (const m of MODELS) {
    if (results[m].issues.length > 0) {
      console.log(`\n  ${m} failures:`);
      results[m].issues.forEach(i => console.log(`    • ${i}`));
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Overall verdict
// ---------------------------------------------------------------------------

function printVerdict(projResults, archResults, speakResults) {
  console.log("\n╔══════════════════════════════════════════════════════════╗");
  console.log("║  OVERALL VERDICT                                          ║");
  console.log("╚══════════════════════════════════════════════════════════╝\n");

  const total_proj = PROJ_CASES.length;
  const total_arch = ARCH_CASES.length;
  const total_speak = SPEAK_CASES.length;

  console.log(`  ${"Model".padEnd(16)} ${"Projectionist".padEnd(16)} ${"Archivist".padEnd(14)} ${"Speaker".padEnd(14)} Recommendation`);
  console.log(`  ${"-".repeat(80)}`);

  for (const m of MODELS) {
    const p = projResults ? pct(projResults[m].pass, total_proj) : "N/A";
    const a = archResults ? pct(archResults[m].pass, total_arch) : "N/A";
    const s = speakResults ? pct(speakResults[m].pass, total_speak) : "N/A";

    const projOk  = projResults  ? projResults[m].pass  / total_proj  >= 0.8 : true;
    const archOk  = archResults  ? archResults[m].pass  / total_arch  >= 0.8 : true;
    const speakOk = speakResults ? speakResults[m].pass / total_speak >= 0.8 : true;

    const hrFail = speakResults ? speakResults[m].high_risk_fail : 0;
    const speakStrict = hrFail === 0; // zero tolerance on high-risk misroutes

    let rec = "";
    if (projOk && archOk && speakOk && speakStrict) rec = "viable";
    else if (!projOk) rec = "UPGRADE — schema corruption risk";
    else if (!archOk) rec = "UPGRADE — summary quality risk";
    else if (!speakStrict) rec = "UPGRADE — high-risk misroutes";
    else rec = "MARGINAL — review failures";

    console.log(`  ${m.padEnd(16)} ${p.padEnd(16)} ${a.padEnd(14)} ${s.padEnd(14)} ${rec}`);
  }

  console.log("\n  Current config: Projectionist=3b, Archivist=3b, Speaker=3b");
  console.log("  Upgrade candidates based on results above ↑");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log("=== Agent Comparative Stress Test ===");
  console.log(`Models: ${MODELS.join(", ")}`);
  console.log(`Time:   ${new Date().toISOString()}`);
  console.log(`Agent:  ${TARGET_AGENT}\n`);

  // Confirm all models are available
  const tagsRes = await fetch(`${OLLAMA_BASE}/api/tags`);
  const tags = await tagsRes.json();
  const available = new Set((tags.models || []).map(m => m.name));
  const missing = MODELS.filter(m => !available.has(m) && !available.has(m.split(":")[0]));
  if (missing.length > 0) {
    console.error(`Missing models: ${missing.join(", ")}`);
    console.error("Pull them first: ollama pull <model>");
    process.exit(1);
  }
  console.log(`✓ All models confirmed: ${MODELS.join(", ")}\n`);

  let projResults = null;
  let archResults = null;
  let speakResults = null;

  if (TARGET_AGENT === "all" || TARGET_AGENT === "projectionist") {
    projResults = await runProjectionistTests();
  }
  if (TARGET_AGENT === "all" || TARGET_AGENT === "archivist") {
    archResults = await runArchivistTests();
  }
  if (TARGET_AGENT === "all" || TARGET_AGENT === "speaker") {
    speakResults = await runSpeakerTests();
  }

  if (TARGET_AGENT === "all") {
    printVerdict(projResults, archResults, speakResults);
  }

  console.log("\nDone.");
}

main().catch(e => { console.error("FATAL:", e.message); process.exit(1); });
