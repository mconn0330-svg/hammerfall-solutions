#!/usr/bin/env python3
"""
backfill_embeddings.py — Backfill embeddings for existing helm_beliefs and helm_entities rows.

Queries all rows with embedding IS NULL, generates text-embedding-3-small vectors
via the OpenAI API, and PATCHes each row. Idempotent — safe to re-run.

Usage:
    python3 scripts/backfill_embeddings.py [--dry-run]

Environment variables required:
    OPENAI_API_KEY           — OpenAI API key for embedding generation
    SUPABASE_BRAIN_SERVICE_KEY — Supabase service role key

Brain URL and service key env var name are read from hammerfall-config.md.
"""

import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.request
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 20          # rows per batch before sleeping
BATCH_SLEEP = 1.0        # seconds between batches (rate limit headroom)
REQUEST_TIMEOUT = 20     # seconds per OpenAI API call

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR.parent / "hammerfall-config.md"


def read_config() -> tuple[str, str]:
    """Read BRAIN_URL and SERVICE_KEY from hammerfall-config.md + env."""
    text = CONFIG_FILE.read_text()

    url_match = re.search(r"supabase_brain_url:\s*(\S+)", text)
    key_env_match = re.search(r"supabase_brain_service_key_env:\s*(\S+)", text)

    if not url_match:
        sys.exit("ERROR: supabase_brain_url not found in hammerfall-config.md")
    if not key_env_match:
        sys.exit("ERROR: supabase_brain_service_key_env not found in hammerfall-config.md")

    brain_url = url_match.group(1).rstrip("/")
    key_env = key_env_match.group(1)
    service_key = os.environ.get(key_env)

    if not service_key:
        sys.exit(f"ERROR: env var '{key_env}' is not set.")

    return brain_url, service_key


def get_openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("ERROR: OPENAI_API_KEY is not set.")
    return key


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def supabase_get(brain_url: str, service_key: str, path: str) -> list:
    """GET from Supabase REST API."""
    req = urllib.request.Request(
        f"{brain_url}/rest/v1/{path}",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def supabase_patch(brain_url: str, service_key: str, table: str, row_id: str, payload: dict) -> None:
    """PATCH a single row by id."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{brain_url}/rest/v1/{table}?id=eq.{row_id}",
        data=data,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def generate_embedding(text: str, openai_key: str) -> list[float] | None:
    """Call text-embedding-3-small. Returns vector or None on failure."""
    data = json.dumps({"model": EMBEDDING_MODEL, "input": text}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=data,
        headers={
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            result = json.load(resp)
            return result["data"][0]["embedding"]
    except Exception as e:
        print(f"    WARNING: embedding generation failed — {e}")
        return None


# ---------------------------------------------------------------------------
# Table backfills
# ---------------------------------------------------------------------------

def backfill_beliefs(brain_url: str, service_key: str, openai_key: str, dry_run: bool) -> tuple[int, int]:
    """
    Backfill helm_beliefs rows with embedding IS NULL.
    Embed the belief text (the main semantic content).
    Returns (success_count, failed_count).
    """
    print("\n--- helm_beliefs ---")
    rows = supabase_get(
        brain_url, service_key,
        "helm_beliefs?select=id,belief&embedding=is.null&active=eq.true",
    )
    print(f"  {len(rows)} rows with null embedding")

    if not rows:
        return 0, 0

    success = 0
    failed = 0

    for i, row in enumerate(rows):
        row_id = row["id"]
        belief_text = row.get("belief", "").strip()

        if not belief_text:
            print(f"  SKIP  [{i+1}/{len(rows)}] id={row_id} — empty belief text")
            failed += 1
            continue

        print(f"  [{i+1}/{len(rows)}] id={row_id} — {belief_text[:60]}...")

        if dry_run:
            print("    DRY RUN — skipping embed + patch")
            success += 1
        else:
            embedding = generate_embedding(belief_text, openai_key)
            if embedding is None:
                failed += 1
            else:
                try:
                    supabase_patch(brain_url, service_key, "helm_beliefs", row_id, {"embedding": embedding})
                    success += 1
                except Exception as e:
                    print(f"    ERROR: patch failed — {e}")
                    failed += 1

        if (i + 1) % BATCH_SIZE == 0 and not dry_run:
            print(f"  Batch complete — sleeping {BATCH_SLEEP}s")
            time.sleep(BATCH_SLEEP)

    return success, failed


def backfill_entities(brain_url: str, service_key: str, openai_key: str, dry_run: bool) -> tuple[int, int]:
    """
    Backfill helm_entities rows with embedding IS NULL.
    Embed "name — summary" when summary is present, else just name.
    Returns (success_count, failed_count).
    """
    print("\n--- helm_entities ---")
    rows = supabase_get(
        brain_url, service_key,
        "helm_entities?select=id,name,summary&embedding=is.null&active=eq.true",
    )
    print(f"  {len(rows)} rows with null embedding")

    if not rows:
        return 0, 0

    success = 0
    failed = 0

    for i, row in enumerate(rows):
        row_id = row["id"]
        name = (row.get("name") or "").strip()
        summary = (row.get("summary") or "").strip()

        if not name:
            print(f"  SKIP  [{i+1}/{len(rows)}] id={row_id} — empty name")
            failed += 1
            continue

        embed_text = f"{name} — {summary}" if summary else name
        print(f"  [{i+1}/{len(rows)}] id={row_id} — {embed_text[:60]}...")

        if dry_run:
            print("    DRY RUN — skipping embed + patch")
            success += 1
        else:
            embedding = generate_embedding(embed_text, openai_key)
            if embedding is None:
                failed += 1
            else:
                try:
                    supabase_patch(brain_url, service_key, "helm_entities", row_id, {"embedding": embedding})
                    success += 1
                except Exception as e:
                    print(f"    ERROR: patch failed — {e}")
                    failed += 1

        if (i + 1) % BATCH_SIZE == 0 and not dry_run:
            print(f"  Batch complete — sleeping {BATCH_SLEEP}s")
            time.sleep(BATCH_SLEEP)

    return success, failed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Backfill embeddings for helm_beliefs and helm_entities.")
    parser.add_argument("--dry-run", action="store_true", help="Query rows and print plan without writing.")
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN — no writes will occur ===")

    brain_url, service_key = read_config()
    openai_key = get_openai_key() if not args.dry_run else "dry-run"

    print(f"Brain URL: {brain_url}")
    print(f"Model:     {EMBEDDING_MODEL}")

    b_success, b_failed = backfill_beliefs(brain_url, service_key, openai_key, args.dry_run)
    e_success, e_failed = backfill_entities(brain_url, service_key, openai_key, args.dry_run)

    total_success = b_success + e_success
    total_failed = b_failed + e_failed

    print(f"\n=== Backfill complete ===")
    print(f"  helm_beliefs:  {b_success} embedded, {b_failed} failed/skipped")
    print(f"  helm_entities: {e_success} embedded, {e_failed} failed/skipped")
    print(f"  Total:         {total_success} embedded, {total_failed} failed/skipped")

    if total_failed > 0:
        print(f"\n  {total_failed} rows still have null embedding — re-run to retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
