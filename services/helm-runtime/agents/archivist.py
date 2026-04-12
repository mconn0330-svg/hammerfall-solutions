"""
archivist.py — Archivist agent handler.

Reads cold frames from helm_frames, generates a 1-3 sentence summary per frame
via Qwen2.5 3B on Ollama, writes to helm_memory at full fidelity via
supabase_client.py, then deletes the helm_frames row.

The model's only job is summary generation. Frame structure, field values, and
frame_status all come from the cold frame itself — the model does not infer these.

Write path: supabase_client.py → Supabase REST → helm_memory table
Safety net: frame stays in helm_frames (layer='cold') on any write failure —
            retried on next Archivist invocation. Nothing is lost.

frame_status source of truth: the helm_frames column (authoritative per BA6
Projectionist contract). The column value is written into full_content JSONB.
"""

import asyncio
import logging

from middleware import InvokeRequest
from model_router import ModelRouter
from supabase_client import SupabaseClient, SupabaseError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Summary prompt
#
# The model's only task: compress a turn into 1-3 sentences.
# No JSON output required — plain prose only.
# ---------------------------------------------------------------------------

SUMMARY_SYSTEM_PROMPT = """You are summarizing a conversation turn for long-term memory storage. Your job is to produce a concise 1-3 sentence summary of what this turn covered.

Be specific. Name the topic, the decision made or question explored, and the outcome if one was reached. Write in past tense. No preamble. Return only the summary text."""


async def handle(
    req: InvokeRequest,
    router: ModelRouter,
    supabase: SupabaseClient,
) -> str:
    """
    Migrate all cold frames for the current session from helm_frames to helm_memory.

    For each cold frame:
      1. Generate a 1-3 sentence summary via the model
      2. Write to helm_memory at full fidelity (summary in content, full frame in full_content)
      3. Delete the helm_frames row only after confirmed write
      4. On write failure: leave frame in helm_frames, log, continue to next frame

    Returns a summary of what was migrated.
    """
    # Query all cold frames — not scoped to session, Archivist clears the full cold queue
    cold_frames = await supabase.select(
        "helm_frames",
        {"layer": "eq.cold", "select": "*", "order": "created_at.asc"},
    )

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
        )
        if summary is None:
            # All retries exhausted — leave frame in cold, continue
            failed += 1
            continue

        # Build full_content — verbatim frame_json with frame_status from the column
        full_content = dict(frame_json)
        full_content["frame_status"] = frame_status  # column is authoritative

        # Write to helm_memory at full fidelity
        payload = {
            "project": req.context.get("project", "hammerfall-solutions"),
            "agent": req.context.get("agent", "helm"),
            "memory_type": "frame",
            "content": summary,
            "sync_ready": False,
            "full_content": full_content,
        }

        write_ok = await _write_to_memory(supabase, payload, frame_id)
        if not write_ok:
            # Write failed — frame stays in cold, retried next invocation
            failed += 1
            continue

        # Delete helm_frames row only after confirmed write
        try:
            await supabase.delete("helm_frames", {"id": frame_id})
            logger.info(
                "Archivist migrated frame: id=%s status=%s topic=%r",
                frame_id, frame_status, frame_json.get("topic"),
            )
            migrated += 1
        except Exception as e:
            logger.error(
                "Archivist: helm_frames delete failed for id=%s — frame may be duplicated "
                "in helm_memory on next run. error=%s", frame_id, e,
            )
            # Do not count as failed — the memory write succeeded.
            # The duplicate-on-retry risk is acceptable; helm_memory has no unique constraint
            # on frame content. Log clearly so it can be investigated.
            migrated += 1

    result = f"Archivist migration complete: {migrated} migrated, {failed} failed (left in cold queue)."
    logger.info(result)
    return result


async def _generate_summary(
    router: ModelRouter,
    user_msg: str,
    helm_msg: str,
    frame_id: str,
) -> str | None:
    """
    Generate a 1-3 sentence summary of a turn via the model.
    Retries up to 3 attempts with 0.5s backoff on transient model failure.
    Returns the summary string, or None if all attempts fail.
    """
    user_prompt = f"""User message:
{user_msg}

Helm response:
{helm_msg}

Summarize this turn in 1-3 sentences."""

    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
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
            summary = response.choices[0].message.content.strip()
            if not summary:
                raise ValueError("Model returned empty summary")
            return summary
        except Exception as e:
            if attempt < _max_attempts - 1:
                logger.warning(
                    "Archivist summary generation failed (attempt %d/%d) for frame=%s: %s — retrying in %.1fs",
                    attempt + 1, _max_attempts, frame_id, e, _retry_delay,
                )
                await asyncio.sleep(_retry_delay)
            else:
                logger.error(
                    "Archivist summary generation failed after %d attempts for frame=%s: %s — "
                    "frame left in cold queue for retry.",
                    _max_attempts, frame_id, e,
                )
                return None


async def _write_to_memory(
    supabase: SupabaseClient,
    payload: dict,
    frame_id: str,
) -> bool:
    """
    Write a frame to helm_memory. Returns True on success, False on failure.
    Does NOT delete the helm_frames row — caller handles deletion after this returns True.
    """
    try:
        await supabase.insert("helm_memory", payload)
        return True
    except SupabaseError as e:
        logger.error(
            "Archivist: helm_memory write failed for frame=%s — frame left in cold queue. error=%s",
            frame_id, e,
        )
        return False
    except Exception as e:
        logger.error(
            "Archivist: unexpected error writing helm_memory for frame=%s — frame left in cold queue. error=%s",
            frame_id, e,
        )
        return False
