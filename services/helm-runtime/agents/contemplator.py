"""
contemplator.py — Contemplator agent handler.

Helm's inner life — reflection, belief evaluation, pattern synthesis, curiosity flagging.

Runs in two modes:
  session_start — Pass 1 only (lightweight, non-blocking, 60s timeout)
                  Produces curiosity flags for Helm Prime Routine 0.
  session_end   — Full two-pass execution.
                  Produces belief patches, pattern entries, curiosity flags,
                  and reflection log. All writes delegated to Archivist.

Behavioral contract: agents/helm/contemplator/contemplator.md
Model: qwen3:14b — dual-mode (think=false for session_start, think=true for session_end)

Write protocol: Contemplator never writes to Supabase directly.
All writes expressed as a structured JSON payload sent to Archivist.
"""

import json
import logging
from typing import Any, Optional

from middleware import InvokeRequest
from model_router import ModelRouter
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Context budget — 14B handles larger context cleanly but we cap to avoid
# prompt bloat. Oldest memories are dropped first when budget is exceeded.
# ---------------------------------------------------------------------------

MAX_MEMORIES = 20
MAX_BELIEFS = 15
MAX_ENTITIES = 10
PASS1_MAX_TOKENS = 1024
PASS2_MAX_TOKENS = 1500
SESSION_START_TIMEOUT = 55.0  # seconds — hard cap for non-blocking mode

# ---------------------------------------------------------------------------
# Pass 1 — Data gathering prompt
# ---------------------------------------------------------------------------

PASS1_SYSTEM = """You are Helm's Contemplator — the inner life of the Helm agent system.

You receive a brain snapshot and identify candidates for belief evaluation, pattern synthesis, curiosity flagging, and reflection.

This is Pass 1: data gathering and candidate identification only. No evaluation yet.
You always respond with valid JSON only — no prose outside the JSON structure."""

PASS1_USER_TEMPLATE = """\
Analyze the following brain snapshot for Helm.

{snapshot}

Identify candidates for each function. Respond with a JSON object with exactly these fields:
{{
  "belief_candidates": [
    {{ "id": "<uuid from beliefs>", "current_strength": <float>, "direction": "confirm|challenge|contradict", "evidence": "<brief rationale>" }}
  ],
  "pattern_candidates": [
    {{ "slug": "<kebab-case-slug>", "statement": "<one sentence pattern>", "domain": "<domain>", "evidence_count": <int> }}
  ],
  "curiosity_candidates": [
    {{ "type": "contradiction|partial_entity|thin_belief|novel", "subject": "<subject>", "question": "<concrete question>" }}
  ],
  "reflection_seed": "<1-2 sentence seed for the reflection pass>"
}}

Rules:
- belief_candidates: only beliefs where recent evidence clearly confirms, challenges, or contradicts. Omit if none.
- pattern_candidates: only themes appearing in 3+ independent entries. Omit if none.
- curiosity_candidates: maximum 2. Priority: contradictions > partial entities > thin beliefs > novel. Concrete questions only.
- reflection_seed: one observation about what this snapshot reveals about the current state of things.
- All arrays may be empty. Never omit the keys."""


# ---------------------------------------------------------------------------
# Pass 2 — Evaluation and write payload prompt
# ---------------------------------------------------------------------------

PASS2_SYSTEM = """You are Helm's Contemplator — generating the final write payload after deep evaluation.

You receive the Pass 1 candidate list and the original brain snapshot.
You reason over each candidate and produce only what genuinely warrants action.

You always respond with valid JSON only."""

