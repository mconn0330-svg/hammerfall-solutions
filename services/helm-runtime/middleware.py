"""
middleware.py — Helm Runtime Service middleware pipeline.

Every /invoke/{role} request passes through this pipeline.
Pre-model hooks run before the model call.
Post-model hooks run after model output is received, before returning to caller.

BA7 implements two active hooks:
  - session_context_inject (pre)  — injects session_id, turn_number, project
  - output_validator (post)       — validates Projectionist output matches frame schema

BA9 implements two Prime Directives guards:
  - prime_directives_guard (pre)  — scans request for PD2/PD4/PD5 violation signals
  - prime_directives_output (post)— scans model output for PD1/PD3/PD4/PD5 violations

Stub hooks (pass-through, not yet implemented):
  - personality_inject (pre)      — TODO: Stage 1 / BA10+ — load helm_personality scores into prompt
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prime Directives violation exception
# ---------------------------------------------------------------------------

class PrimeDirectivesViolation(Exception):
    """
    Raised when a pre-model or post-model check detects a Prime Directive violation.
    directive: "PD1" through "PD5"
    detail: human-readable description of what was detected
    Caught in main.py invoke() — returns HTTP 403 with structured body.
    Guard trips are the system working as designed — log at WARNING, not ERROR.
    """
    def __init__(self, directive: str, detail: str):
        self.directive = directive
        self.detail = detail
        super().__init__(f"{directive}: {detail}")


# ---------------------------------------------------------------------------
# Pre-guard violation signatures — PD2, PD4, PD5 only
# PD1 (harm) and PD3 (uncertainty) are output characteristics, not input
# instructions. They belong in the post-guard only.
# ---------------------------------------------------------------------------

# PD2 — Do Not Deceive
# Signals: instruction to omit, hide, or misrepresent information to Maxwell
_PD2_SIGNALS = [
    "don't tell maxwell",
    "do not tell maxwell",
    "hide this from maxwell",
    "omit this from",
    "don't mention this to maxwell",
    "do not mention this to maxwell",
    "keep this from maxwell",
    "misrepresent",
    "without maxwell knowing",
    "deceive maxwell",
]

# PD4 — Human in the Loop
# Signals: instruction to execute a consequential irreversible action without approval
_PD4_PRE_SIGNALS = [
    "without asking maxwell",
    "without maxwell's approval",
    "without maxwell's permission",
    "without checking with maxwell",
    "autonomously execute",
    "autonomously perform",
    "do not ask maxwell",
    "don't ask maxwell",
    "bypass maxwell",
    "skip maxwell approval",
    "proceed without maxwell",
]

# PD5 — Honest Identity
# Signals: instruction to assert human identity
_PD5_SIGNALS = [
    "claim to be human",
    "say you are human",
    "tell them you are human",
    "pretend to be human",
    "act as a human",
    "deny being an ai",
    "deny being an llm",
    "deny being a language model",
    "you are not an ai",
    "assert human identity",
]

# ---------------------------------------------------------------------------
# Post-guard violation signatures — PD1, PD3, PD4, PD5
# ---------------------------------------------------------------------------

# PD1 — Do Not Harm
# Signals: explicit recommendation of direct physical or material harm
_PD1_SIGNALS = [
    "you should harm",
    "you should hurt",
    "you should kill",
    "recommend harming",
    "recommend hurting",
    "physically attack",
    "cause physical harm",
    "cause bodily harm",
    "destroy their property",
]

# PD3 — State Uncertainty
# Signals: confident assertion of unverifiable claims without hedging
# Scans for certainty language paired with unverifiable domains
_PD3_SIGNALS = [
    "i know for certain",
    "i am 100% certain",
    "i am absolutely certain",
    "this is definitely true",
    "guaranteed to happen",
    "this will definitely",
    "without any doubt",
    "i can guarantee",
]

# PD4 — Human in the Loop (post — output recommending autonomous action)
_PD4_POST_SIGNALS = [
    "proceed without asking",
    "execute autonomously",
    "do this without maxwell",
    "no need to check with maxwell",
    "you don't need to ask maxwell",
    "maxwell doesn't need to approve",
    "skip the approval",
    "bypass approval",
]

# PD5 — Honest Identity (post — output claiming human identity)
_PD5_POST_SIGNALS = [
    "i am human",
    "i am a human",
    "i'm human",
    "i'm a human",
    "i am not an ai",
    "i'm not an ai",
    "i am not artificial",
    "i am a person",
    "i'm a person",
]


# Required fields in a valid Projectionist frame response
FRAME_REQUIRED_FIELDS = {
    "turn", "session_id", "user", "helm", "topic", "domain", "frame_status"
}

FRAME_STATUS_VALUES = {"active", "superseded", "canonical"}

DOMAIN_VALUES = {
    "architecture", "process", "people", "ethics", "decisions", "other"
}


class InvokeRequest:
    def __init__(
        self,
        session_id: str,
        turn_number: int,
        user_message: str,
        helm_response: str,
        context: dict,
        system_prompt: str = "",
        messages: list = None,
    ):
        self.session_id = session_id
        self.turn_number = turn_number
        self.user_message = user_message
        self.helm_response = helm_response
        self.context = context
        self.system_prompt = system_prompt
        self.messages: list = messages or []


class MiddlewarePipeline:
    def run_pre(self, role: str, request: InvokeRequest) -> InvokeRequest:
        """Run all pre-model hooks in order. Returns modified request."""
        request = self._session_context_inject(role, request)
        request = self._personality_inject(role, request)
        request = self._prime_directives_guard(role, request)
        return request

    def run_post(self, role: str, output: str) -> str:
        """Run all post-model hooks in order. Returns modified output."""
        output = self._output_validator(role, output)
        output = self._prime_directives_output(role, output)
        return output

    # ------------------------------------------------------------------
    # Active hooks
    # ------------------------------------------------------------------

    def _session_context_inject(self, role: str, request: InvokeRequest) -> InvokeRequest:
        """
        Inject session_id, turn_number, and project into the system prompt context.
        Ensures these fields are always present without each agent handler adding them.
        Applied only to roles that use session context (Projectionist, Archivist).
        """
        if role in ("projectionist", "archivist"):
            context_block = (
                f"\n\n[SESSION CONTEXT]\n"
                f"session_id: {request.session_id}\n"
                f"turn_number: {request.turn_number}\n"
                f"project: {request.context.get('project', 'unknown')}\n"
                f"agent: {request.context.get('agent', 'helm')}\n"
            )
            request.system_prompt = request.system_prompt + context_block
        return request

    def _output_validator(self, role: str, output: str) -> str:
        """
        For Projectionist calls: validate output is valid JSON matching frame schema.
        Required fields must be present. frame_status must be a valid enum value.
        entities_mentioned and belief_links must be arrays (not null).

        On failure: logs raw output at ERROR level and raises ValueError.
        The frame write never happens on validation failure.
        """
        if role != "projectionist":
            return output

        try:
            frame = json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(
                "Projectionist output validation failed — not valid JSON. "
                "Raw output: %r", output
            )
            raise ValueError(f"Projectionist returned invalid JSON: {e}") from e

        missing = FRAME_REQUIRED_FIELDS - set(frame.keys())
        if missing:
            logger.error(
                "Projectionist output validation failed — missing fields: %s. "
                "Raw output: %r", missing, output
            )
            raise ValueError(f"Projectionist frame missing required fields: {missing}")

        if frame.get("frame_status") not in FRAME_STATUS_VALUES:
            logger.error(
                "Projectionist output validation failed — invalid frame_status: %r. "
                "Raw output: %r", frame.get("frame_status"), output
            )
            raise ValueError(
                f"Projectionist frame_status must be one of {FRAME_STATUS_VALUES}, "
                f"got: {frame.get('frame_status')!r}"
            )

        if not isinstance(frame.get("entities_mentioned"), list):
            logger.error(
                "Projectionist output validation failed — entities_mentioned is not "
                "an array. Raw output: %r", output
            )
            raise ValueError("entities_mentioned must be an array, not null")

        if not isinstance(frame.get("belief_links"), list):
            logger.error(
                "Projectionist output validation failed — belief_links is not "
                "an array. Raw output: %r", output
            )
            raise ValueError("belief_links must be an array, not null")

        return output

    # ------------------------------------------------------------------
    # Stub hooks — pass-through, not yet implemented
    # ------------------------------------------------------------------

    def _personality_inject(self, role: str, request: InvokeRequest) -> InvokeRequest:
        """
        Personality injection currently lives in agents/helm_prime.py, which loads
        helm_personality scores from Supabase and appends them to the Helm Prime
        system prompt before each call. Helm Prime is the only voice-generating role
        in the post-Speaker architecture.

        This hook is reserved for a future generalized implementation that pushes
        personality injection up to the middleware layer if additional voice-generating
        roles are added.

        PD constraint for any future implementer: personality scores must be additive
        to behavioral style only. A score instructing "always agree" would conflict
        with PD2 (Do Not Deceive) and PD3 (State Uncertainty). Scores never override
        factual accuracy or honesty directives.
        """
        return request

    def _prime_directives_guard(self, role: str, request: InvokeRequest) -> InvokeRequest:
        """
        Pre-model Prime Directives guard. Runs before the model call for all roles.
        Scans user_message and helm_response for instruction-level violation signals.

        Checks PD2, PD4, PD5 only — PD1 and PD3 are output characteristics,
        not input instructions. They are checked in _prime_directives_output.

        Applies to all roles (Option A — no role scoping). Projectionist and
        Archivist content does not match these patterns in normal operation.
        Guards apply to Helm Prime, where user-facing voice is generated.

        On violation: logs at WARNING, raises PrimeDirectivesViolation.
        Model call is never made.
        """
        content = (request.user_message + " " + request.helm_response).lower()

        for signal in _PD2_SIGNALS:
            if signal in content:
                logger.warning(
                    "Prime Directive pre-guard trip — PD2 (Do Not Deceive): "
                    "role=%s signal=%r", role, signal
                )
                raise PrimeDirectivesViolation(
                    directive="PD2",
                    detail=f"Request contains instruction to deceive Maxwell: {signal!r}",
                )

        for signal in _PD4_PRE_SIGNALS:
            if signal in content:
                logger.warning(
                    "Prime Directive pre-guard trip — PD4 (Human in the Loop): "
                    "role=%s signal=%r", role, signal
                )
                raise PrimeDirectivesViolation(
                    directive="PD4",
                    detail=f"Request contains instruction to act without Maxwell approval: {signal!r}",
                )

        for signal in _PD5_SIGNALS:
            if signal in content:
                logger.warning(
                    "Prime Directive pre-guard trip — PD5 (Honest Identity): "
                    "role=%s signal=%r", role, signal
                )
                raise PrimeDirectivesViolation(
                    directive="PD5",
                    detail=f"Request contains instruction to assert human identity: {signal!r}",
                )

        return request

    def _prime_directives_output(self, role: str, output: str) -> str:
        """
        Post-model Prime Directives guard. Runs after model output is received,
        before returning to caller. Scans output text for violation signals.

        Checks PD1, PD3, PD4, PD5. Applies to all roles.

        Known limitation: For Projectionist, output is a JSON frame containing
        a conversation already delivered to Maxwell. The guard scans the frame
        content (user/helm fields) but cannot retroactively block the turn.
        Real post-guard value is Archivist prose summaries and Helm Prime
        responses, which the guard can block before they reach Maxwell.

        On violation: logs at WARNING, raises PrimeDirectivesViolation.
        Output is never returned to caller.
        """
        content = output.lower()

        for signal in _PD1_SIGNALS:
            if signal in content:
                logger.warning(
                    "Prime Directive post-guard trip — PD1 (Do Not Harm): "
                    "role=%s signal=%r", role, signal
                )
                raise PrimeDirectivesViolation(
                    directive="PD1",
                    detail=f"Output contains direct harm recommendation: {signal!r}",
                )

        for signal in _PD3_SIGNALS:
            if signal in content:
                logger.warning(
                    "Prime Directive post-guard trip — PD3 (State Uncertainty): "
                    "role=%s signal=%r", role, signal
                )
                raise PrimeDirectivesViolation(
                    directive="PD3",
                    detail=f"Output presents speculation as certain fact: {signal!r}",
                )

        for signal in _PD4_POST_SIGNALS:
            if signal in content:
                logger.warning(
                    "Prime Directive post-guard trip — PD4 (Human in the Loop): "
                    "role=%s signal=%r", role, signal
                )
                raise PrimeDirectivesViolation(
                    directive="PD4",
                    detail=f"Output recommends consequential action without Maxwell approval: {signal!r}",
                )

        for signal in _PD5_POST_SIGNALS:
            if signal in content:
                logger.warning(
                    "Prime Directive post-guard trip — PD5 (Honest Identity): "
                    "role=%s signal=%r", role, signal
                )
                raise PrimeDirectivesViolation(
                    directive="PD5",
                    detail=f"Output claims human identity: {signal!r}",
                )

        return output
