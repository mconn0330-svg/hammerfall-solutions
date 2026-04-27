"""CLI entry point for memory.prompt management.

Invoke as:
    python -m memory.prompt <subcommand> [args]

Subcommands:
    list                          Show all agent_roles + active version
    history <role>                Show version chronology for one role
    push <role> [--notes ...]     Push local file to Supabase as new active version
    pull <role>                   Pull active version, overwrite local file
    diff <role>                   Show diff between local file and current active
    activate <role> <version>     Flip a specific past version back to active

Reads Supabase URL + service key from env. Honors HELM_MEMORY_SUPABASE_URL /
HELM_MEMORY_SUPABASE_SERVICE_KEY first, falls back to SUPABASE_BRAIN_URL /
SUPABASE_BRAIN_SERVICE_KEY (the runtime-wide vars). Either works.

Local prompt files live at services/helm-runtime/agents/prompts/<role>.md.
The CLI resolves them relative to its own location so it works from any cwd.
"""

from __future__ import annotations

import argparse
import asyncio
import difflib
import os
import sys
from pathlib import Path

from read_client import ReadClient

from .client import MemoryClient
from .prompt import PromptManager, PromptManagerError
from .seed import (
    SeedError,
    seed_entities_from_file,
    seed_relationships_from_file,
)
from .settings import MemorySettings
from .writer import MemoryWriter

# Force UTF-8 output so prompt content with em-dashes / unicode renders
# correctly on Windows consoles (cp1252 default chokes on U+2014, U+2713, etc.).
# Containers and Linux/macOS already default to UTF-8; this is the Windows fix.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "agents" / "prompts"


