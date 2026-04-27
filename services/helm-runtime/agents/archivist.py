"""
archivist.py — Archivist agent handler.

Two responsibilities:

1. Cold frame migration — reads cold frames from helm_frames via memory.read_frames(),
   generates a 1-3 sentence summary per frame via qwen3:14b on Ollama, writes to
   helm_memory at full fidelity via memory.MemoryWriter (durable + outbox-fallback),
   then deletes the helm_frames row.

2. Contemplator write handoff — when req.context contains "contemplator_writes",
   executes the structured payload (belief patches, pattern entries, curiosity
   flags, reflection log). Pattern/curiosity/monologue inserts go through the
   memory module; belief/personality PATCHes stay through SupabaseClient
   (sibling-table modifies — no outbox semantics needed).

Write paths (T0.B3+):
  helm_memory inserts → memory.MemoryWriter
  helm_beliefs PATCH  → SupabaseClient (sibling-table modify)
  helm_personality PATCH → SupabaseClient (sibling-table modify)
  helm_frames DELETE → SupabaseClient (cleanup after migration confirmed)

Read paths:
  Cold-frame queue → memory.read_frames(layer="cold") (T0.B3 migration)
  helm_beliefs SELECT → SupabaseClient (current-strength lookup before PATCH)
  helm_personality SELECT → SupabaseClient (current-score lookup before PATCH)

Safety net: cold frames stay in helm_frames on any write failure —
            retried on next Archivist invocation. Nothing is lost.

frame_status source of truth: the helm_frames column (authoritative per BA6
Projectionist contract). The column value is written into full_content JSONB.
"""

import asyncio
import logging
from datetime import date
from pathlib import Path
from typing import Any

from embedding_client import EmbeddingClient
from memory import MemoryType, MemoryWriter, PromptManager, read_frames
from middleware import InvokeRequest
from model_router import ModelRouter
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt fallback path — Supabase canonical (agent_role='archivist'),
# this file is the boot-time fallback. The model's only job is summarizing
# a turn into 1-3 sentences (no JSON output required).
# ---------------------------------------------------------------------------

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "archivist.md"


