#!/usr/bin/env node
/**
 * backfill_embeddings.js — Backfill embeddings for existing helm_beliefs and helm_entities rows.
 *
 * Queries all active rows with embedding IS NULL, generates text-embedding-3-small
 * vectors via the OpenAI API, and PATCHes each row. Idempotent — safe to re-run.
 *
 * Usage:
 *   node scripts/backfill_embeddings.js [--dry-run]
 *
 * Environment variables required:
 *   OPENAI_API_KEY             — OpenAI API key
 *   SUPABASE_BRAIN_SERVICE_KEY — Supabase service role key
 *
 * Brain URL is read from hammerfall-config.md.
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const EMBEDDING_MODEL = "text-embedding-3-small";
const BATCH_SIZE = 20;
const BATCH_SLEEP_MS = 1000;
const DRY_RUN = process.argv.includes("--dry-run");

// ---------------------------------------------------------------------------
// Config
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

function getOpenAIKey() {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error("OPENAI_API_KEY is not set.");
  return key;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function supabaseGet(brainUrl, serviceKey, path) {
  const res = await fetch(`${brainUrl}/rest/v1/${path}`, {
    headers: {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
    },
  });
  if (!res.ok) throw new Error(`Supabase GET failed: ${res.status} ${await res.text()}`);
  return res.json();
}

async function supabasePatch(brainUrl, serviceKey, table, rowId, payload) {
  const res = await fetch(`${brainUrl}/rest/v1/${table}?id=eq.${rowId}`, {
    method: "PATCH",
    headers: {
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Supabase PATCH failed: ${res.status} ${await res.text()}`);
}

async function generateEmbedding(text, openaiKey) {
  const res = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${openaiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ model: EMBEDDING_MODEL, input: text }),
  });
  if (!res.ok) throw new Error(`OpenAI embeddings failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  return data.data[0].embedding;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Table backfills
// ---------------------------------------------------------------------------

async function backfillBeliefs(brainUrl, serviceKey, openaiKey) {
  console.log("\n--- helm_beliefs ---");
  const rows = await supabaseGet(
    brainUrl, serviceKey,
    "helm_beliefs?select=id,belief&embedding=is.null&active=eq.true"
  );
  console.log(`  ${rows.length} rows with null embedding`);
  if (!rows.length) return { success: 0, failed: 0 };

  let success = 0, failed = 0;

  for (let i = 0; i < rows.length; i++) {
    const { id, belief } = rows[i];
    const text = (belief || "").trim();

    if (!text) {
      console.log(`  SKIP  [${i+1}/${rows.length}] id=${id} — empty belief text`);
      failed++;
      continue;
    }

    console.log(`  [${i+1}/${rows.length}] id=${id} — ${text.slice(0, 60)}...`);

    if (DRY_RUN) {
      console.log("    DRY RUN — skipping embed + patch");
      success++;
    } else {
      try {
        const embedding = await generateEmbedding(text, openaiKey);
        await supabasePatch(brainUrl, serviceKey, "helm_beliefs", id, { embedding });
        success++;
      } catch (e) {
        console.log(`    ERROR: ${e.message}`);
        failed++;
      }
    }

    if ((i + 1) % BATCH_SIZE === 0 && !DRY_RUN) {
      console.log(`  Batch complete — sleeping ${BATCH_SLEEP_MS}ms`);
      await sleep(BATCH_SLEEP_MS);
    }
  }

  return { success, failed };
}

async function backfillEntities(brainUrl, serviceKey, openaiKey) {
  console.log("\n--- helm_entities ---");
  const rows = await supabaseGet(
    brainUrl, serviceKey,
    "helm_entities?select=id,name,summary&embedding=is.null&active=eq.true"
  );
  console.log(`  ${rows.length} rows with null embedding`);
  if (!rows.length) return { success: 0, failed: 0 };

  let success = 0, failed = 0;

  for (let i = 0; i < rows.length; i++) {
    const { id, name, summary } = rows[i];
    const nameText = (name || "").trim();
    const summaryText = (summary || "").trim();

    if (!nameText) {
      console.log(`  SKIP  [${i+1}/${rows.length}] id=${id} — empty name`);
      failed++;
      continue;
    }

    const embedText = summaryText ? `${nameText} — ${summaryText}` : nameText;
    console.log(`  [${i+1}/${rows.length}] id=${id} — ${embedText.slice(0, 60)}...`);

    if (DRY_RUN) {
      console.log("    DRY RUN — skipping embed + patch");
      success++;
    } else {
      try {
        const embedding = await generateEmbedding(embedText, openaiKey);
        await supabasePatch(brainUrl, serviceKey, "helm_entities", id, { embedding });
        success++;
      } catch (e) {
        console.log(`    ERROR: ${e.message}`);
        failed++;
      }
    }

    if ((i + 1) % BATCH_SIZE === 0 && !DRY_RUN) {
      console.log(`  Batch complete — sleeping ${BATCH_SLEEP_MS}ms`);
      await sleep(BATCH_SLEEP_MS);
    }
  }

  return { success, failed };
}

async function backfillMemory(brainUrl, serviceKey, openaiKey) {
  console.log("\n--- helm_memory ---");
  const rows = await supabaseGet(
    brainUrl, serviceKey,
    "helm_memory?select=id,content&embedding=is.null"
  );
  console.log(`  ${rows.length} rows with null embedding`);
  if (!rows.length) return { success: 0, failed: 0 };

  let success = 0, failed = 0;

  for (let i = 0; i < rows.length; i++) {
    const { id, content } = rows[i];
    const text = (content || "").trim();

    if (!text) {
      console.log(`  SKIP  [${i+1}/${rows.length}] id=${id} — empty content`);
      failed++;
      continue;
    }

    console.log(`  [${i+1}/${rows.length}] id=${id} — ${text.slice(0, 60)}...`);

    if (DRY_RUN) {
      console.log("    DRY RUN — skipping embed + patch");
      success++;
    } else {
      try {
        const embedding = await generateEmbedding(text, openaiKey);
        await supabasePatch(brainUrl, serviceKey, "helm_memory", id, { embedding });
        success++;
      } catch (e) {
        console.log(`    ERROR: ${e.message}`);
        failed++;
      }
    }

    if ((i + 1) % BATCH_SIZE === 0 && !DRY_RUN) {
      console.log(`  Batch complete — sleeping ${BATCH_SLEEP_MS}ms`);
      await sleep(BATCH_SLEEP_MS);
    }
  }

  return { success, failed };
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

async function main() {
  if (DRY_RUN) console.log("=== DRY RUN — no writes will occur ===");

  const { brainUrl, serviceKey } = readConfig();
  const openaiKey = DRY_RUN ? "dry-run" : getOpenAIKey();

  console.log(`Brain URL: ${brainUrl}`);
  console.log(`Model:     ${EMBEDDING_MODEL}`);

  const memory = await backfillMemory(brainUrl, serviceKey, openaiKey);
  const beliefs = await backfillBeliefs(brainUrl, serviceKey, openaiKey);
  const entities = await backfillEntities(brainUrl, serviceKey, openaiKey);

  const totalSuccess = memory.success + beliefs.success + entities.success;
  const totalFailed = memory.failed + beliefs.failed + entities.failed;

  console.log(`\n=== Backfill complete ===`);
  console.log(`  helm_memory:   ${memory.success} embedded, ${memory.failed} failed/skipped`);
  console.log(`  helm_beliefs:  ${beliefs.success} embedded, ${beliefs.failed} failed/skipped`);
  console.log(`  helm_entities: ${entities.success} embedded, ${entities.failed} failed/skipped`);
  console.log(`  Total:         ${totalSuccess} embedded, ${totalFailed} failed/skipped`);

  if (totalFailed > 0) {
    console.log(`\n  ${totalFailed} rows still have null embedding — re-run to retry.`);
    process.exit(1);
  }
}

main().catch((e) => { console.error("FATAL:", e.message); process.exit(1); });
