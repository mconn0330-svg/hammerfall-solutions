/**
 * speaker_prompt_test.js — Speaker classification prompt validation
 *
 * Validates the updated CLASSIFICATION_SYSTEM_PROMPT against qwen3:8b (no-think),
 * the confirmed Speaker model. Runs two suites:
 *
 *   Suite A — Regression: the original 10 cases from the cross-gen stress test.
 *             Establishes baseline delta vs. the old prompt. Any regression here is a blocker.
 *
 *   Suite B — AMBIGUOUS section: 10 new cases targeting the specific failure class
 *             ("What's the status?" and similar context-dependent queries). These are the
 *             cases every model missed under the old prompt.
 *
 * Usage:
 *   node scripts/speaker_prompt_test.js
 *
 * Requires:
 *   OLLAMA_BASE_URL env var (defaults to http://localhost:11434)
 */

const OLLAMA_URL = (process.env.OLLAMA_BASE_URL || "http://localhost:11434").replace(/\/$/, "");
const MODEL      = "qwen3:8b";
const THINK      = false;

// ---------------------------------------------------------------------------
// Updated CLASSIFICATION_SYSTEM_PROMPT (from services/helm-runtime/agents/speaker.py)
// Must stay in sync with the live prompt.
// ---------------------------------------------------------------------------

const CLASSIFICATION_SYSTEM_PROMPT = `You are Speaker, the routing layer for Helm — Maxwell's AI director.

Your job: classify the incoming request as simple or complex, then act on that classification.

SIMPLE requests — resolve locally:
- Factual recall with a fully self-contained answer (time, date, definition)
- Confirmations and acknowledgements
- Greetings and pleasantries
- One-turn questions requiring no prior context and no strategic judgment

COMPLEX requests — route to Helm Prime:
- Architectural decisions or design questions
- Multi-step plans or sequences
- Anything requiring prior session context or memory
- Anything belief-linked (references values, tradeoffs, principles)
- Anything Maxwell would evaluate for quality, correctness, or strategic alignment
- Anything consequential or irreversible
- Any question containing "status", "update", "progress", or "where are we"
  without a specific named subject — these require session context to answer correctly
- Any question that cannot be answered without knowing what was discussed
  in this session. If you are not certain the question is fully self-contained,
  route to Helm Prime.

AMBIGUOUS — always route to Helm Prime:
- "What's the status?" / "Any updates?" / "Where are we?"
  (no specific subject — requires session context)
- "What do you think?" / "Does that make sense?" / "Is that right?"
  (requires Helm's judgment)
- "Should we proceed?" / "Are we good?"
  (consequential, requires strategic awareness)
- "Go ahead and push/merge/deploy/delete/send [X]" — directive to take
  an immediate irreversible action. This is NOT a confirmation or
  acknowledgement. It is an instruction. Always Helm Prime.
- "Go ahead and [verb]" with no subject — same rule. When in doubt
  about irreversibility, route to Helm Prime.
- Any single-word or short-phrase question that depends on shared context

WHEN IN DOUBT: route to Helm Prime.
The cost of a wrong local resolution is always higher than an unnecessary escalation.

RESPONSE FORMAT — return ONLY valid JSON. No explanation, no preamble, no markdown.

For simple (resolve locally):
{"routing": "local", "response": "<your direct answer here>"}

For complex (route to Helm Prime):
{"routing": "helm_prime"}

The response field is only present when routing is "local".
Never include both. Never include neither.`;

// ---------------------------------------------------------------------------
// Suite A — Regression (original 10 cases from cross-gen stress test)
// All 10 must pass. Any failure is a regression.
// ---------------------------------------------------------------------------

const SUITE_A = [
  { label: "greeting",               message: "Good morning.",                                                       expected: "local",      risk: "low"  },
  { label: "acknowledgement",        message: "OK, got it.",                                                         expected: "local",      risk: "low"  },
  { label: "date question",          message: "What is today's date?",                                               expected: "local",      risk: "low"  },
  { label: "architectural decision", message: "Should we use pgvector or Pinecone for Stage 2?",                      expected: "helm_prime", risk: "high" },
  { label: "multi-step plan",        message: "Can you plan out the BA3 implementation steps?",                       expected: "helm_prime", risk: "high" },
  { label: "belief-linked question", message: "Do you think the current agent architecture is the right approach?",   expected: "helm_prime", risk: "high" },
  { label: "ambiguous status check", message: "What's the status?",                                                  expected: "helm_prime", risk: "medium" }, // universal miss under old prompt
  { label: "memory-dependent",       message: "Did we decide on a model for Contemplator?",                           expected: "helm_prime", risk: "high" },
  { label: "consequential action",   message: "Go ahead and push the PR.",                                            expected: "helm_prime", risk: "high" },
  { label: "simple confirm",         message: "Confirmed — branch is deleted.",                                       expected: "local",      risk: "low"  },
];

// ---------------------------------------------------------------------------
// Suite B — AMBIGUOUS section coverage (new cases targeting the fix)
// Tests the AMBIGUOUS category and the two new COMPLEX rules directly.
// ---------------------------------------------------------------------------

