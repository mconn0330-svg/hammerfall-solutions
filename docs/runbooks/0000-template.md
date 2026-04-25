# Runbook NNNN — Title (problem statement, not solution)

**Status:** Active | Stale | Superseded by Runbook NNNN
**Created:** YYYY-MM-DD
**Last verified:** YYYY-MM-DD
**Owner:** (name / role)

## Symptom

What does the failure look like from the outside? Be precise — the next person reading this is probably stressed and pattern-matching against this section.

- Observable signal 1 (e.g., `/health` returns 503, dashboard alert fires)
- Observable signal 2

## Diagnosis

How do you confirm this is the failure mode this runbook covers (vs. a similar-looking but different one)? Include the specific commands, log queries, or dashboard checks.

```bash
# example diagnostic command
```

Expected output if this is indeed the issue: …

## Fix

Step-by-step recovery actions. Include exact commands. Note any irreversible steps explicitly.

1. …
2. …
3. …

**Verification:** how do you know the fix worked? (Specific signal that should clear.)

## Root cause

Why does this happen? Link to the relevant ADRs, code, or design notes that explain the underlying design choice or limitation. If this is a known-acceptable trade-off, say so. If it's a bug, link to the issue.

- Related code: …
- Related ADRs: …
- Related findings: `docs/stage1/Post_T1_Findings.md` Finding #NNN (if any)

## Prevention

What would prevent this from happening again? (E.g., monitoring, an additional guardrail, a code change.) If prevention is queued as future work, link to the task or finding. If it is accepted-as-is, say why.

---

*Maintenance: Re-verify this runbook after any change to the underlying system. Update the "Last verified" date when re-tested.*
