"""
projectionist.py — Projectionist agent handler.

Receives a turn request, builds a structured frame JSON via Qwen2.5 3B on Ollama,
validates the output, and writes the frame to helm_frames via supabase_client.py.

Frame schema: agents/helm/projectionist/projectionist.md
Write path: supabase_client.py → Supabase REST → helm_frames table
"""

import json
import logging
from datetime import datetime, timezone

from middleware import InvokeRequest
from model_router import ModelRouter
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

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
      1. Build prompt with verbatim turn content
      2. Call Qwen2.5 3B via Ollama with JSON mode enforced
      3. output_validator middleware validates the response (runs in pipeline after this returns)
      4. Write validated frame to helm_frames
      5. Return frame JSON string
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    user_prompt = f"""Turn number: {req.turn_number}
Session ID: {req.session_id}
Timestamp: {timestamp}

User message:
{req.user_message}

Helm response:
{req.helm_response}

Produce the frame JSON now."""

    messages = [
        {"role": "system", "content": req.system_prompt + "\n" + SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    # Ollama JSON mode — forces valid JSON output at the model level.
    # Combined with output_validator middleware for schema compliance.
    response = await router.invoke(
        role="projectionist",
        messages=messages,
        stream=False,
        extra_kwargs={"format": "json"},
    )

    raw_output = response.choices[0].message.content.strip()

    # output_validator middleware runs post-handler in the pipeline.
    # If validation fails it raises ValueError — frame write never happens.
    # Parse here to add the write; middleware re-validates the returned string.
    try:
        frame = json.loads(raw_output)
    except json.JSONDecodeError as e:
        logger.error(
            "Projectionist JSON parse failed before write. "
            "session=%s turn=%d raw=%r",
            req.session_id, req.turn_number, raw_output,
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
            req.session_id, req.turn_number, frame.get("topic"),
        )
    except Exception as e:
        logger.error(
            "Projectionist helm_frames write failed: session=%s turn=%d error=%s",
            req.session_id, req.turn_number, e,
        )
        raise

    return json.dumps(frame)