async def handle(
    req: InvokeRequest,
    router: ModelRouter,
    supabase: SupabaseClient,
    writer: MemoryWriter,
    prompt_manager: PromptManager,
    embedding_client: EmbeddingClient | None = None,
) -> str:
    """
    Archivist entry point.

    If req.context contains "contemplator_writes": execute the Contemplator
    write payload (belief patches, pattern entries, curiosity flags, reflection).
    No model call. Returns a summary of what was written.

    Otherwise: migrate all cold frames from helm_frames to helm_memory.
    For each cold frame:
      1. Generate a 1-3 sentence summary via the model
      2. Write to helm_memory at full fidelity (summary in content, full frame in full_content)
      3. Delete the helm_frames row only after confirmed write
      4. On write failure: leave frame in helm_frames, log, continue to next frame

    Returns a summary of what was migrated.
    """
    contemplator_payload = req.context.get("contemplator_writes")
    if contemplator_payload:
        logger.info("Archivist: received contemplator_writes payload. session=%s", req.session_id)
        return await _execute_contemplator_writes(
            contemplator_payload, supabase, writer, embedding_client
        )

    # Load summary prompt via PromptManager (Supabase canonical, file fallback)
    summary_system_prompt = await prompt_manager.load("archivist", fallback_path=PROMPT_PATH)

    # Query all cold frames via memory.read_frames — not scoped to session,
    # Archivist clears the full cold queue.
    cold_frames = await read_frames(supabase, layer="cold")

    if not cold_frames:
        logger.info("Archivist: no cold frames to migrate.")
        return "No cold frames pending migration."

    logger.info("Archivist: found %d cold frame(s) to migrate.", len(cold_frames))

    migrated = 0
    failed = 0

    for frame_row in cold_frames:
        frame_id = frame_row["id"]
        frame_json = frame_row.get("frame_json", {})
        # frame_status column is authoritative — read from row, not from frame_json
        frame_status = frame_row.get("frame_status", "active")

        user_msg = frame_json.get("user", "")
        helm_msg = frame_json.get("helm", "")

        # Generate summary via model
        summary = await _generate_summary(
            router=router,
            user_msg=user_msg,
            helm_msg=helm_msg,
            frame_id=frame_id,
            system_prompt=summary_system_prompt,
        )
        if summary is None:
            # All retries exhausted — leave frame in cold, continue
            failed += 1
            continue

        # Build full_content — verbatim frame_json with frame_status from the column
        full_content = dict(frame_json)
        full_content["frame_status"] = frame_status  # column is authoritative

        # session_date extracted from ISO timestamp in frame_json (first 10 chars:
        # YYYY-MM-DD). Indexes the helm_memory row to when the conversation
        # actually happened — not when the drain ran. Used as a filter field
        # at Stage 1 pgvector semantic search.
        session_date = _parse_session_date(full_content.get("timestamp"))

        # Note: frames don't carry per-row embeddings — the summary text gets
        # embedded at retrieval time. Pattern / monologue / curiosity writes
        # below DO carry embeddings (high-value semantic-search targets).

        # Write to helm_memory via memory.MemoryWriter — durable + outbox-fallback.
        write_ok = await _write_frame_to_memory(
            writer=writer,
            project=req.context.get("project", "hammerfall-solutions"),
            agent=req.context.get("agent", "helm"),
            content=summary,
            full_content=full_content,
            session_date=session_date,
            frame_id=frame_id,
        )
        if not write_ok:
            # Write failed — frame stays in cold, retried next invocation.
            failed += 1
            continue

        # Delete helm_frames row only after confirmed write
        try:
            await supabase.delete("helm_frames", {"id": frame_id})
            logger.info(
                "Archivist migrated frame: id=%s status=%s topic=%r",
                frame_id,
                frame_status,
                frame_json.get("topic"),
            )
            migrated += 1
        except Exception as e:
            logger.error(
                "Archivist: helm_frames delete failed for id=%s — frame may be duplicated "
                "in helm_memory on next run. error=%s",
                frame_id,
                e,
            )
            # Do not count as failed — the memory write succeeded.
            # The duplicate-on-retry risk is acceptable; helm_memory has no unique constraint
            # on frame content. Log clearly so it can be investigated.
            migrated += 1

    result = (
        f"Archivist migration complete: {migrated} migrated, {failed} failed (left in cold queue)."
    )
    logger.info(result)
    return result


