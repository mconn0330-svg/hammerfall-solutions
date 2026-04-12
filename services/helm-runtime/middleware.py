"""
middleware.py — Helm Runtime Service middleware pipeline.

Every /invoke/{role} request passes through this pipeline.
Pre-model hooks run before the model call.
Post-model hooks run after model output is received, before returning to caller.

BA7 implements two active hooks:
  - session_context_inject (pre)  — injects session_id, turn_number, project
  - output_validator (post)       — validates Projectionist output matches frame schema

Stub hooks (pass-through, not yet implemented):
  - personality_inject (pre)      — TODO: BA8 — load helm_personality scores into prompt
  - prime_directives_guard (pre)  — TODO: BA9 — validate request before model call
  - prime_directives_output (post)— TODO: BA9 — scan output for Prime Directive violations
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

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
        Only applied to roles that use session context (not speaker at T1).
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
        TODO: BA8 — Load helm_personality scores from Supabase and inject into
        system prompt for roles that generate user-facing output (Speaker, Helm Prime).
        Projectionist and Archivist are exempt — they do not generate voice responses.
        """
        return request

    def _prime_directives_guard(self, role: str, request: InvokeRequest) -> InvokeRequest:
        """
        TODO: BA9 — Validate that the incoming request does not ask the model to
        violate a Prime Directive before the model call is made.
        """
        return request

    def _prime_directives_output(self, role: str, output: str) -> str:
        """
        TODO: BA9 — Scan model output for Prime Directive violations before
        returning to caller. If violation detected, block the response.
        """
        return output
