"""
helm_prime.py — Helm Prime agent handler.

Helm Prime is the conscious reasoning subsystem of Helm — the surface the user
talks to. This handler is the runtime entry point for Prime invocation.

Responsibilities:
  1. Load helm_personality scores from Supabase and format as an injection block
  2. Assemble the system prompt (helm_prompt.md + personality block + operational context)
  3. Invoke the configured Prime model via model_router
  4. Return the response string

Does NOT own: memory writes (Prime writes via brain.sh during its own operation,
not through this handler), frame management (Projectionist), belief graduation
(Contemplator → Archivist handoff).

Model configuration lives in config.yaml under agents.helm_prime. Provider-agnostic
by design — swap provider/model via config without touching this code.
"""

import logging
from pathlib import Path

from middleware import InvokeRequest
from model_router import ModelRouter
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# helm_prompt.md is mounted into the container at /app/agents/helm/helm_prompt.md
# via docker-compose volume. Edit the host file and restart the service to pick
# up changes — no image rebuild required. This file is the canonical source.
# Long-term the prompt moves to Supabase alongside helm_personality; mounting
# preserves edit-and-restart UX in the meantime.
PROMPT_PATH = Path(__file__).resolve().parent.parent / "agents" / "helm" / "helm_prompt.md"


async def handle(
    req: InvokeRequest,
    router: ModelRouter,
    supabase: SupabaseClient,
) -> str:
    """
    Helm Prime invocation.

    1. Load helm_prompt.md as the base system prompt
    2. Load personality scores from Supabase, format as injection block
    3. Assemble system prompt: base + personality + operational context
    4. Invoke helm_prime via model_router with user message
    5. Return response
    """
    base_prompt = _load_base_prompt()
    personality_block = await _load_personality_block(supabase)
    operational_context = _build_operational_context(req)

    system_prompt = _assemble_system_prompt(
        base_prompt=base_prompt,
        personality_block=personality_block,
        operational_context=operational_context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.user_message},
    ]

    result = await router.invoke(
        role="helm_prime",
        messages=messages,
        stream=False,
    )

    response = result.choices[0].message.content.strip()
    logger.info(
        "Helm Prime response received. session=%s turn=%d length=%d",
        req.session_id,
        req.turn_number,
        len(response),
    )
    return response


def _load_base_prompt() -> str:
    """Load helm_prompt.md as the base system prompt. Fatal if missing — Prime cannot operate without its prompt."""
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise RuntimeError(
            f"helm_prompt.md not found at {PROMPT_PATH}. "
            "Confirm the docker-compose volume mount is in place."
        ) from e


async def _load_personality_block(supabase: SupabaseClient) -> str:
    """
    Load helm_personality scores from Supabase and format as a calibration block.

    Non-fatal: returns empty string on any failure so Prime still operates with
    base identity if scores are unavailable.
    """
    try:
        rows = await supabase.select(
            "helm_personality",
            {"order": "attribute.asc", "select": "attribute,score,description"},
        )
        if not rows:
            return ""
        lines = ["[PERSONALITY CALIBRATION — active operating parameters for this session]"]
        for r in rows:
            attr = r.get("attribute", "?")
            score = r.get("score", "?")
            desc = r.get("description", "")
            lines.append(f"{attr}: {score} — {desc}")
        return "\n".join(lines)
    except Exception as e:
        logger.warning("helm_prime: failed to load personality scores — %s", e)
        return ""


def _build_operational_context(req: InvokeRequest) -> str:
    """
    Build operational context — surface, tier, session metadata.

    T1 surface defaults to desktop_ui. Stage 2+ expands the surface set
    (mobile, ambient hardware); surface is read from req.context when supplied.
    """
    surface = req.context.get("surface", "desktop_ui") if req.context else "desktop_ui"
    return (
        "[OPERATIONAL CONTEXT]\n"
        f"surface: {surface}\n"
        "tier: T1 (on-demand)\n"
        f"session_id: {req.session_id}\n"
        f"turn_number: {req.turn_number}"
    )


def _assemble_system_prompt(
    base_prompt: str,
    personality_block: str,
    operational_context: str,
) -> str:
    """Combine base prompt, personality calibration, and operational context."""
    parts = [base_prompt]
    if personality_block:
        parts.append(personality_block)
    if operational_context:
        parts.append(operational_context)
    return "\n\n---\n\n".join(parts)
