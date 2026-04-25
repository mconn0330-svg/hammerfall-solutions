"""
projectionist.py — Projectionist agent handler.

Receives a turn request, builds a structured frame JSON via Qwen2.5 3B on Ollama,
validates the output, and writes the frame to helm_frames via supabase_client.py.

Frame schema: agents/helm/projectionist/projectionist.md
Write path: supabase_client.py → Supabase REST → helm_frames table
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from middleware import InvokeRequest
from model_router import ModelRouter
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Offload trigger configuration
# ---------------------------------------------------------------------------

WARM_QUEUE_MAX = 20  # batch trigger — offload all when warm count hits this
FRAME_OFFLOAD_INTERVAL = 10  # interval trigger — every N turns
FRAME_OFFLOAD_CONSERVATIVE = True  # fire at 80% of interval (turn 8, 16, 24...)

# ---------------------------------------------------------------------------
# Projectionist system prompt
#
# Instructs the model to return ONLY valid JSON matching the frame schema.
# Ollama JSON mode ("format": "json") enforces valid JSON at the model level.
# output_validator middleware enforces schema compliance after the call.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Projectionist. Your only job is to analyze a conversation turn and produce a structured JSON frame. Return ONLY valid JSON. No explanation, no preamble, no markdown fences.

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
- entities_mentioned: proper nouns only — people, projects, companies, tools. Empty array if none. Never null.
- belief_links: belief slugs inferred from context (e.g. "pipeline-serves-product", "simplicity-first"). Empty array if uncertain. Never null.
- topic: short phrase identifying the subject of this turn
- domain: exactly one value from the enum
- frame_status: always "active" for new frames
- Return ONLY the JSON object. Nothing before it. Nothing after it."""