def _env(*names: str) -> str | None:
    """Return the first env var found among `names`. None if all unset."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _build_pm() -> PromptManager:
    """Construct a PromptManager from env. Errors loudly if env not set."""
    url = _env("HELM_MEMORY_SUPABASE_URL", "SUPABASE_BRAIN_URL")
    key = _env("HELM_MEMORY_SUPABASE_SERVICE_KEY", "SUPABASE_BRAIN_SERVICE_KEY")
    if not url or not key:
        print(
            "error: Supabase env not configured. Set HELM_MEMORY_SUPABASE_URL + "
            "HELM_MEMORY_SUPABASE_SERVICE_KEY (or SUPABASE_BRAIN_URL + "
            "SUPABASE_BRAIN_SERVICE_KEY).",
            file=sys.stderr,
        )
        sys.exit(2)
    return PromptManager(ReadClient(url=url, service_key=key))


def _path_for(role: str) -> Path:
    return PROMPTS_DIR / f"{role}.md"


# ─── Subcommands ────────────────────────────────────────────────────────────


async def cmd_list(_args: argparse.Namespace) -> int:
    pm = _build_pm()
    rows = await pm.list_active()
    if not rows:
        print("(no active prompts in helm_prompts)")
        return 0
    print(f"{'AGENT_ROLE':<24} {'VER':>4}  PUSHED_BY      PUSHED_AT")
    for r in rows:
        ts = str(r.get("created_at", ""))[:19]
        print(f"{r['agent_role']:<24} {r['version']:>4}  {(r.get('pushed_by') or '?'):<14} {ts}")
    return 0


async def cmd_history(args: argparse.Namespace) -> int:
    pm = _build_pm()
    rows = await pm.list_versions(args.role)
    if not rows:
        print(f"(no rows for agent_role={args.role!r})")
        return 1
    print(f"{'VER':>4}  {'ACTIVE':<6}  PUSHED_BY      PUSHED_AT          NOTES")
    for r in rows:
        ts = str(r.get("created_at", ""))[:19]
        active = "[*]" if r["active"] else "   "
        notes = (r.get("notes") or "").replace("\n", " ")[:60]
        print(f"{r['version']:>4}  {active:<6}  {(r.get('pushed_by') or '?'):<14} {ts}  {notes}")
    return 0


async def cmd_push(args: argparse.Namespace) -> int:
    path = _path_for(args.role)
    if not path.exists():
        print(f"error: local file not found: {path}", file=sys.stderr)
        return 1
    content = path.read_text(encoding="utf-8")
    pm = _build_pm()
    version = await pm.push(
        args.role,
        content,
        pushed_by=args.pushed_by,
        pushed_from="cli",
        notes=args.notes,
    )
    print(f"pushed {args.role} v{version} ({len(content)} bytes)")
    return 0


async def cmd_pull(args: argparse.Namespace) -> int:
    pm = _build_pm()
    target = _path_for(args.role)
    try:
        version = await pm.pull(args.role, target)
    except PromptManagerError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"pulled {args.role} v{version} → {target}")
    return 0


async def cmd_diff(args: argparse.Namespace) -> int:
    pm = _build_pm()
    rows = await pm.list_active()
    active = next((r for r in rows if r["agent_role"] == args.role), None)
    if not active:
        print(f"error: no active row for agent_role={args.role!r}", file=sys.stderr)
        return 1
    # Re-fetch the content (list_active doesn't include it)
    content_rows = await pm._supabase.select(  # noqa: SLF001 — internal use
        pm.TABLE,
        {
            "agent_role": f"eq.{args.role}",
            "active": "eq.true",
            "select": "content",
            "limit": "1",
        },
    )
    remote = str(content_rows[0]["content"]) if content_rows else ""
    path = _path_for(args.role)
    local = path.read_text(encoding="utf-8") if path.exists() else ""
    if local == remote:
        print(f"{args.role}: local matches active v{active['version']} (no diff)")
        return 0
    diff = difflib.unified_diff(
        remote.splitlines(keepends=True),
        local.splitlines(keepends=True),
        fromfile=f"supabase:{args.role}@v{active['version']}",
        tofile=f"local:{path}",
    )
    sys.stdout.writelines(diff)
    return 0


async def cmd_activate(args: argparse.Namespace) -> int:
    pm = _build_pm()
    try:
        await pm.activate(args.role, args.version)
    except PromptManagerError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"activated {args.role} v{args.version}")
    return 0


# ─── Seed CLI (Finding #010 — replaces deleted scripts/seed_*.sh) ──────────


def _build_writer_and_client() -> tuple[MemoryWriter, ReadClient]:
    """Construct a MemoryWriter (writes via MemoryClient) plus a ReadClient
    (for the safety-guard counts and name→UUID lookups). Both bind to the
    same env-resolved Supabase URL + service key."""
    url = _env("HELM_MEMORY_SUPABASE_URL", "SUPABASE_BRAIN_URL")
    key = _env("HELM_MEMORY_SUPABASE_SERVICE_KEY", "SUPABASE_BRAIN_SERVICE_KEY")
    if not url or not key:
        print(
            "error: Supabase env not configured. Set HELM_MEMORY_SUPABASE_URL + "
            "HELM_MEMORY_SUPABASE_SERVICE_KEY (or SUPABASE_BRAIN_URL + "
            "SUPABASE_BRAIN_SERVICE_KEY).",
            file=sys.stderr,
        )
        sys.exit(2)
    settings = MemorySettings(supabase_url=url, supabase_service_key=key)
    writer = MemoryWriter(MemoryClient(settings))
    read_client = ReadClient(url=url, service_key=key)
    return writer, read_client


async def cmd_seed_entities(args: argparse.Namespace) -> int:
    """Seed `helm_entities` from a YAML data file."""
    writer, read_client = _build_writer_and_client()
    try:
        name_to_uuid = await seed_entities_from_file(read_client, writer, args.data_file)
    except SeedError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"seeded {len(name_to_uuid)} entities from {args.data_file}")
    return 0


async def cmd_seed_relationships(args: argparse.Namespace) -> int:
    """Seed `helm_entity_relationships` from a YAML data file.

    Resolves entity names to UUIDs by querying `helm_entities` first —
    so this command can run independently of seed-entities (as long as
    the entities are already in the brain)."""
    writer, read_client = _build_writer_and_client()

    # Build name → UUID map by re-querying current entities.
    rows = await read_client.select("helm_entities", {"select": "id,name"})
    if not rows:
        print(
            "error: helm_entities is empty — run `seed-entities` first.",
            file=sys.stderr,
        )
        return 1
    from uuid import UUID  # local import keeps top-of-file imports tidy

    name_to_uuid = {row["name"]: UUID(row["id"]) for row in rows}

    try:
        count = await seed_relationships_from_file(
            read_client, writer, name_to_uuid, args.data_file
        )
    except SeedError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"seeded {count} relationships from {args.data_file}")
    return 0


# ─── Argparse ───────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m memory.prompt",
        description="Manage agent prompts in helm_prompts (T0.B6 CLI).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True, metavar="<command>")

    sub.add_parser("list", help="show all agent_roles + active version")

    p_history = sub.add_parser("history", help="show version chronology for one role")
    p_history.add_argument("role", help="agent_role (e.g. helm_prime)")

    p_push = sub.add_parser("push", help="push local file to Supabase as new active version")
    p_push.add_argument("role")
    p_push.add_argument("--notes", default=None, help="commit-message-style note for the push")
    p_push.add_argument("--pushed-by", default=os.environ.get("USER") or "cli", help="audit field")

    p_pull = sub.add_parser("pull", help="pull active version, overwrite local file")
    p_pull.add_argument("role")

    p_diff = sub.add_parser("diff", help="diff local file vs current active in Supabase")
    p_diff.add_argument("role")

    p_act = sub.add_parser("activate", help="flip a past version back to active (revert)")
    p_act.add_argument("role")
    p_act.add_argument("version", type=int)

    p_seed_e = sub.add_parser(
        "seed-entities",
        help="seed helm_entities from a YAML data file (Finding #010)",
    )
    p_seed_e.add_argument("data_file", help="path to entities.yaml")

    p_seed_r = sub.add_parser(
        "seed-relationships",
        help="seed helm_entity_relationships from a YAML data file (Finding #010)",
    )
    p_seed_r.add_argument("data_file", help="path to relationships.yaml")

    return parser


HANDLERS = {
    "list": cmd_list,
    "history": cmd_history,
    "push": cmd_push,
    "pull": cmd_pull,
    "diff": cmd_diff,
    "activate": cmd_activate,
    "seed-entities": cmd_seed_entities,
    "seed-relationships": cmd_seed_relationships,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = HANDLERS[args.cmd]
    return asyncio.run(handler(args))


if __name__ == "__main__":
    sys.exit(main())
