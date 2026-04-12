"""
model_router.py — Config loading, provider resolution, LiteLLM dispatch.

Loads config.yaml at service startup. Resolves all env var values at startup
time — missing required env vars raise immediately, not silently at request time.

LiteLLM handles all provider normalization. This router never calls Anthropic,
OpenAI, or Ollama directly. It builds the correct kwargs and delegates.

Provider types:
  anthropic — requires api_key_env
  openai    — requires api_key_env
  ollama    — requires base_url_env (resolves to Ollama server URL)
  custom    — requires base_url_env; api_key_env optional
"""

import logging
import os
import time
from typing import Any

import litellm
import yaml

logger = logging.getLogger(__name__)

# Suppress LiteLLM's verbose startup output
litellm.suppress_debug_info = True


class UnknownRoleError(Exception):
    pass


class ConfigError(Exception):
    pass


class ModelRouter:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self._raw_config = yaml.safe_load(f)

        self._agent_configs = self._resolve_configs()
        self._supabase_config = self._resolve_supabase()

        logger.info("ModelRouter initialized. Agents: %s", list(self._agent_configs.keys()))

    def _resolve_configs(self) -> dict:
        """
        Resolve env var values for each agent. Fails at startup if a required
        env var is missing — never silently at request time.
        """
        agents_raw = self._raw_config.get("agents", {})
        resolved = {}

        for role, cfg in agents_raw.items():
            provider = cfg.get("provider")
            model = cfg.get("model")

            if not provider:
                raise ConfigError(f"Agent '{role}' missing required field: provider")
            if not model:
                raise ConfigError(f"Agent '{role}' missing required field: model")

            entry = {"provider": provider, "model": model}

            # Resolve API key
            api_key_env = cfg.get("api_key_env")
            if api_key_env:
                api_key = os.environ.get(api_key_env)
                if not api_key and provider in ("anthropic", "openai"):
                    raise ConfigError(
                        f"Agent '{role}' (provider: {provider}) requires env var "
                        f"'{api_key_env}' but it is not set."
                    )
                entry["api_key"] = api_key

            # Resolve base URL
            base_url_env = cfg.get("base_url_env")
            if base_url_env:
                base_url = os.environ.get(base_url_env, "http://localhost:11434")
                entry["base_url"] = base_url
            elif provider in ("ollama", "custom"):
                raise ConfigError(
                    f"Agent '{role}' (provider: {provider}) requires base_url_env "
                    f"to be set in config.yaml."
                )

            resolved[role] = entry

        return resolved

    def _resolve_supabase(self) -> dict:
        """Resolve Supabase connection details from config env vars."""
        sb = self._raw_config.get("supabase", {})
        url_env = sb.get("url_env", "SUPABASE_BRAIN_URL")
        key_env = sb.get("service_key_env", "SUPABASE_BRAIN_SERVICE_KEY")

        url = os.environ.get(url_env)
        key = os.environ.get(key_env)

        if not url:
            raise ConfigError(
                f"Supabase URL env var '{url_env}' is not set. "
                "Set it before starting the service."
            )
        if not key:
            raise ConfigError(
                f"Supabase service key env var '{key_env}' is not set. "
                "Set it before starting the service."
            )

        return {"url": url, "service_key": key}

    @property
    def supabase_url(self) -> str:
        return self._supabase_config["url"]

    @property
    def supabase_service_key(self) -> str:
        return self._supabase_config["service_key"]

    def get_agent_config(self, role: str) -> dict:
        """Return resolved config for a role. Raises UnknownRoleError if not found."""
        cfg = self._agent_configs.get(role)
        if not cfg:
            raise UnknownRoleError(
                f"No configuration found for role: '{role}'. "
                f"Configured roles: {list(self._agent_configs.keys())}"
            )
        return cfg

    def config_summary(self) -> dict:
        """
        Return agent config summary with no secrets exposed.
        Used by GET /config/agents.
        """
        summary = {}
        for role, cfg in self._agent_configs.items():
            entry = {"provider": cfg["provider"], "model": cfg["model"]}
            if cfg.get("base_url"):
                entry["base_url"] = cfg["base_url"]
            # api_key is intentionally omitted
            summary[role] = entry
        return summary

    async def invoke(
        self,
        role: str,
        messages: list,
        stream: bool = False,
        extra_kwargs: dict = None,
    ) -> Any:
        """
        Route a request to the model configured for role via LiteLLM.

        LiteLLM model string format: "provider/model"
        e.g. "anthropic/claude-sonnet-4-6", "ollama/qwen2.5:3b"

        For custom provider: use "openai/model-name" so LiteLLM treats it as
        an OpenAI-compatible endpoint and routes to the custom base_url.
        """
        cfg = self.get_agent_config(role)
        provider = cfg["provider"]
        model = cfg["model"]

        # LiteLLM model string
        if provider == "custom":
            # Custom endpoints speak OpenAI API format
            model_string = f"openai/{model}"
        else:
            model_string = f"{provider}/{model}"

        kwargs: dict[str, Any] = {
            "model": model_string,
            "messages": messages,
            "stream": stream,
        }

        if cfg.get("api_key"):
            kwargs["api_key"] = cfg["api_key"]
        if cfg.get("base_url"):
            kwargs["api_base"] = cfg["base_url"]

        if extra_kwargs:
            kwargs.update(extra_kwargs)

        logger.debug("Invoking %s → %s", role, model_string)
        return await litellm.acompletion(**kwargs)

    # Health check cache: role → {"result": dict, "checked_at": float}
    # TTL of 60s prevents repeated API calls to paid providers (Anthropic, OpenAI)
    # on every /health invocation (monitoring loops, smoke tests, Quartermaster polling).
    # Ollama/custom endpoints are cheap to ping but benefit from the same TTL for
    # consistency. Cache is per-instance — resets on service restart.
    _health_cache: dict = {}
    _health_cache_ttl: int = 60  # seconds

    async def check_model_health(self, role: str) -> dict:
        """
        Check if a model endpoint is reachable for a given role.
        Returns a dict with status, provider, model, and optional error.

        Results are cached for _health_cache_ttl seconds. Paid provider endpoints
        (Anthropic, OpenAI) are only pinged when the cache is stale — not on
        every /health call.
        """
        cfg = self._agent_configs.get(role)
        if not cfg:
            return {"status": "unconfigured", "error": f"No config for role: {role}"}

        # Return cached result if still fresh
        cached = self._health_cache.get(role)
        if cached and (time.monotonic() - cached["checked_at"]) < self._health_cache_ttl:
            return cached["result"]

        try:
            # Minimal ping — one token, no actual work
            await self.invoke(
                role,
                messages=[{"role": "user", "content": "ping"}],
                stream=False,
                extra_kwargs={"max_tokens": 1},
            )
            result = {
                "status": "ok",
                "provider": cfg["provider"],
                "model": cfg["model"],
            }
        except Exception as e:
            result = {
                "status": "unreachable",
                "provider": cfg["provider"],
                "model": cfg["model"],
                "error": str(e),
            }

        self._health_cache[role] = {"result": result, "checked_at": time.monotonic()}
        return result
