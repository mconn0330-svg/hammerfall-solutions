#!/usr/bin/env python3
"""
T0.A9 — Migration reversibility policy enforcer.

Walks supabase/migrations/ and verifies each file complies with ADR-002:

  Class 1 (reversible)        — DROP / RENAME / lossy TYPE change → must
                                include a `-- DOWN:` comment block at the
                                end of the file containing the rollback SQL.
  Class 2 (forward-only)      — CREATE TABLE / INDEX / POLICY / FUNCTION,
                                ADD COLUMN with default — declare class in
                                header, no DOWN block needed.
  Class 3 (irreversible)      — destructive change with no clean rollback
                                — `-- IRREVERSIBLE: restore from backup ...`
                                in the DOWN block, plus snapshot-policy
                                sentence in the header.

Usage:
  python3 scripts/check_migration_reversibility.py [migrations_dir]

Default migrations_dir is supabase/migrations/.

Exits non-zero if any new migration violates the policy. Existing
pre-policy migrations (before T0.A9 landed) are grandfathered: the
check only complains about a missing class declaration, not missing
DOWN blocks, so the historical 9 files don't fail the check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Migrations whose timestamp is <= this cutoff are pre-T0.A9 and grandfathered.
# Any new migration after this date MUST declare a reversibility class.
GRANDFATHER_CUTOFF = "20260425000000"

# Destructive SQL keywords that require a Class-1 DOWN block.
# Conservative regexes — surface false positives rather than miss real ones.
# Comments and strings inside SQL aren't excluded; if a DOWN block contains
# a `DROP` keyword in its commented-out SQL, that's fine because we strip
# `-- DOWN:` ... before the keyword scan (see _strip_down_block).
DESTRUCTIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("DROP TABLE", re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE)),
    ("DROP COLUMN", re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE)),
    ("DROP INDEX", re.compile(r"\bDROP\s+INDEX\b", re.IGNORECASE)),
    ("DROP CONSTRAINT", re.compile(r"\bDROP\s+CONSTRAINT\b", re.IGNORECASE)),
    ("DROP TYPE", re.compile(r"\bDROP\s+TYPE\b", re.IGNORECASE)),
    ("DROP POLICY", re.compile(r"\bDROP\s+POLICY\b", re.IGNORECASE)),
    ("DROP FUNCTION", re.compile(r"\bDROP\s+FUNCTION\b", re.IGNORECASE)),
    ("RENAME", re.compile(r"\bALTER\s+(TABLE|COLUMN|INDEX)\b.*\bRENAME\b", re.IGNORECASE)),
    ("ALTER COLUMN ... TYPE", re.compile(r"\bALTER\s+COLUMN\b.*\bTYPE\b", re.IGNORECASE)),
    ("TRUNCATE", re.compile(r"\bTRUNCATE\b", re.IGNORECASE)),
]

CLASS_HEADER = re.compile(r"--\s*Reversibility:\s*Class\s*(1|2|3)\b", re.IGNORECASE)
DOWN_BLOCK = re.compile(r"--\s*DOWN:", re.IGNORECASE)
IRREVERSIBLE_MARKER = re.compile(r"--\s*IRREVERSIBLE:", re.IGNORECASE)
TIMESTAMP_PREFIX = re.compile(r"^(\d{14})_")


def _strip_down_block(content: str) -> str:
    """Return content with the trailing DOWN comment block removed.
    The DOWN block contains commented-out SQL like `-- DROP TABLE foo;`
    which would otherwise trip the destructive-pattern scan."""
    match = DOWN_BLOCK.search(content)
    if not match:
        return content
    return content[: match.start()]


def _check_one(path: Path) -> list[str]:
    """Return list of policy violations for `path`. Empty list = compliant."""
    violations: list[str] = []
    name = path.name
    timestamp_match = TIMESTAMP_PREFIX.match(name)
    if not timestamp_match:
        violations.append(f"{name}: filename is not <YYYYMMDDHHMMSS>_<slug>.sql")
        return violations

    is_grandfathered = timestamp_match.group(1) <= GRANDFATHER_CUTOFF

    content = path.read_text(encoding="utf-8")

    # Class declaration in header — required for new migrations.
    class_match = CLASS_HEADER.search(content)
    if not class_match:
        if not is_grandfathered:
            violations.append(
                f"{name}: missing `-- Reversibility: Class 1|2|3` header (per ADR-002). "
                "Pre-cutoff migrations are exempt; new ones must declare."
            )
        return violations

    declared_class = class_match.group(1)
    body = _strip_down_block(content)
    triggered = [keyword for keyword, pattern in DESTRUCTIVE_PATTERNS if pattern.search(body)]

    if declared_class == "1":
        # Class 1 must contain a DOWN block.
        if not DOWN_BLOCK.search(content):
            violations.append(
                f"{name}: declared Class 1 but no `-- DOWN:` block found. "
                "Add the rollback SQL as commented lines after `-- DOWN:`."
            )
    elif declared_class == "2":
        # Class 2 must NOT contain destructive operations.
        if triggered:
            violations.append(
                f"{name}: declared Class 2 but contains destructive op(s) "
                f"({', '.join(triggered)}). Re-declare as Class 1 with a DOWN block, "
                "or Class 3 if irreversible."
            )
    elif declared_class == "3":
        # Class 3 must contain the IRREVERSIBLE marker.
        if not IRREVERSIBLE_MARKER.search(content):
            violations.append(
                f"{name}: declared Class 3 but missing `-- IRREVERSIBLE: ...` marker."
            )

    # Independent of declared class: if destructive ops are present, demand
    # the migration be Class 1 or Class 3, not Class 2.
    # (Already covered by Class 2 check above; this is the catch-all if
    # something declares an unexpected class string.)
    if triggered and declared_class not in ("1", "3"):
        violations.append(
            f"{name}: contains destructive op(s) ({', '.join(triggered)}) "
            f"but declared Class {declared_class}. Must be Class 1 (with DOWN) or Class 3."
        )

    return violations


def main(argv: list[str]) -> int:
    migrations_dir = Path(argv[1]) if len(argv) > 1 else Path("supabase/migrations")
    if not migrations_dir.is_dir():
        print(f"error: {migrations_dir} is not a directory", file=sys.stderr)
        return 2

    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        print(f"no migration files in {migrations_dir}")
        return 0

    all_violations: list[str] = []
    for path in files:
        all_violations.extend(_check_one(path))

    if all_violations:
        print(f"Migration reversibility check FAILED ({len(all_violations)} violation(s)):\n")
        for v in all_violations:
            print(f"  - {v}")
        print(
            "\nSee docs/adr/0002-migration-reversibility-policy.md for the policy."
        )
        return 1

    print(f"Migration reversibility check PASSED ({len(files)} file(s) scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
