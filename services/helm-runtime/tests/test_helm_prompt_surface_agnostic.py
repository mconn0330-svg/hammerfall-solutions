"""Regression guard: helm_prime.md must stay surface-agnostic.

Per V2.1 spec T0.B6 + the durable infrastructure-portable directive: the
canonical Helm Prime prompt must not encode IDE/shell/surface assumptions.
Routines describe what the runtime DOES around Prime, not what Prime
EXECUTES. After T0.B6 cutover, no bash, no curl, no IDE-specific naming.

Forbidden tokens enumerated below. Adding a new forbidden token is a
one-line change to FORBIDDEN. Allowing a new exception is a one-line
addition to ALLOWED_EXCEPTIONS (with a comment explaining why).
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROMPT_PATH = Path(__file__).resolve().parent.parent / "agents" / "prompts" / "helm_prime.md"


# Forbidden tokens that must not appear in helm_prime.md after T0.B6 cutover.
# Token, reason, suggested replacement.
FORBIDDEN: list[tuple[str, str, str]] = [
    ("```bash", "bash code blocks — runtime executes, not Prime", "describe behavior in prose"),
    ("curl ", "curl invocations — Prime does not call HTTP", "describe what the runtime queries"),
    (
        "node -e",
        "inline node — Prime does not execute scripts",
        "describe what the runtime computes",
    ),
    (
        "$BRAIN_URL",
        "env-var reference — Prime is invoked, not invoking",
        "describe brain reads conceptually",
    ),
    (
        "$SUPABASE_BRAIN_SERVICE_KEY",
        "env-var reference — Prime is invoked, not invoking",
        "describe brain reads conceptually",
    ),
    ("localhost:8000", "localhost reference — surface-bound", "use 'the runtime' generically"),
    ("Antigravity", "IDE-specific naming", "use 'the runtime' or surface-agnostic phrasing"),
    ("Claude Code", "IDE-specific naming", "use 'the runtime' or surface-agnostic phrasing"),
    (
        "hammerfall-config.md",
        "local config file reference — config moved to config.yaml in T0.B5b",
        "describe runtime tunables conceptually",
    ),
    (
        "powershell.exe",
        "Windows-specific shell invocation",
        "remove — runtime owns operational concerns",
    ),
    (
        "BEHAVIORAL_PROFILE.md",
        "orphan snapshot file — deleted in T0.B6",
        "describe Routine 5 snapshots conceptually",
    ),
    (
        "BRAIN_SUMMARY.md",
        "orphan snapshot file — deleted in T0.B6",
        "describe Routine 5 snapshots conceptually",
    ),
    (
        "BELIEFS_SUMMARY.md",
        "orphan snapshot file — deleted in T0.B6",
        "describe Routine 5 snapshots conceptually",
    ),
    (
        "PERSONALITY_SUMMARY.md",
        "orphan snapshot file — deleted in T0.B6",
        "describe Routine 5 snapshots conceptually",
    ),
    (
        "ShortTerm_Scratchpad.md",
        "orphan snapshot file — deleted in T0.B6",
        "describe scratchpad as a memory_type, not a file",
    ),
    (
        "scripts/brain.sh",
        "deleted in T0.B6 — replaced by memory module",
        "describe writes through the memory module",
    ),
    (
        "scripts/snapshot.sh",
        "deleted in T0.B6",
        "describe Routine 5 snapshots conceptually",
    ),
    (
        "session_watchdog",
        "session instrumentation script — deleted in T0.B6",
        "remove — runtime owns session liveness",
    ),
    (
        "ping_session",
        "session instrumentation script — deleted in T0.B6",
        "remove — runtime owns session liveness",
    ),
    (
        "activity_ping",
        "session instrumentation script — deleted in T0.B6",
        "remove — runtime owns activity tracking",
    ),
]


def test_prompt_file_exists() -> None:
    """Sanity check: the canonical prompt file is on disk where the runtime
    expects it (services/helm-runtime/agents/prompts/helm_prime.md)."""
    assert PROMPT_PATH.exists(), f"helm_prime.md not found at {PROMPT_PATH}"


@pytest.mark.parametrize("token, reason, suggestion", FORBIDDEN)
def test_helm_prime_prompt_does_not_contain_forbidden_token(
    token: str, reason: str, suggestion: str
) -> None:
    """Each forbidden token gets its own test case so failures point at
    exactly which surface assumption leaked back in."""
    content = PROMPT_PATH.read_text(encoding="utf-8")
    if token in content:
        line_no = next(
            (i for i, line in enumerate(content.splitlines(), 1) if token in line),
            None,
        )
        pytest.fail(
            f"helm_prime.md contains forbidden token {token!r} at line {line_no}.\n"
            f"  Why forbidden: {reason}\n"
            f"  Suggested replacement: {suggestion}\n"
            f"  Per V2.1 spec T0.B6: prompts describe runtime behavior, not Prime execution."
        )


def test_no_surprise_bash_block() -> None:
    """Catches generic ``` ... ``` shell blocks beyond the explicit ```bash check.
    Permits ```json, ```python, etc. — those are safe (illustrative content)."""
    content = PROMPT_PATH.read_text(encoding="utf-8")
    bad_fences = ["```sh\n", "```shell\n", "```zsh\n"]
    for fence in bad_fences:
        if fence in content:
            pytest.fail(
                f"helm_prime.md contains shell code fence {fence!r} — runtime "
                "executes, not Prime."
            )
