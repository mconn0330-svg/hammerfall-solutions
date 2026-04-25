"""
observability.py — Structured logging + correlation IDs + OpenTelemetry tracer.

T0.A6 lays the observability convention before T0.B1 (memory module). Every
log line is JSON-shaped and carries a correlation ID; every cross-component
operation can wrap itself in a tracer span. No exporter ships in T1 — spans
are structured for in-process inspection only. T4 / Stage 2 wires an OTLP
collector when there's somewhere to send them.

Conventions (also documented in /AGENTS.md):

  Logger names         helm.<module>            (helm.memory, helm.runtime, helm.agent.contemplator)
  Event names          dotted.snake_case        (memory.write, memory.write.failed, agent.invoked)
  Levels               info / warning / error / critical
  Required fields      correlation_id           (auto-bound via contextvars)
  Error events         error (str), error_type (cls name), traceback

Usage:

    from observability import get_logger, tracer
    log = get_logger("helm.memory")
    log.info("memory.write", project=p, agent=a, memory_type=t)

    with tracer.start_as_current_span("memory.write") as span:
        span.set_attribute("project", p)
        ...

Stdlib `logging.getLogger(__name__)` calls are bridged through the same
processor pipeline so existing modules emit the same JSON shape without
needing a refactor pass.
"""

import logging
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# ---------------------------------------------------------------------------
# Correlation ID context — propagates through all logs in a request.
# Set in the FastAPI middleware (see main.py), reset on response.
# ---------------------------------------------------------------------------

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Return the current request's correlation ID. Lazily generates one if
    none is set — safe to call from background tasks or one-off scripts."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid4())
        correlation_id_var.set(cid)
    return cid


def new_correlation_id() -> str:
    """Generate a fresh correlation ID without binding it. Caller binds via
    `structlog.contextvars.bind_contextvars(correlation_id=cid)` to scope it."""
    return str(uuid4())


# ---------------------------------------------------------------------------
# Logging configuration — call once at service startup.
# ---------------------------------------------------------------------------

_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def configure_logging(level: str = "info") -> None:
    """Configure structlog + bridge stdlib logging through the same JSON pipeline.

    Idempotent — safe to call multiple times. The level argument accepts the
    same lowercase strings that `config.yaml` uses (`debug`, `info`, ...).

    Stdlib loggers (`logging.getLogger(__name__)`) emit through structlog's
    ProcessorFormatter so existing helm-runtime modules don't need to migrate
    to call `get_logger()` immediately. New modules should prefer the
    structlog API for ergonomic kwargs.
    """
    log_level = _LEVEL_MAP.get(level.lower(), logging.INFO)

    # Shared processor chain — applied to BOTH structlog and stdlib log records.
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.dict_tracebacks,
    ]

    # structlog: format + render
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Stdlib bridge: route logging.getLogger() through the same JSON renderer.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Replace handlers cleanly — supports re-configuration without duplicates.
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(log_level)


def get_logger(name: str) -> Any:
    """Return a structlog logger. Use the `helm.<module>` naming convention
    (e.g., `helm.memory`, `helm.agent.contemplator`)."""
    return structlog.get_logger(name)


# ---------------------------------------------------------------------------
# OpenTelemetry tracer — no exporter in T1.
# Spans give us in-process structure (parent/child relationships, attributes)
# even without remote shipping. Stage 2 wires an OTLP exporter when a
# collector lands.
# ---------------------------------------------------------------------------

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer("helm.runtime")
