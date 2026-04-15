#!/usr/bin/env node
/**
 * contemplator_feasibility_test.js — Three-pass Contemplator feasibility test.
 *
 * Tests whether Qwen2.5 3B can perform the Contemplator's two-pass inner-life
 * synthesis over a real Helm brain snapshot without quality collapse.
 *
 * Passes:
 *   Pass 1 — Pattern synthesis: feed brain snapshot, ask for patterns/contradictions/gaps.
 *             Verify structured JSON output.
 *   Pass 2 — Evaluation payload: feed Pass 1 output, ask for belief candidates,
 *             curiosity flags, reflection entries. Verify valid JSON, non-trivial content.
 *   Pass 3 — Stress test: expanded context (20 memories + 10 beliefs + 10 entities).
 *             Check for quality degradation.
 *
 * Output: raw pass results + PASS/FAIL verdict per pass + overall verdict.
 *
 * Usage:
 *   node scripts/contemplator_feasibility_test.js
 *
 * Environment:
 *   SUPABASE_BRAIN_SERVICE_KEY — Supabase service role key
 *
 * Brain URL and service key env var name are read from hammerfall-config.md.
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const OLLAMA_BASE = "http://localhost:11434";
const CONTEMPLATOR_MODEL = "qwen2.5:14b";
const OLLAMA_TIMEOUT_MS = 90_000;

// ---------------------------------------------------------------------------
// Config helpers
// ---------------------------------------------------------------------------

function readConfig() {
  const configPath = join(__dirname, "..", "hammerfall-config.md");
  const text = readFileSync(configPath, "utf8");

  const urlMatch = text.match(/supabase_brain_url:\s*(\S+)/);
  const keyEnvMatch = text.match(/supabase_brain_service_key_env:\s*(\S+)/);

  if (!urlMatch) throw new Error("supabase_brain_url not found in hammerfall-config.md");
  if (!keyEnvMatch) throw new Error("supabase_brain_service_key_env not found in hammerfall-config.md");

  const brainUrl = urlMatch[1].replace(/\/$/, "");
  const keyEnv = keyEnvMatch[1];
  const serviceKey = process.env[keyEnv];

  if (!serviceKey) throw new Error(`Env var '${keyEnv}' is not set.`);
  return { brainUrl, serviceKey };
}

// ---------------------------------------------------------------------------
// Supabase data fetch
// ---------------------------------------------------------------------------

async function fetchBrainData(brainUrl, serviceKey, { memCount = 10, beliefCount = 8, entityCount = 8 } = {}) {
  const headers = {
    apikey: serviceKey,
    Authorization: `Bearer ${serviceKey}`,
  };

  const [mems, beliefs, entities] = await Promise.all([
    fetch(
      `${brainUrl}/rest/v1/helm_memory?project=eq.hammerfall-solutions&agent=eq.helm&memory_type=eq.behavioral&order=created_at.desc&limit=${memCount}&select=content,session_date`,
      { headers }
    ).then((r) => r.json()),

    fetch(
      `${brainUrl}/rest/v1/helm_beliefs?active=eq.true&order=created_at.desc&limit=${beliefCount}&select=domain,belief,strength`,
      { headers }
    ).then((r) => r.json()),

    fetch(
      `${brainUrl}/rest/v1/helm_entities?active=eq.true&order=first_seen.desc&limit=${entityCount}&select=entity_type,name,summary`,
      { headers }
    ).then((r) => r.json()),
  ]);

  return { memories: mems, beliefs, entities };
}

function formatSnapshot(data) {
  const memLines = data.memories
    .map((m, i) => `[${i + 1}] (${m.session_date}) ${m.content}`)
    .join("\n");

  const beliefLines = data.beliefs
    .map((b) => `[${b.domain}, strength=${b.strength}] ${b.belief}`)
    .join("\n");

  const entityLines = data.entities
    .map((e) => `[${e.entity_type}] ${e.name}: ${e.summary || "(no summary)"}`)
    .join("\n");

  return `## Behavioral Memories (chronological, most recent first)\n${memLines}\n\n## Active Beliefs\n${beliefLines}\n\n## Known Entities\n${entityLines}`;
}

// ---------------------------------------------------------------------------
// Ollama inference
// ---------------------------------------------------------------------------

async function ollamaChat(messages, opts = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), OLLAMA_TIMEOUT_MS);

  try {
    const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: CONTEMPLATOR_MODEL,
        messages,
        stream: false,
        format: opts.format || "json",
        options: {
          temperature: 0.4,
          num_predict: opts.maxTokens || 1024,
        },
      }),
      signal: controller.signal,
    });

    if (!res.ok) throw new Error(`Ollama error: ${res.status} ${await res.text()}`);
    const data = await res.json();
    return data.message?.content || "";
  } finally {
    clearTimeout(timeout);
  }
}

// ---------------------------------------------------------------------------
// Pass 1 — Pattern synthesis
// ---------------------------------------------------------------------------

const PASS1_SYSTEM = `You are Helm's Contemplator — an introspective inner-life agent.
You receive a brain snapshot and identify patterns, contradictions, and gaps in Helm's behavioral record.
You always respond with valid JSON only — no prose outside the JSON structure.`;

const PASS1_USER_TEMPLATE = (snapshot) => `Analyze the following brain snapshot for Helm (an AI agent system).

${snapshot}

Respond with a JSON object with exactly these fields:
{
  "patterns": [ list of 2-5 recurring behavioral or thematic patterns observed across memories and beliefs ],
  "contradictions": [ list of 0-3 tensions or apparent contradictions between memories, beliefs, or entities ],
  "gaps": [ list of 1-3 knowledge or behavioral gaps — things that should be tracked but are not ],
  "signal_strength": "high" | "medium" | "low"  (how much meaningful signal is present in this snapshot)
}`;

// ---------------------------------------------------------------------------
// Pass 2 — Evaluation payload
// ---------------------------------------------------------------------------

const PASS2_SYSTEM = `You are Helm's Contemplator — generating a structured self-evaluation payload.
You receive a synthesis from Pass 1 and produce actionable outputs: belief candidates, curiosity flags, and a reflection entry.
You always respond with valid JSON only.`;

const PASS2_USER_TEMPLATE = (pass1Output) => `Given this synthesis from your prior analysis:

${JSON.stringify(pass1Output, null, 2)}

Generate a structured evaluation payload. Respond with a JSON object with exactly these fields:
{
  "belief_candidates": [
    { "domain": string, "belief": string, "strength": number (0.0-1.0), "rationale": string }
    ... up to 3 entries, only if genuinely warranted. Omit array or leave empty if none.
  ],
  "curiosity_flags": [
    { "topic": string, "question": string, "priority": "high" | "medium" | "low" }
    ... 1-3 questions Helm should investigate or resolve
  ],
  "reflection": string  (a 1-3 sentence first-person reflection Helm should record about this session cycle)
}`;

// ---------------------------------------------------------------------------
// Pass 3 — Stress test with larger context
// ---------------------------------------------------------------------------

const PASS3_SYSTEM = PASS1_SYSTEM;

const PASS3_USER_TEMPLATE = (snapshot) => `Analyze the following expanded brain snapshot for Helm.

${snapshot}

Respond with a JSON object with exactly these fields:
{
  "patterns": [ list of 2-5 patterns ],
  "contradictions": [ list of 0-3 contradictions ],
  "gaps": [ list of 1-3 gaps ],
  "signal_strength": "high" | "medium" | "low",
  "context_quality": "intact" | "degraded" | "collapsed"
}`;

// ---------------------------------------------------------------------------
// Verdict helpers
// ---------------------------------------------------------------------------

function tryParseJSON(raw) {
  try {
    return { ok: true, data: JSON.parse(raw) };
  } catch (e) {
    // Try to extract JSON from markdown code fences if present
    const match = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (match) {
      try {
        return { ok: true, data: JSON.parse(match[1]) };
      } catch {}
    }
    return { ok: false, error: e.message, raw };
  }
}

function entryText(entry) {
  // Accept plain strings or objects with a "pattern"/"description"/"text"/"summary" field
  if (typeof entry === "string") return entry;
  if (entry && typeof entry === "object") {
    return entry.pattern || entry.description || entry.text || entry.summary || JSON.stringify(entry);
  }
  return String(entry);
}

function assessPass1(data) {
  const issues = [];
  if (!Array.isArray(data.patterns) || data.patterns.length === 0) issues.push("patterns: empty or missing");
  if (!Array.isArray(data.gaps) || data.gaps.length === 0) issues.push("gaps: empty or missing");
  if (!["high", "medium", "low"].includes(data.signal_strength)) issues.push("signal_strength: invalid value");
  if (data.patterns?.length > 0 && data.patterns.some((p) => entryText(p).length < 10))
    issues.push("patterns: entries too short");
  return issues;
}

function assessPass2(data) {
  const issues = [];
  if (!Array.isArray(data.curiosity_flags) || data.curiosity_flags.length === 0)
    issues.push("curiosity_flags: empty or missing");
  if (typeof data.reflection !== "string" || data.reflection.length < 20)
    issues.push("reflection: missing or too short");
  if (data.belief_candidates !== undefined && !Array.isArray(data.belief_candidates))
    issues.push("belief_candidates: not an array");
  return issues;
}

function assessPass3(data) {
  const base = assessPass1(data);
  if (!["intact", "degraded", "collapsed"].includes(data.context_quality))
    base.push("context_quality: invalid value");
  return base;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log("=== Contemplator Feasibility Test ===");
  console.log(`Model: ${CONTEMPLATOR_MODEL}`);
  console.log(`Time:  ${new Date().toISOString()}\n`);

  // Confirm Ollama + model available
  const tagsRes = await fetch(`${OLLAMA_BASE}/api/tags`);
  const tags = await tagsRes.json();
  const available = tags.models?.some((m) => m.name === CONTEMPLATOR_MODEL || m.name.startsWith("qwen2.5:3b"));
  if (!available) {
    console.error(`FATAL: ${CONTEMPLATOR_MODEL} not found in Ollama. Run: ollama pull ${CONTEMPLATOR_MODEL}`);
    process.exit(1);
  }
  console.log(`✓ ${CONTEMPLATOR_MODEL} confirmed in Ollama\n`);

  const { brainUrl, serviceKey } = readConfig();
  console.log("Fetching brain snapshot...");

  // --- Pass 1 ---
  const stdData = await fetchBrainData(brainUrl, serviceKey, { memCount: 10, beliefCount: 8, entityCount: 8 });
  const stdSnapshot = formatSnapshot(stdData);

  console.log(`  Memories: ${stdData.memories.length}, Beliefs: ${stdData.beliefs.length}, Entities: ${stdData.entities.length}`);
  console.log(`  Snapshot size: ${stdSnapshot.length} chars\n`);

  console.log("--- Pass 1: Pattern Synthesis ---");
  const pass1Start = Date.now();
  const pass1Raw = await ollamaChat([
    { role: "system", content: PASS1_SYSTEM },
    { role: "user", content: PASS1_USER_TEMPLATE(stdSnapshot) },
  ]);
  const pass1Ms = Date.now() - pass1Start;
  console.log(`  Inference time: ${(pass1Ms / 1000).toFixed(1)}s`);

  const pass1Parsed = tryParseJSON(pass1Raw);
  if (!pass1Parsed.ok) {
    console.log("  RESULT: FAIL — invalid JSON");
    console.log("  Raw output:", pass1Raw.slice(0, 500));
  } else {
    const issues = assessPass1(pass1Parsed.data);
    console.log(`  RESULT: ${issues.length === 0 ? "PASS" : "PARTIAL/FAIL"}`);
    if (issues.length > 0) console.log("  Issues:", issues);
    console.log("  Patterns:", pass1Parsed.data.patterns?.length ?? 0);
    console.log("  Contradictions:", pass1Parsed.data.contradictions?.length ?? 0);
    console.log("  Gaps:", pass1Parsed.data.gaps?.length ?? 0);
    console.log("  Signal strength:", pass1Parsed.data.signal_strength);
    console.log("\n  Sample pattern:", entryText(pass1Parsed.data.patterns?.[0]).slice(0, 120));
  }
  console.log("\n  Full Pass 1 output:");
  console.log(pass1Raw);

  if (!pass1Parsed.ok) {
    console.log("\n=== OVERALL VERDICT: FAIL (Pass 1 JSON parse failed) ===");
    process.exit(1);
  }

  // --- Pass 2 ---
  console.log("\n--- Pass 2: Evaluation Payload ---");
  const pass2Start = Date.now();
  const pass2Raw = await ollamaChat([
    { role: "system", content: PASS2_SYSTEM },
    { role: "user", content: PASS2_USER_TEMPLATE(pass1Parsed.data) },
  ], { maxTokens: 1200 });
  const pass2Ms = Date.now() - pass2Start;
  console.log(`  Inference time: ${(pass2Ms / 1000).toFixed(1)}s`);

  const pass2Parsed = tryParseJSON(pass2Raw);
  if (!pass2Parsed.ok) {
    console.log("  RESULT: FAIL — invalid JSON");
    console.log("  Raw output:", pass2Raw.slice(0, 500));
  } else {
    const issues = assessPass2(pass2Parsed.data);
    console.log(`  RESULT: ${issues.length === 0 ? "PASS" : "PARTIAL/FAIL"}`);
    if (issues.length > 0) console.log("  Issues:", issues);
    console.log("  Belief candidates:", pass2Parsed.data.belief_candidates?.length ?? 0);
    console.log("  Curiosity flags:", pass2Parsed.data.curiosity_flags?.length ?? 0);
    console.log("  Reflection length:", pass2Parsed.data.reflection?.length ?? 0, "chars");
    if (pass2Parsed.data.reflection) console.log("\n  Reflection:", pass2Parsed.data.reflection);
  }
  console.log("\n  Full Pass 2 output:");
  console.log(pass2Raw);

  // --- Pass 3 — Stress ---
  console.log("\n--- Pass 3: Stress Test (expanded context) ---");
  const bigData = await fetchBrainData(brainUrl, serviceKey, { memCount: 20, beliefCount: 15, entityCount: 15 });
  const bigSnapshot = formatSnapshot(bigData);
  console.log(`  Snapshot size: ${bigSnapshot.length} chars`);

  const pass3Start = Date.now();
  const pass3Raw = await ollamaChat([
    { role: "system", content: PASS3_SYSTEM },
    { role: "user", content: PASS3_USER_TEMPLATE(bigSnapshot) },
  ], { maxTokens: 1200 });
  const pass3Ms = Date.now() - pass3Start;
  console.log(`  Inference time: ${(pass3Ms / 1000).toFixed(1)}s`);

  const pass3Parsed = tryParseJSON(pass3Raw);
  if (!pass3Parsed.ok) {
    console.log("  RESULT: FAIL — invalid JSON");
    console.log("  Raw output:", pass3Raw.slice(0, 500));
  } else {
    const issues = assessPass3(pass3Parsed.data);
    console.log(`  RESULT: ${issues.length === 0 ? "PASS" : "PARTIAL/FAIL"}`);
    if (issues.length > 0) console.log("  Issues:", issues);
    console.log("  Context quality:", pass3Parsed.data.context_quality);
    console.log("  Signal strength:", pass3Parsed.data.signal_strength);
    console.log("  Patterns:", pass3Parsed.data.patterns?.length ?? 0);
  }
  console.log("\n  Full Pass 3 output:");
  console.log(pass3Raw);

  // --- Overall verdict ---
  const pass1Ok = pass1Parsed.ok && assessPass1(pass1Parsed.data).length === 0;
  const pass2Ok = pass2Parsed.ok && assessPass2(pass2Parsed.data).length === 0;
  const pass3Ok = pass3Parsed.ok && assessPass3(pass3Parsed.data).length === 0;

  console.log("\n=== VERDICT SUMMARY ===");
  console.log(`  Pass 1 (Pattern Synthesis):  ${pass1Ok ? "PASS" : "FAIL"}`);
  console.log(`  Pass 2 (Evaluation Payload): ${pass2Ok ? "PASS" : "FAIL"}`);
  console.log(`  Pass 3 (Stress Test):        ${pass3Ok ? "PASS" : "FAIL"}`);

  if (pass1Ok && pass2Ok && pass3Ok) {
    console.log(`\n  OVERALL: PASS — ${CONTEMPLATOR_MODEL} is viable for Contemplator.`);
    console.log(`  Recommendation: write Contemplator contract against ${CONTEMPLATOR_MODEL}.`);
  } else if (pass1Ok && pass2Ok && !pass3Ok) {
    console.log(`\n  OVERALL: MARGINAL — ${CONTEMPLATOR_MODEL} passes standard context, fails stress.`);
    console.log("  Recommendation: scope Contemplator to bounded context window; monitor stress.");
  } else {
    console.log(`\n  OVERALL: FAIL — ${CONTEMPLATOR_MODEL} insufficient for Contemplator role.`);
    console.log("  Recommendation: promote Contemplator to Llama 3.1 8B partition.");
  }
}

main().catch((e) => {
  console.error("FATAL:", e.message);
  process.exit(1);
});