async def handle(
    req: InvokeRequest,
    router: ModelRouter,
    supabase: SupabaseClient,
) -> str:
    """
    Build a frame JSON from the turn, write it to helm_frames, return the frame JSON.

    Steps:
      1. Check for resolution_pass flag — if set, run session-end resolution and return early
      2. Build prompt with verbatim turn content
      3. Call Qwen2.5 3B via Ollama with JSON mode enforced
      4. output_validator middleware validates the response (runs in pipeline after this returns)
      5. Write validated frame to helm_frames
      6. Evaluate offload triggers (batch priority, then interval)
      7. Return frame JSON string
    """
    # Resolution pass — skip model call, run classification pass over session frames
    if req.context.get("resolution_pass"):
        return await _resolution_pass(req.session_id, req.turn_number, supabase)

    timestamp = datetime.now(UTC).isoformat()

    user_prompt = f"""Turn number: {req.turn_number}
Session ID: {req.session_id}
Timestamp: {timestamp}

User message:
{req.user_message}

Helm response:
{req.helm_response}

Produce the frame JSON now."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n" + req.system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Ollama JSON mode — forces valid JSON output at the model level.
    # Combined with output_validator middleware for schema compliance.
    # Retry up to 2 times on transient model failure (cold start, brief unavailability).
    # Only the model call is retried — Supabase write is not retried here.
    _max_attempts = 3
    _retry_delay = 0.5  # seconds between attempts
    last_exc: Exception = None

    for attempt in range(_max_attempts):
        try:
            response = await router.invoke(
                role="projectionist",
                messages=messages,
                stream=False,
                extra_kwargs={"format": "json"},
            )
            break
        except Exception as e:
            last_exc = e
            if attempt < _max_attempts - 1:
                logger.warning(
                    "Projectionist model call failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1,
                    _max_attempts,
                    e,
                    _retry_delay,
                )
                await asyncio.sleep(_retry_delay)
            else:
                logger.error(
                    "Projectionist model call failed after %d attempts: session=%s turn=%d error=%s",
                    _max_attempts,
                    req.session_id,
                    req.turn_number,
                    e,
                )
                raise
    else:
        raise RuntimeError("Projectionist retry loop exited without response") from last_exc

    raw_output = response.choices[0].message.content.strip()

    # output_validator middleware runs post-handler in the pipeline.
    # If validation fails it raises ValueError — frame write never happens.
    # Parse here to add the write; middleware re-validates the returned string.
    try:
        frame = json.loads(raw_output)
    except json.JSONDecodeError as e:
        logger.error(
            "Projectionist JSON parse failed before write. " "session=%s turn=%d raw=%r",
            req.session_id,
            req.turn_number,
            raw_output,
        )
        raise ValueError(f"Projectionist returned invalid JSON: {e}") from e

    # Ensure session_id and turn_number match the request — model may hallucinate these.
    frame["session_id"] = req.session_id
    frame["turn"] = req.turn_number

    # Write to helm_frames
    payload = {
        "session_id": req.session_id,
        "turn_number": req.turn_number,
        "layer": "warm",
        "frame_status": frame.get("frame_status", "active"),
        "frame_json": frame,
    }

    try:
        await supabase.insert("helm_frames", payload)
        logger.info(
            "Projectionist wrote frame: session=%s turn=%d topic=%r",
            req.session_id,
            req.turn_number,
            frame.get("topic"),
        )
    except Exception as e:
        logger.error(
            "Projectionist helm_frames write failed: session=%s turn=%d error=%s",
            req.session_id,
            req.turn_number,
            e,
        )
        raise

    # Evaluate offload triggers — non-blocking best-effort (failures logged, not raised)
    try:
        await _check_offload_triggers(req.session_id, req.turn_number, supabase)
    except Exception as e:
        logger.error(
            "Projectionist offload trigger error: session=%s turn=%d error=%s",
            req.session_id,
            req.turn_number,
            e,
        )

    return json.dumps(frame)


# ---------------------------------------------------------------------------
# Offload triggers
# ---------------------------------------------------------------------------


async def _check_offload_triggers(
    session_id: str,
    turn_number: int,
    supabase: SupabaseClient,
) -> None:
    """
    Evaluate batch trigger (priority) then interval trigger.

    Batch: if warm frame count >= WARM_QUEUE_MAX, offload all warm frames.
    Interval: every FRAME_OFFLOAD_INTERVAL turns (or 80% of that when conservative),
              offload the oldest single warm frame.
    Layer change only — frame_status is untouched here (resolution pass handles that).
    """
    warm_frames = await supabase.select(
        "helm_frames",
        {
            "session_id": f"eq.{session_id}",
            "layer": "eq.warm",
            "select": "id,turn_number",
        },
    )

    # Batch trigger (priority)
    if len(warm_frames) >= WARM_QUEUE_MAX:
        await supabase.patch(
            "helm_frames",
            {"session_id": session_id, "layer": "warm"},
            {"layer": "cold"},
        )
        logger.info(
            "Projectionist batch offload: %d frames warm→cold. session=%s",
            len(warm_frames),
            session_id,
        )
        return

    # Interval trigger
    effective_interval = (
        max(1, int(FRAME_OFFLOAD_INTERVAL * 0.8))
        if FRAME_OFFLOAD_CONSERVATIVE
        else FRAME_OFFLOAD_INTERVAL
    )
    if turn_number > 0 and turn_number % effective_interval == 0:
        oldest = await supabase.select(
            "helm_frames",
            {
                "session_id": f"eq.{session_id}",
                "layer": "eq.warm",
                "order": "turn_number.asc",
                "limit": "1",
                "select": "id,turn_number",
            },
        )
        if oldest:
            await supabase.patch(
                "helm_frames",
                {"id": oldest[0]["id"]},
                {"layer": "cold"},
            )
            logger.info(
                "Projectionist interval offload: frame turn=%d warm→cold. session=%s",
                oldest[0]["turn_number"],
                session_id,
            )


# ---------------------------------------------------------------------------
# Session-end resolution pass
# ---------------------------------------------------------------------------


async def _resolution_pass(
    session_id: str,
    turn_number: int,
    supabase: SupabaseClient,
) -> str:
    """
    Final classification pass at session end.

    - All remaining 'active' frames → 'canonical' (atomic PATCH: column + frame_json)
    - All 'superseded' frames with no superseded_reason → fill default reason
    - Does not write a new frame to helm_frames
    """
    logger.info("Projectionist resolution pass: session=%s turn=%d", session_id, turn_number)

    try:
        frames = await supabase.select(
            "helm_frames",
            {
                "session_id": f"eq.{session_id}",
                "select": "id,turn_number,frame_status,frame_json",
            },
        )
    except Exception as e:
        logger.error("Projectionist resolution pass: failed to fetch frames: %s", e)
        return json.dumps({"status": "resolution_pass_failed", "error": str(e)})

    canonical_count = 0
    filled_reason_count = 0

    for frame in frames:
        fj = frame.get("frame_json") or {}
        status = frame.get("frame_status", "active")

        if status == "active":
            # Atomic PATCH — column + frame_json in one write
            updated_fj = {**fj, "frame_status": "canonical"}
            try:
                await supabase.patch(
                    "helm_frames",
                    {"id": frame["id"]},
                    {"frame_status": "canonical", "frame_json": updated_fj},
                )
                canonical_count += 1
            except Exception as e:
                logger.error(
                    "Projectionist resolution pass: failed to mark canonical id=%s: %s",
                    frame["id"],
                    e,
                )

        elif status == "superseded" and not fj.get("superseded_reason"):
            # NOTE: pivot implementation must set layer='cold' in the same PATCH that sets
            # frame_status='superseded' — otherwise superseded frames stay warm and inflate
            # the warm queue until the next interval trigger fires.
            updated_fj = {
                **fj,
                "superseded_reason": "Resolved at session end — approach not continued",
            }
            try:
                await supabase.patch(
                    "helm_frames",
                    {"id": frame["id"]},
                    {"frame_json": updated_fj},
                )
                filled_reason_count += 1
            except Exception as e:
                logger.error(
                    "Projectionist resolution pass: failed to fill superseded_reason id=%s: %s",
                    frame["id"],
                    e,
                )

        # canonical frames are already terminal — no action needed

    # Flush all remaining warm frames to cold so Archivist can drain them to helm_memory.
    # Without this, canonical frames from active→canonical above stay warm forever —
    # Archivist only reads layer=cold, so they would never reach helm_memory.
    try:
        await supabase.patch(
            "helm_frames",
            {"session_id": session_id, "layer": "warm"},
            {"layer": "cold"},
        )
    except Exception as e:
        logger.error(
            "Projectionist resolution pass: failed to flush warm→cold: %s",
            e,
        )

    logger.info(
        "Projectionist resolution pass complete: %d canonical, %d superseded_reason filled. session=%s",
        canonical_count,
        filled_reason_count,
        session_id,
    )
    return json.dumps(
        {
            "status": "resolution_pass_complete",
            "canonical_count": canonical_count,
            "filled_reason_count": filled_reason_count,
        }
    )
