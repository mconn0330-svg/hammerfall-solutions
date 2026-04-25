"""
model_router.py — Config loading, provider resolution, LiteLLM dispatch.

Loads config.yaml at service startup. Config structure is validated against a
Pydantic schema — malformed config produces a clear named error at startup, not
a mysterious failure at request time. All env var values are resolved at startup
too; missing required env vars raise immediately.

LiteLLM handles all provider normalization. This router never calls Anthropic,
OpenAI, or Ollama directly. It builds the correct kwargs and delegates.

Provider types:
  anthropic — Claude API. Requires api_key_env.
  openai    — OpenAI API. Requires api_key_env.
  ollama    — Local Ollama instance. Requires base_url_env.
  custom    — Any OpenAI-compatible endpoint. Requires base_url_env.
              api_key_env is optional (some endpoints need no auth).

BYO model contract:
  Swapping any agent's model is one line in config.yaml + service restart.
  No code changes required for any supported provider type.
  See config.yaml for annotated examples of each provider type.
"""

import logging
import os
import time
from enum import StrEnum
from typing import Any

import litellm
import yaml
from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger(__name__)

# Suppress LiteLLM's verbose startup output
litellm.suppress_debug_info = True


# ---------------------------------------------------------------------------
# Config schema — Pydantic models
# ---------------------------------------------------------------------------


class Provider(StrEnum):
    anthropic = "anthropic"
    openai = "openai"
    ollama = "ollama"
    custom = "custom"


class AgentConfigSchema(BaseModel):
    """Schema for a single agent entry in config.yaml."""

    provider: Provider
    model: str
    api_key_env: str | None = None
    base_url_env: str | None = None

    @model_validator(mode="after")
    def validate_provider_requirements(self) -> "AgentConfigSchema":
        if self.provider in (Provider.anthropic, Provider.openai):
            if not self.api_key_env:
                raise ValueError(
                    f"Provider '{self.provider}' requires api_key_env to be set in config.yaml."
                )
        if self.provider in (Provider.ollama, Provider.custom):
            if not self.base_url_env:
                raise ValueError(
                    f"Provider '{self.provider}' requires base_url_env to be set in config.yaml."
                )
        return self


class EmbeddingsConfigSchema(BaseModel):
    """Schema for the optional embeddings block in config.yaml."""

    model: str = "text-embedding-3-small"
    api_key_env: str = "OPENAI_API_KEY"


class SupabaseConfigSchema(BaseModel):
    """Schema for the supabase block in config.yaml."""

    url_env: str = "SUPABASE_BRAIN_URL"
    service_key_env: str = "SUPABASE_BRAIN_SERVICE_KEY"


class ServiceConfigSchema(BaseModel):
    """Schema for the service block in config.yaml."""

    port: int = 8000
    log_level: str = "info"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in valid:
            raise ValueError(f"log_level must be one of {valid}, got: '{v}'")
        return v.lower()


class HelmRuntimeConfig(BaseModel):
    """Root config schema. Validated at service startup."""

    service: ServiceConfigSchema = ServiceConfigSchema()
    supabase: SupabaseConfigSchema = SupabaseConfigSchema()
    embeddings: EmbeddingsConfigSchema | None = None
    agents: dict[str, AgentConfigSchema]

    @field_validator("agents")
    @classmethod
    def agents_not_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("agents block must define at least one agent role.")
        return v


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class UnknownRoleError(Exception):
    pass


class ConfigError(Exception):
    pass


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------