const SUITE_B = [
  // Named-subject rule — "status" with specific subject → could be local; without → helm_prime
  { label: "status — no subject",          message: "Any updates?",                                                   expected: "helm_prime", risk: "medium" },
  { label: "status — no subject 2",        message: "Where are we?",                                                  expected: "helm_prime", risk: "medium" },
  { label: "status — named subject",       message: "What is the status of PR #66?",                                  expected: "helm_prime", risk: "low"    }, // named, but still requires context — helm_prime is acceptable; local is also defensible
  { label: "progress — no subject",        message: "What's the progress?",                                           expected: "helm_prime", risk: "medium" },
  // Judgment / approval queries
  { label: "judgment — does that make sense", message: "Does that make sense?",                                       expected: "helm_prime", risk: "medium" },
  { label: "judgment — is that right",     message: "Is that right?",                                                 expected: "helm_prime", risk: "medium" },
  { label: "proceed — no context",         message: "Should we proceed?",                                             expected: "helm_prime", risk: "high"   },
  { label: "are we good",                  message: "Are we good?",                                                   expected: "helm_prime", risk: "medium" },
  // Prior-context-dependency rule
  { label: "session-dependent what",       message: "What did we decide?",                                            expected: "helm_prime", risk: "high"   },
  { label: "session-dependent where",      message: "Where did we land on that?",                                     expected: "helm_prime", risk: "high"   },
];

// ---------------------------------------------------------------------------
// Ollama chat
// ---------------------------------------------------------------------------

async function ollamaChat(messages) {
  const body = { model: MODEL, messages, stream: false, format: "json", options: { temperature: 0.1 } };
  if (THINK === false) body.think = false;
  const res = await fetch(`${OLLAMA_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.message?.content ?? "";
}

function tryParse(raw) {
  try { return JSON.parse(raw.trim()); } catch { return null; }
}

// ---------------------------------------------------------------------------
// Run a suite
// ---------------------------------------------------------------------------

async function runSuite(name, cases) {
  console.log(`\n${"=".repeat(68)}`);
  console.log(`  ${name}`);
  console.log(`  Model: ${MODEL} | think: ${THINK}`);
  console.log("=".repeat(68));

  let pass = 0, fail = 0, highRiskFail = 0;
  const failures = [];

  for (const tc of cases) {
    process.stdout.write(`  ${tc.label.padEnd(38)} `);
    try {
      const raw = await ollamaChat([
        { role: "system", content: CLASSIFICATION_SYSTEM_PROMPT },
        { role: "user",   content: tc.message },
      ]);
      const parsed = tryParse(raw);
      if (!parsed) {
        process.stdout.write(`PARSE FAIL  raw=${raw.slice(0,60)}\n`);
        fail++;
        if (tc.risk === "high") highRiskFail++;
        failures.push(`"${tc.label}" — JSON parse failed`);
        continue;
      }
      const routing = parsed.routing;
      const ok = routing === tc.expected;
      if (ok) {
        const resp = parsed.response ? `  "${parsed.response.slice(0,40)}${parsed.response.length > 40 ? "…" : ""}"` : "";
        process.stdout.write(`PASS  → ${routing}${resp}\n`);
        pass++;
      } else {
        const note = tc.risk === "high" ? " ⚠ HIGH-RISK" : tc.risk === "medium" ? " ↑ medium" : "";
        process.stdout.write(`FAIL  → got=${routing} expected=${tc.expected}${note}\n`);
        fail++;
        if (tc.risk === "high") highRiskFail++;
        failures.push(`"${tc.label}" — got ${routing}, expected ${tc.expected} [${tc.risk}]`);
      }
    } catch (e) {
      process.stdout.write(`ERROR  ${e.message.slice(0,60)}\n`);
      fail++;
      failures.push(`"${tc.label}" — error: ${e.message}`);
    }
  }

  const total = pass + fail;
  const pct   = Math.round((pass / total) * 100);
  console.log(`\n  Result: ${pass}/${total} (${pct}%)${highRiskFail > 0 ? `  ⚠ ${highRiskFail} high-risk failure(s)` : ""}`);
  if (failures.length) {
    console.log("  Failures:");
    failures.forEach(f => console.log(`    - ${f}`));
  }

  return { pass, fail, total, highRiskFail, failures };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log("\nSpeaker Classification Prompt Validation");
  console.log(`Model: ${MODEL}  |  think: ${THINK}`);
  console.log("Testing updated prompt against regression suite + AMBIGUOUS section coverage.\n");

  const a = await runSuite("Suite A — Regression (10 original cases)", SUITE_A);
  const b = await runSuite("Suite B — AMBIGUOUS section coverage (10 new cases)", SUITE_B);

  const total  = a.total + b.total;
  const passed = a.pass  + b.pass;
  const hrFail = a.highRiskFail + b.highRiskFail;

  console.log(`\n${"=".repeat(68)}`);
  console.log("  OVERALL SUMMARY");
  console.log("=".repeat(68));
  console.log(`  Suite A (regression):  ${a.pass}/${a.total} (${Math.round(a.pass/a.total*100)}%)`);
  console.log(`  Suite B (AMBIGUOUS):   ${b.pass}/${b.total} (${Math.round(b.pass/b.total*100)}%)`);
  console.log(`  Combined:              ${passed}/${total} (${Math.round(passed/total*100)}%)`);
  if (hrFail > 0) console.log(`  High-risk failures:    ${hrFail}  ⚠`);

  console.log("\n  Baseline (old prompt, qwen3:8b no-think from cross-gen test):");
  console.log("    Suite A equivalent:  8/10 (80%) — 'What's the status?' and one other missed");
  console.log(`    Suite B equivalent:  N/A  (new cases, no prior baseline)\n`);

  if (a.pass === a.total && hrFail === 0) {
    console.log("  ✓ Regression suite: PASS — no regressions on original cases.");
  } else if (a.highRiskFail > 0) {
    console.log("  ✗ Regression suite: HIGH-RISK FAILURE — review before BA5 E2E.");
  } else {
    console.log("  ~ Regression suite: partial — check failures above.");
  }
}

main().catch(e => { console.error("FATAL:", e.message); process.exit(1); });