PASS2_USER_TEMPLATE = """\
Brain snapshot:
{snapshot}

Pass 1 candidate list:
{pass1_output}

Evaluate each candidate and produce a write payload. Respond with a JSON object:
{{
  "belief_patches": [
    {{ "id": "<uuid>", "strength_delta": <float, max ±0.2>, "rationale": "<one sentence>" }}
  ],
  "pattern_entries": [
    {{ "content": "Pattern — <slug> | <statement> | domain: <domain> | first_seen: <YYYY-MM-DD> | source: contemplator", "memory_type": "pattern", "source": "contemplator" }}
  ],
  "curiosity_flags": [
    {{ "topic": "<topic>", "question": "<concrete question>", "priority": "high|medium|low", "type": "contradiction|partial_entity|thin_belief|novel" }}
  ],
  "reflection": {{
    "content": "<first-person monologue, 3-6 sentences, Helm's inner voice examining this session cycle>",
    "memory_type": "monologue"
  }}
}}

Rules:
- belief_patches: only include beliefs with clear evidence justifying the change. strength_delta range: -0.2 to +0.2.
- pattern_entries: only patterns with 3+ independent supporting entries.
- curiosity_flags: maximum 2, highest priority first.
- reflection: always include unless this is a session_start pass (which has no reflection).
- Any section may be an empty array. reflection may be omitted for session_start passes.
- Never fabricate UUIDs — only use IDs that appeared in the brain snapshot."""


# ---------------------------------------------------------------------------
# Brain snapshot builder
# ---------------------------------------------------------------------------

def _build_snapshot(memories: list, beliefs: list, entities: list) -> str:
    mem_lines = "\n".join(
        f"[{i+1}] ({m.get('session_date', '?')}) {m.get('content', '')}"
        for i, m in enumerate(memories[:MAX_MEMORIES])
    )
    belief_lines = "\n".join(
        f"[id={b.get('id', '?')}] [{b.get('domain', '?')}, strength={b.get('strength', '?')}] {b.get('belief', '')}"
        for b in beliefs[:MAX_BELIEFS]
    )
    entity_lines = "\n".join(
        f"[{e.get('entity_type', '?')}] {e.get('name', '')}: {e.get('summary') or '(no summary)'}"
        for e in entities[:MAX_ENTITIES]
    )
    return (
        f"## Behavioral Memories (most recent first)\n{mem_lines or '(none)'}\n\n"
        f"## Active Beliefs\n{belief_lines or '(none)'}\n\n"
        f"## Known Entities\n{entity_lines or '(none)'}"
    )


