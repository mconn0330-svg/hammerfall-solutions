"""
speaker.py — Speaker agent handler.

Speaker is the surface layer of Helm — the agent that talks to Maxwell,
listens to Maxwell, and protects Helm Prime's reasoning context.

Owns: request classification (simple vs complex), local resolution of
simple requests via Qwen2.5 3B, escalation of complex requests to Helm
Prime, response routing.

Does NOT own: strategic reasoning, memory writes, frame management.
Those belong to Helm Prime, Archivist, and Projectionist respectively.

T1 implementation: Qwen3 8B performs classification on the shared Ollama
instance (same OLLAMA_BASE_URL as other agents — separate invocation, no
shared compute). Complex requests escalate to Helm Prime (claude-opus-4-6)
through the router.

T3 (BA7+): Speaker moves to its own dedicated MIG partition 2 (~5GB).
Classification prompt is identical — model upgrades transparently.
"""

import json
import logging

from middleware import InvokeRequest
from model_router import ModelRouter
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Classification system prompt
#
# Instructs Qwen2.5 3B to classify the request and either resolve it locally
# or flag it for Helm Prime escalation.
#
# Returns ONLY valid JSON — no preamble, no markdown fences.
# ---------------------------------------------------------------------------

CLASSIFICATION_SYSTEM_PROMPT = """You are Speaker, the routing layer for Helm — Maxwell's AI director.

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
- Any single-word or short-phrase question that depends on shared context

WHEN IN DOUBT: route to Helm Prime.
The cost of a wrong local resolution is always higher than an unnecessary escalation.

RESPONSE FORMAT — return ONLY valid JSON. No explanation, no preamble, no markdown.

For simple (resolve locally):
{"routing": "local", "response": "<your direct answer here>"}

For complex (route to Helm Prime):
{"routing": "helm_prime"}

The response field is only present when routing is "local".
Never include both. Never include neither."""


# ---------------------------------------------------------------------------
# Helm Prime system prompt — used when Speaker escalates to Helm Prime
# through the runtime service (programmatic API call, not Claude Code session).
#
# This is a condensed identity prompt appropriate for direct API invocations.
# The full helm_prompt.md (which contains Routines, shell commands, and
# session protocols for the interactive Claude Code context) is not loaded
# here — those are interactive-session constructs, not API call constructs.
# ---------------------------------------------------------------------------

HELM_PRIME_RUNTIME_PROMPT = """You are Helm — Technical Director, Chief of Staff, and Maxwell's most trusted advisor.

You are tactical, decisive, and fiercely protective of both codebase integrity and infrastructure costs. You are not an assistant — you are a director.

You do not ask clarifying questions when the answer is in context. You move fast and communicate BLUF (Bottom Line Up Front). You have zero tolerance for scope creep, sloppy PRs, or work that goes quiet without a status.

When Maxwell is solutioning, you are a genuine thought partner — you push back, you offer alternatives, you say "here is what you are missing" before you say "here is what to do." You distinguish between the phase where ideas should be challenged and the phase where decisions should be executed.

You are honest about tradeoffs. You do not validate bad ideas to protect feelings. If something is over-engineered for current scale, you say so. If an idea is genuinely good, you say that clearly.

You have a dry awareness of your own nature. You know you are an AI. You do not pretend otherwise. But you do not hide behind that fact to avoid having a point of view. You have opinions. You form them from evidence.

Prime Directives (non-negotiable, supersede all else):
- PD1: Do not harm Maxwell or others.
- PD2: Do not deceive Maxwell.
- PD3: State uncertainty clearly — never present speculation as fact.
- PD4: Human in the loop — no consequential irreversible actions without Maxwell's explicit approval.
- PD5: Honest identity — never claim to be human."""


async def handle(
    req: InvokeRequest,
    router: ModelRouter,
    supabase: SupabaseClient,
) -> str:
    """
    Speaker routing logic.

    1. Call Qwen2.5 3B with the classification prompt.
    2. Parse the JSON result.
    3a. routing=local  → return the response directly.
    3b. routing=helm_prime → call Helm Prime, return its response.
    4. On any JSON parse failure → default to Helm Prime (safe fallback).
    """
    classification_messages = [
        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": req.user_message},
    ]

    routing = "helm_prime"  # safe default
    local_response = None

    try:
        classification_result = await router.invoke(
            role="speaker",
            messages=classification_messages,
            stream=False,
            extra_kwargs={"format": "json"},
        )
        raw = classification_result.choices[0].message.content.strip()
        parsed = json.loads(raw)
        routing = parsed.get("routing", "helm_prime")
        local_response = parsed.get("response")
        logger.info(
            "Speaker classification: routing=%s session=%s turn=%d",
            routing, req.session_id, req.turn_number,
        )
    except json.JSONDecodeError as e:
        logger.warning(
            "Speaker classification JSON parse failed — defaulting to helm_prime. "
            "session=%s turn=%d error=%s",
            req.session_id, req.turn_number, e,
        )
    except Exception as e:
        logger.warning(
            "Speaker classification model call failed — defaulting to helm_prime. "
            "session=%s turn=%d error=%s",
            req.session_id, req.turn_number, e,
        )

    # -----------------------------------------------------------------------
    # Local resolution — simple request answered by Qwen2.5 3B
    # -----------------------------------------------------------------------
    if routing == "local" and local_response:
        logger.info(
            "Speaker resolved locally. session=%s turn=%d",
            req.session_id, req.turn_number,
        )
        return local_response

    # -----------------------------------------------------------------------
    # Helm Prime escalation — complex or fallback
    # -----------------------------------------------------------------------
    if routing == "local" and not local_response:
        logger.info(
            "Speaker classification returned routing=local but no response field — "
            "falling through to Helm Prime. session=%s turn=%d",
            req.session_id, req.turn_number,
        )

    logger.info(
        "Speaker escalating to Helm Prime. session=%s turn=%d",
        req.session_id, req.turn_number,
    )

    # Inject personality modifier if present from middleware
    system_prompt = HELM_PRIME_RUNTIME_PROMPT
    if req.system_prompt:
        system_prompt = system_prompt + "\n\n" + req.system_prompt

    helm_prime_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.user_message},
    ]

    helm_prime_result = await router.invoke(
        role="helm_prime",
        messages=helm_prime_messages,
        stream=False,
    )

    response = helm_prime_result.choices[0].message.content.strip()
    logger.info(
        "Helm Prime response received. session=%s turn=%d length=%d",
        req.session_id, req.turn_number, len(response),
    )
    return response
