#!/usr/bin/env bash
# T0.A10 — Manual Supabase brain backup. Cron-friendly.
# Spec: docs/stage1/Helm_T1_Launch_Spec_V2.md §T0.A10
# Runbook: docs/runbooks/0002-supabase-backup-restore.md
#
# Belt-and-suspenders backup on top of Supabase's Pro-tier automatic
# daily snapshots (PITR). The runbook explains why we keep this even
# though the platform backs up too.
#
# Output: ~/helm-backups/helm-brain-YYYYMMDD-HHMMSS.sql (full data + schema)
# Retention: keeps the last 30 dumps; older ones are deleted.
#
# Usage:
#   ./scripts/backup.sh                    # one-off
#   crontab -e                             # then:
#   0 3 * * *  /full/path/to/scripts/backup.sh >> ~/helm-backups/backup.log 2>&1
#
# Prerequisites:
#   - supabase CLI logged in (`supabase login`) and project linked
#     (`supabase link --project-ref <ref>`)
#   - Disk space: each dump is ~3-10 MB at T1 sizes; 30 dumps ~ 100-300 MB
#
# What's NOT in this dump:
#   - Auth users (no users at T1; T1 is Maxwell-only via static bearer)
#   - Storage buckets (none at T1)
#   - RLS policies survive in the schema (they're DDL, included)
#   - Postgres roles / extensions (Supabase reprovisions these on restore)

set -euo pipefail

BACKUP_DIR="${HELM_BACKUP_DIR:-$HOME/helm-backups}"
RETENTION_COUNT="${HELM_BACKUP_RETENTION:-30}"

mkdir -p "$BACKUP_DIR"

ts="$(date +%Y%m%d-%H%M%S)"
out="$BACKUP_DIR/helm-brain-$ts.sql"

echo "[$(date -Is)] Dumping public schema (data + structure) to $out..."
supabase db dump --data-only --schema public > "$out.data"
supabase db dump            --schema public > "$out.schema"

# Concatenate schema (DDL) before data (INSERTs). psql replays cleanly that way.
cat "$out.schema" "$out.data" > "$out"
rm "$out.data" "$out.schema"

size=$(wc -c < "$out")
echo "[$(date -Is)] Wrote $out ($size bytes)."

# Rotation: keep the most recent $RETENTION_COUNT dumps, delete older.
# Sort newest-first, skip the first N, delete the rest.
old_count=$(ls -1t "$BACKUP_DIR"/helm-brain-*.sql 2>/dev/null | tail -n +$((RETENTION_COUNT + 1)) | wc -l)
if [ "$old_count" -gt 0 ]; then
  echo "[$(date -Is)] Rotating: deleting $old_count dump(s) older than the last $RETENTION_COUNT."
  ls -1t "$BACKUP_DIR"/helm-brain-*.sql | tail -n +$((RETENTION_COUNT + 1)) | xargs rm --
fi

echo "[$(date -Is)] Backup complete."