async def _generate_summary(
    router: ModelRouter,
    user_msg: str,
    helm_msg: str,
    frame_id: str,
    system_prompt: str,
) -> str | None:
    """
    Generate a 1-3 sentence summary of a turn via the model.
    Retries up to 3 attempts with 0.5s backoff on transient model failure.
    Returns the summary string, or None if all attempts fail.

    `system_prompt` is loaded by the caller via PromptManager — passed in
    rather than fetched here so the prompt-load happens once per Archivist
    invocation, not once per frame.
    """
    user_prompt = f"""User message:
{user_msg}

Helm response:
{helm_msg}

Summarize this turn in 1-3 sentences."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    _max_attempts = 3
    _retry_delay = 0.5

    for attempt in range(_max_attempts):
        try:
            response = await router.invoke(
                role="archivist",
                messages=messages,
                stream=False,
            )
            summary: str = response.choices[0].message.content.strip()
            if not summary:
                raise ValueError("Model returned empty summary")
            return summary
        except Exception as e:
            if attempt < _max_attempts - 1:
                logger.warning(
                    "Archivist summary generation failed (attempt %d/%d) for frame=%s: %s — retrying in %.1fs",
                    attempt + 1,
                    _max_attempts,
                    frame_id,
                    e,
                    _retry_delay,
                )
                await asyncio.sleep(_retry_delay)
            else:
                logger.error(
                    "Archivist summary generation failed after %d attempts for frame=%s: %s — "
                    "frame left in cold queue for retry.",
                    _max_attempts,
                    frame_id,
                    e,
                )
                return None
    return None  # unreachable; satisfies mypy's missing-return analysis


async def _execute_contemplator_writes(
    payload: dict[str, Any],
    supabase: SupabaseClient,
    writer: MemoryWriter,
    embedding_client: EmbeddingClient | None = None,
) -> str:
    """
    Execute the structured write payload produced by Contemplator after a session_end pass.

    Payload fields (all optional — any may be empty):
      belief_patches      — list of {id, strength_delta, rationale}
                            PATCH helm_beliefs.strength (clamped 0.0–1.0)
      personality_patches — list of {attribute, score_delta, rationale}
                            PATCH helm_personality.score (clamped 0.0–10.0)
                            Requires 2+ corroborating observations — Contemplator enforces
                            this constraint in its Pass 2 prompt.
      pattern_entries     — list of {content, memory_type, source}
                            INSERT into helm_memory (memory_type=pattern)
      curiosity_flags     — list of {topic, question, priority, type}
                            INSERT into helm_memory (memory_type=curiosity_flag)
      reflection          — {content, memory_type}
                            INSERT into helm_memory (memory_type=monologue)

    Embeddings: generated for pattern_entries, curiosity_flags, and reflection if
    embedding_client is available. Non-fatal — writes proceed without embedding on
    any failure. Full content is embedded (not truncated) per architect guidance.

    Returns a one-line summary string. Errors are logged and collected but do
    not abort remaining writes — all writes are attempted regardless of failures.
    """
    # session_date defaults to today via MemoryWriter's MemoryEntry factory —
    # contemplator writes ARE produced today, so the default is correct.
    results: dict[str, Any] = {
        "belief_patches": 0,
        "personality_patches": 0,
        "pattern_entries": 0,
        "curiosity_flags": 0,
        "reflection": False,
        "errors": [],
    }

    # --- Belief patches ---
    for patch in payload.get("belief_patches", []):
        belief_id = patch.get("id")
        try:
            delta = float(patch["strength_delta"])
            rows = await supabase.select(
                "helm_beliefs",
                {"id": f"eq.{belief_id}", "select": "id,strength"},
            )
            if not rows:
                results["errors"].append(f"belief_patch {belief_id}: not found")
                continue
            current = float(rows[0]["strength"])
            new_strength = round(max(0.0, min(1.0, current + delta)), 4)
            await supabase.patch("helm_beliefs", {"id": belief_id}, {"strength": new_strength})
            logger.info(
                "Archivist: belief patched id=%s %.4f→%.4f (delta=%.4f)",
                belief_id,
                current,
                new_strength,
                delta,
            )
            results["belief_patches"] += 1
        except Exception as e:
            logger.error("Archivist: belief_patch failed id=%s: %s", belief_id, e)
            results["errors"].append(f"belief_patch {belief_id}: {e}")

    # --- Personality patches ---
    # Requires 2+ corroborating observations — Contemplator enforces in Pass 2 prompt.
    # Scores clamped 0.0–1.0 — matches helm_personality score scale. Displayed as /10 in user-facing contexts is a rendering choice made at presentation time.
    for patch in payload.get("personality_patches", []):
        attr = patch.get("attribute")
        try:
            delta = float(patch["score_delta"])
            rows = await supabase.select(
                "helm_personality",
                {"attribute": f"eq.{attr}", "select": "attribute,score"},
            )
            if not rows:
                results["errors"].append(f"personality_patch {attr}: not found")
                continue
            current = float(rows[0]["score"])
            new_score = round(max(0.0, min(1.0, current + delta)), 4)
            await supabase.patch("helm_personality", {"attribute": attr}, {"score": new_score})
            logger.info(
                "Archivist: personality patched attribute=%s %.4f→%.4f (delta=%.4f)",
                attr,
                current,
                new_score,
                delta,
            )
            results["personality_patches"] += 1
        except Exception as e:
            logger.error("Archivist: personality_patch failed attribute=%s: %s", attr, e)
            results["errors"].append(f"personality_patch {attr}: {e}")

    # --- Pattern entries ---
    for entry in payload.get("pattern_entries", []):
        try:
            content = entry["content"]
            embedding = None
            if embedding_client is not None:
                embedding = await embedding_client.generate(content)
            await writer.write(
                project="hammerfall-solutions",
                agent="helm",
                memory_type=MemoryType.PATTERN,
                content=content,
                embedding=embedding,
            )
            results["pattern_entries"] += 1
        except Exception as e:
            logger.error("Archivist: pattern_entry write failed: %s", e)
            results["errors"].append(f"pattern_entry: {e}")

    # --- Curiosity flags ---
    # Note: T0.B7b lands `helm_curiosities` as a sibling table with its own
    # MemoryType.CURIOSITY enum value. Until then, curiosity flags piggyback on
    # `helm_memory` with `memory_type='curiosity_flag'` (legacy literal — not
    # a Tier 1 enum value). Using writer.write() with the literal string
    # preserves backwards compatibility; the existing rows in helm_memory
    # remain queryable.
    for flag in payload.get("curiosity_flags", []):
        try:
            flag_type = flag.get("type", "unknown").upper()
            topic = flag.get("topic", "")
            question = flag.get("question", "")
            content = f"[CURIOUS:{flag_type}] {topic} — {question}"
            embedding = None
            if embedding_client is not None:
                embedding = await embedding_client.generate(content)
            await writer.write(
                project="hammerfall-solutions",
                agent="helm",
                memory_type="curiosity_flag",  # legacy literal — see comment above
                content=content,
                embedding=embedding,
            )
            results["curiosity_flags"] += 1
        except Exception as e:
            logger.error("Archivist: curiosity_flag write failed: %s", e)
            results["errors"].append(f"curiosity_flag: {e}")

    # --- Reflection (monologue) ---
    # Highest-value embedding target — full content embedded, no truncation.
    reflection = payload.get("reflection")
    if reflection and reflection.get("content"):
        try:
            content = reflection["content"]
            embedding = None
            if embedding_client is not None:
                embedding = await embedding_client.generate(content)
            await writer.write_monologue(
                project="hammerfall-solutions",
                agent="helm",
                content=content,
                embedding=embedding,
            )
            results["reflection"] = True
        except Exception as e:
            logger.error("Archivist: reflection write failed: %s", e)
            results["errors"].append(f"reflection: {e}")

    summary = (
        f"Contemplator writes complete: "
        f"{results['belief_patches']} belief patches, "
        f"{results['personality_patches']} personality patches, "
        f"{results['pattern_entries']} pattern entries, "
        f"{results['curiosity_flags']} curiosity flags, "
        f"reflection={'yes' if results['reflection'] else 'no'}."
    )
    if results["errors"]:
        summary += f" Errors ({len(results['errors'])}): {'; '.join(results['errors'])}"
    logger.info(summary)
    return summary


def _parse_session_date(raw_timestamp: Any) -> date | None:
    """Pull the date portion from an ISO-8601 timestamp string. Returns None
    on missing / malformed input — caller falls back to MemoryWriter's
    default (today). Used by frame migration to preserve the original
    conversation date in helm_memory.session_date."""
    if not isinstance(raw_timestamp, str) or len(raw_timestamp) < 10:
        return None
    try:
        return date.fromisoformat(raw_timestamp[:10])
    except ValueError:
        return None


async def _write_frame_to_memory(
    *,
    writer: MemoryWriter,
    project: str,
    agent: str,
    content: str,
    full_content: dict[str, Any],
    session_date: date | None,
    frame_id: str,
) -> bool:
    """
    Write a frame to helm_memory via MemoryWriter. Returns True on success,
    False on failure. Caller handles helm_frames deletion after True.

    Failure modes:
      - MemoryWriteFailed / CircuitBreakerOpen with outbox configured: writer
        enqueues + returns success. We never see the exception here.
      - MemoryWriteFailed / CircuitBreakerOpen WITHOUT outbox: exception
        propagates here; we log + leave the frame in cold for retry.
      - Validation error (Pydantic): caller bug; log + leave the frame.
    """
    try:
        await writer.write_frame(
            project=project,
            agent=agent,
            content=content,
            full_content=full_content,
            session_date=session_date,
        )
        return True
    except Exception as e:
        logger.error(
            "Archivist: helm_memory write failed for frame=%s — frame left in cold queue. error=%s",
            frame_id,
            e,
        )
        return False