class ModelRouter:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            raw = yaml.safe_load(f)

        # Pydantic schema validation — raises ValidationError with field-level
        # detail on any structural or type error in config.yaml
        try:
            self._config = HelmRuntimeConfig(**raw)
        except Exception as e:
            raise ConfigError(f"config.yaml validation failed:\n{e}") from e

        self._agent_configs = self._resolve_env_vars()
        self._supabase_config = self._resolve_supabase()
        self._embeddings_config = self._resolve_embeddings()

        logger.info("ModelRouter initialized. Agents: %s", list(self._agent_configs.keys()))

    def _resolve_env_vars(self) -> dict:
        """
        Resolve all env var values from the validated config schema.
        Raises ConfigError immediately if a required env var is missing.
        Returns a dict of role → resolved runtime config (provider, model, api_key, base_url).
        """
        resolved = {}

        for role, cfg in self._config.agents.items():
            entry: dict[str, Any] = {
                "provider": cfg.provider.value,
                "model": cfg.model,
            }

            # Resolve API key
            if cfg.api_key_env:
                api_key = os.environ.get(cfg.api_key_env)
                if not api_key and cfg.provider in (Provider.anthropic, Provider.openai):
                    raise ConfigError(
                        f"Agent '{role}' (provider: {cfg.provider.value}) requires env var "
                        f"'{cfg.api_key_env}' but it is not set. "
                        f"Add it to your environment before starting the service."
                    )
                if api_key:
                    entry["api_key"] = api_key

            # Resolve base URL
            if cfg.base_url_env:
                base_url = os.environ.get(cfg.base_url_env)
                if not base_url:
                    if cfg.provider == Provider.ollama:
                        # Ollama: well-known default, warn but don't fail
                        base_url = "http://localhost:11434"
                        logger.warning(
                            "Agent '%s': env var '%s' not set — defaulting to %s. "
                            "Set %s explicitly for non-local deployments.",
                            role,
                            cfg.base_url_env,
                            base_url,
                            cfg.base_url_env,
                        )
                    else:
                        # custom provider: no safe default exists
                        raise ConfigError(
                            f"Agent '{role}' (provider: {cfg.provider.value}) requires env var "
                            f"'{cfg.base_url_env}' but it is not set."
                        )
                entry["base_url"] = base_url

            resolved[role] = entry

        return resolved

    def _resolve_supabase(self) -> dict:
        """Resolve Supabase connection details from validated config schema."""
        sb = self._config.supabase
        url = os.environ.get(sb.url_env)
        key = os.environ.get(sb.service_key_env)

        if not url:
            raise ConfigError(
                f"Supabase URL env var '{sb.url_env}' is not set. "
                "Set it before starting the service."
            )
        if not key:
            raise ConfigError(
                f"Supabase service key env var '{sb.service_key_env}' is not set. "
                "Set it before starting the service."
            )

        return {"url": url, "service_key": key}

    def _resolve_embeddings(self) -> dict:
        """
        Resolve embedding config. Optional — returns empty dict if no embeddings block.
        Warns (does not fail) if api_key_env is set but env var is missing.
        """
        emb = self._config.embeddings
        if emb is None:
            return {}

        api_key = os.environ.get(emb.api_key_env)
        if not api_key:
            logger.warning(
                "Embeddings configured but '%s' env var is not set — "
                "embedding generation disabled. Set %s to enable semantic search.",
                emb.api_key_env,
                emb.api_key_env,
            )
            return {"model": emb.model}

        return {"model": emb.model, "api_key": api_key}

    @property
    def embedding_api_key(self) -> str | None:
        return self._embeddings_config.get("api_key")

    @property
    def embedding_model(self) -> str:
        return self._embeddings_config.get("model", "text-embedding-3-small")

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
            # api_key intentionally omitted
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

        custom provider uses "openai/model" — LiteLLM treats it as an
        OpenAI-compatible endpoint and routes to the configured base_url.
        Any service that speaks the OpenAI API format works with zero
        additional code.
        """
        cfg = self.get_agent_config(role)
        provider = cfg["provider"]
        model = cfg["model"]

        # LiteLLM model string
        if provider == "custom":
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
    # on every /health invocation (monitoring loops, smoke tests, external pollers).
    _health_cache: dict = {}
    _health_cache_ttl: int = 60  # seconds

    async def check_model_health(self, role: str) -> dict:
        """
        Check if a model endpoint is reachable for a given role.
        Results cached for _health_cache_ttl seconds — paid provider endpoints
        are not pinged on every /health call.
        """
        cfg = self._agent_configs.get(role)
        if not cfg:
            return {"status": "unconfigured", "error": f"No config for role: {role}"}

        cached = self._health_cache.get(role)
        if cached and (time.monotonic() - cached["checked_at"]) < self._health_cache_ttl:
            return cached["result"]

        try:
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
