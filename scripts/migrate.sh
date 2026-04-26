#!/usr/bin/env bash
# T0.A9 — Operator tool for Supabase migrations.
# Spec: docs/stage1/Helm_T1_Launch_Spec_V2.md §T0.A9
# Policy: docs/adr/0002-migration-reversibility-policy.md
#
# Usage:
#   ./scripts/migrate.sh push           — apply pending migrations to the linked project
#   ./scripts/migrate.sh verify         — show schema diff vs the linked project
#   ./scripts/migrate.sh baseline-dump  — refresh supabase/schema_baseline.sql from the linked project
#
# Prerequisites:
#   - supabase CLI installed and logged in (`supabase login`)
#   - project linked once via `supabase link --project-ref <ref>`
#
# Notes:
#   - For baseline-dump we use `supabase db dump --schema public` rather than
#     raw `pg_dump $SUPABASE_DB_URL` (spec's first instinct). The supabase CLI
#     reuses the existing project link and doesn't need a separate Postgres URL
#     or local pg_dump install. If you specifically need pg_dump and have
#     SUPABASE_DB_URL set, fall back to:
#         pg_dump "$SUPABASE_DB_URL" --schema-only --schema=public > supabase/schema_baseline.sql

set -euo pipefail

cd "$(dirname "$0")/.."

case "${1:-push}" in
  push)
    echo "Applying pending migrations to linked project..."
    supabase db push
    ;;

  verify)
    echo "Schema diff vs linked project (empty output = in sync):"
    supabase db diff --schema public
    ;;

  baseline-dump)
    echo "Dumping schema baseline to supabase/schema_baseline.sql..."
    supabase db dump --schema public > supabase/schema_baseline.sql
    echo "Done. Review the diff and commit if intentional."
    ;;

  *)
    echo "usage: $0 [push|verify|baseline-dump]" >&2
    exit 1
    ;;
esac