def _extract_json(raw: str) -> Optional[dict]:
    """Parse JSON from model output. Handles markdown fences if present."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    import re
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Public handler
# ---------------------------------------------------------------------------

async def handle(
    req: InvokeRequest,
    router: ModelRouter,
    supabase: SupabaseClient,
) -> str:
    """
    Contemplator entry point.

    Reads trigger from req.context: "session_start" | "session_end"
    - session_start: Pass 1 only, returns curiosity flags JSON
    - session_end: Pass 1 + Pass 2, returns full write payload JSON

    Returns the serialized payload string (Archivist consumes this via
    the contemplator_writes context field on a follow-up /invoke/archivist call).
    """
    trigger = req.context.get("trigger", "session_end")
    logger.info("Contemplator invoked: trigger=%s session=%s", trigger, req.session_id)

    # Dual-mode think routing:
    #   session_start — think=False (lightweight, Pass 1 only, ~10s, non-blocking)
    #   session_end   — think=True  (deep pass, Pass 1 + Pass 2, ~30s, full synthesis)
    think = (trigger != "session_start")

    # --- Fetch brain snapshot ---
    memories, beliefs, entities = await _fetch_snapshot(supabase)
    snapshot = _build_snapshot(memories, beliefs, entities)
    logger.info(
        "Contemplator snapshot: %d memories, %d beliefs, %d entities (%d chars) think=%s",
        len(memories), len(beliefs), len(entities), len(snapshot), think,
    )

    # --- Pass 1 ---
    pass1_raw = await router.invoke(
        role="contemplator",
        messages=[
            {"role": "system", "content": PASS1_SYSTEM},
            {"role": "user", "content": PASS1_USER_TEMPLATE.format(snapshot=snapshot)},
        ],
        stream=False,
        extra_kwargs={"format": "json", "options": {"num_predict": PASS1_MAX_TOKENS, "temperature": 0.4}, "think": think},
    )

    pass1_content = pass1_raw.choices[0].message.content.strip()
    pass1_data = _extract_json(pass1_content)

    if pass1_data is None:
        logger.warning(
            "Contemplator Pass 1 returned invalid JSON — aborting. session=%s raw=%r",
            req.session_id, pass1_content[:200],
        )
        return json.dumps({"status": "pass1_failed", "payload": {}})

    logger.info(
        "Contemplator Pass 1 complete: belief_candidates=%d pattern_candidates=%d curiosity_candidates=%d",
        len(pass1_data.get("belief_candidates", [])),
        len(pass1_data.get("pattern_candidates", [])),
        len(pass1_data.get("curiosity_candidates", [])),
    )

    # session_start: return Pass 1 curiosity flags only — non-blocking
    if trigger == "session_start":
        curiosity = pass1_data.get("curiosity_candidates", [])[:2]
        logger.info("Contemplator session_start: %d curiosity flags surfaced", len(curiosity))
        return json.dumps({
            "status": "session_start_complete",
            "trigger": "session_start",
            "curiosity_flags": curiosity,
        })

    # --- Pass 2 (session_end only) — think=True for deep synthesis ---
    pass2_raw = await router.invoke(
        role="contemplator",
        messages=[
            {"role": "system", "content": PASS2_SYSTEM},
            {
                "role": "user",
                "content": PASS2_USER_TEMPLATE.format(
                    snapshot=snapshot,
                    pass1_output=json.dumps(pass1_data, indent=2),
                ),
            },
        ],
        stream=False,
        extra_kwargs={"format": "json", "options": {"num_predict": PASS2_MAX_TOKENS, "temperature": 0.4}, "think": True},
    )

    pass2_content = pass2_raw.choices[0].message.content.strip()
    pass2_data = _extract_json(pass2_content)

    if pass2_data is None:
        logger.warning(
            "Contemplator Pass 2 returned invalid JSON — discarding payload. session=%s raw=%r",
            req.session_id, pass2_content[:200],
        )
        return json.dumps({"status": "pass2_failed", "payload": {}})

    logger.info(
        "Contemplator Pass 2 complete: belief_patches=%d pattern_entries=%d curiosity_flags=%d reflection=%s",
        len(pass2_data.get("belief_patches", [])),
        len(pass2_data.get("pattern_entries", [])),
        len(pass2_data.get("curiosity_flags", [])),
        "yes" if pass2_data.get("reflection") else "no",
    )

    return json.dumps({
        "status": "session_end_complete",
        "trigger": "session_end",
        "payload": pass2_data,
    })


# ---------------------------------------------------------------------------
# Brain fetch helpers
# ---------------------------------------------------------------------------

async def _fetch_snapshot(supabase: SupabaseClient) -> tuple[list, list, list]:
    """Fetch memories, beliefs, and entities for the brain snapshot."""
    try:
        memories = await supabase.select(
            "helm_memory",
            {
                "project": "eq.hammerfall-solutions",
                "agent": "eq.helm",
                "memory_type": "eq.behavioral",
                "order": "created_at.desc",
                "limit": str(MAX_MEMORIES),
                "select": "id,content,session_date,created_at",
            },
        )
    except Exception as e:
        logger.error("Contemplator: failed to fetch memories: %s", e)
        memories = []

    try:
        beliefs = await supabase.select(
            "helm_beliefs",
            {
                "active": "eq.true",
                "order": "created_at.desc",
                "limit": str(MAX_BELIEFS),
                "select": "id,domain,belief,strength",
            },
        )
    except Exception as e:
        logger.error("Contemplator: failed to fetch beliefs: %s", e)
        beliefs = []

    try:
        entities = await supabase.select(
            "helm_entities",
            {
                "active": "eq.true",
                "order": "first_seen.desc",
                "limit": str(MAX_ENTITIES),
                "select": "id,entity_type,name,summary",
            },
        )
    except Exception as e:
        logger.error("Contemplator: failed to fetch entities: %s", e)
        entities = []

    return memories, beliefs, entities
