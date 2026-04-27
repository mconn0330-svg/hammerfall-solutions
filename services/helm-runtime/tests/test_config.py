"""Tests for runtime tunables — config.yaml load + HELM_RUNTIME_* env override.

Covers the precedence chain set up in T0.B5b:
    HELM_RUNTIME_<FIELD> env  >  config.yaml runtime_tunables  >  RuntimeTunables defaults

Direct RuntimeTunables tests cover the override mechanism. The ModelRouter
integration test covers the yaml→property wiring so a future refactor can't
silently break the contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from model_router import ModelRouter, RuntimeTunables


# RuntimeTunables reads HELM_RUNTIME_* from process env. Strip any
# inherited values per-test so machine-local state can't pollute results.
@pytest.fixture(autouse=True)
def _clear_helm_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for key in list(os.environ.keys()):
        if key.startswith("HELM_RUNTIME_"):
            monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# RuntimeTunables — direct unit tests
# ---------------------------------------------------------------------------


def test_runtime_tunables_default_load() -> None:
    """No env, no kwargs — defaults match the values committed in config.yaml."""
    t = RuntimeTunables()
    assert t.frame_offload_interval == 10
    assert t.warm_queue_max_frames == 20
    assert t.frame_offload_conservative is True


def test_runtime_tunables_yaml_kwargs_override_defaults() -> None:
    """kwargs path = yaml runtime_tunables block. Overrides class defaults."""
    t = RuntimeTunables(
        frame_offload_interval=25,
        warm_queue_max_frames=50,
        frame_offload_conservative=False,
    )
    assert t.frame_offload_interval == 25
    assert t.warm_queue_max_frames == 50
    assert t.frame_offload_conservative is False


def test_runtime_tunables_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """HELM_RUNTIME_* env wins over yaml-supplied kwargs.

    This is the load-bearing assertion for per-deployment tuning: a Render
    instance can set HELM_RUNTIME_WARM_QUEUE_MAX_FRAMES=50 and override
    the committed config.yaml without a code change.
    """
    monkeypatch.setenv("HELM_RUNTIME_FRAME_OFFLOAD_INTERVAL", "30")
    monkeypatch.setenv("HELM_RUNTIME_WARM_QUEUE_MAX_FRAMES", "100")
    monkeypatch.setenv("HELM_RUNTIME_FRAME_OFFLOAD_CONSERVATIVE", "false")

    # yaml passes 10/20/true; env should beat it
    t = RuntimeTunables(
        frame_offload_interval=10,
        warm_queue_max_frames=20,
        frame_offload_conservative=True,
    )
    assert t.frame_offload_interval == 30
    assert t.warm_queue_max_frames == 100
    assert t.frame_offload_conservative is False


def test_runtime_tunables_env_override_without_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env wins over the class default when no yaml kwargs are passed."""
    monkeypatch.setenv("HELM_RUNTIME_FRAME_OFFLOAD_INTERVAL", "7")
    t = RuntimeTunables()
    assert t.frame_offload_interval == 7
    # Untouched fields keep their defaults
    assert t.warm_queue_max_frames == 20
    assert t.frame_offload_conservative is True


# ---------------------------------------------------------------------------
# ModelRouter integration — yaml block flows through to .tunables property
# ---------------------------------------------------------------------------


_CONFIG_PREAMBLE = """\
service:
  port: 8000
  log_level: info

supabase:
  url_env: TEST_SUPABASE_URL
  service_key_env: TEST_SUPABASE_KEY
"""

_CONFIG_AGENTS = """\
agents:
  projectionist:
    provider: ollama
    model: qwen2.5:3b
    base_url_env: TEST_OLLAMA_URL
"""


def _write_config(tmp_path: Path, runtime_tunables_block: str) -> Path:
    """Compose a minimal yaml config: preamble + optional runtime_tunables
    block + one ollama agent. Ollama needs no env at startup (defaults
    base_url to localhost), keeping the test hermetic.

    runtime_tunables_block is yaml text starting at column 0 (or empty).
    Composed with plain string concatenation — textwrap.dedent + f-string
    interpolation does not propagate dedent into multi-line variables.
    """
    parts = [_CONFIG_PREAMBLE]
    if runtime_tunables_block:
        parts.append("\n" + runtime_tunables_block.rstrip() + "\n")
    parts.append("\n" + _CONFIG_AGENTS)
    path = tmp_path / "config.yaml"
    path.write_text("".join(parts))
    return path


def test_model_router_tunables_from_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """yaml runtime_tunables block flows through ModelRouter.tunables property."""
    monkeypatch.setenv("TEST_SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("TEST_SUPABASE_KEY", "k")

    cfg_path = _write_config(
        tmp_path,
        "runtime_tunables:\n"
        "  frame_offload_interval: 15\n"
        "  warm_queue_max_frames: 40\n"
        "  frame_offload_conservative: false\n",
    )
    router = ModelRouter(str(cfg_path))
    assert router.tunables.frame_offload_interval == 15
    assert router.tunables.warm_queue_max_frames == 40
    assert router.tunables.frame_offload_conservative is False


def test_model_router_tunables_default_when_yaml_omits_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing runtime_tunables block — RuntimeTunables falls back to defaults."""
    monkeypatch.setenv("TEST_SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("TEST_SUPABASE_KEY", "k")

    cfg_path = _write_config(tmp_path, "")
    router = ModelRouter(str(cfg_path))
    assert router.tunables.frame_offload_interval == 10
    assert router.tunables.warm_queue_max_frames == 20
    assert router.tunables.frame_offload_conservative is True


def test_model_router_env_overrides_yaml_tunables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end precedence: HELM_RUNTIME_* env beats the yaml block in
    a real ModelRouter construction. This is the contract a Render-style
    deployment relies on."""
    monkeypatch.setenv("TEST_SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("TEST_SUPABASE_KEY", "k")
    monkeypatch.setenv("HELM_RUNTIME_WARM_QUEUE_MAX_FRAMES", "200")

    cfg_path = _write_config(
        tmp_path,
        "runtime_tunables:\n  warm_queue_max_frames: 20\n",
    )
    router = ModelRouter(str(cfg_path))
    assert router.tunables.warm_queue_max_frames == 200
