# Runbook 0001 — Helm API token rotation

**Status:** Active
**Created:** 2026-04-25
**Last verified:** 2026-04-25
**Owner:** Maxwell McConnell

## Symptom

You need to rotate `HELM_API_TOKEN` because:

- The current token may have leaked (logged, screen-shared, AV-quarantined into PATH, committed to a draft PR, etc.).
- The token has been in use long enough that scheduled rotation is appropriate (no fixed cadence at T1 — rotate when there's reason).
- Stage 2 user auth is landing and the static token is being retired.

This is a planned procedure, not a failure-recovery runbook — but it lives here because the failure-mode shape (incident → confirm → fix → prevent recurrence) maps cleanly onto rotation.

## Diagnosis

Confirm rotation is the right action vs a different problem:

```bash
# Is the runtime healthy?
curl -fsS http://localhost:8000/health
# 200 → service is up; rotation is the work.
# 401 on /health is impossible (it's exempt). 503 → fix /health first, not rotation.

# Is there an active leak signal?
# - Search shell rc files for raw token strings:
grep -rn "HELM_API_TOKEN" ~/.bashrc ~/.bash_profile ~/.zshrc ~/.profile 2>/dev/null
# - Search shell history (don't use the literal token; use a 6-char prefix):
history | grep "Bearer ${HELM_API_TOKEN:0:6}" 2>/dev/null
```

If `/health` is failing, fix that first (different runbook). If env-var leakage is the trigger, treat the old token as fully compromised and rotate immediately — do not "wait for a quiet moment."

## Fix

1. **Generate a fresh token** (32 bytes, hex-encoded):

   ```bash
   openssl rand -hex 32
   ```

   Save it somewhere readable but not committed (a password manager, `.env.local`, etc.).

2. **Update `HELM_API_TOKEN` in your environment.** Pick the right scope:
   - **Local dev (host shell):** edit `.env` (or however you set env vars) and reload your shell.
   - **Local Docker compose:** edit `.env` so `docker-compose up` picks the new value on next start.
   - **Render / future deploy:** update the secret in the platform UI; trigger a redeploy.
   - **helm-ui / frontend (T3.4 onward):** update `VITE_HELM_API_TOKEN` in the UI's env and rebuild.

3. **Restart the runtime** so the new value is loaded:

   ```bash
   docker-compose restart helm-runtime
   ```

4. **Verify the new token works and the old one is dead**:

   ```bash
   # New token → 200
   curl -fsS -H "Authorization: Bearer $NEW_TOKEN" \
     http://localhost:8000/config/agents

   # Old token → 401
   curl -s -o /dev/null -w "%{http_code}\n" \
     -H "Authorization: Bearer $OLD_TOKEN" \
     http://localhost:8000/config/agents
   # Expected: 401
   ```

5. **Update any callers** that hold the old token (Claude Code session config, scripts, etc.).

**Verification:** `curl /config/agents` with the new token returns 200; with the old token returns 401. `/health` continues to return 200 with no auth.

**Irreversible:** None. If step 4 fails (new token doesn't work), revert by editing the env back to the previous value and restarting. Keep the old value handy until verification passes.

## Root cause

There is no automated rotation at T1. Token lifecycle is manual by design — the threat model is "noise on the box," not a sophisticated attacker, and per-deploy rotation tooling is over-engineering for a single-dev project.

- Related code: `services/helm-runtime/auth.py` (`require_token` dependency)
- Related ADRs: none yet — token rotation tooling is queued as Stage 2 work alongside user auth
- Related findings: none

## Prevention

What would reduce rotation frequency:

- **Don't put the token in `PATH` or anywhere it can be echoed.** A malformed shell rc that injected a key into `PATH` was the precipitating event for OpenAI key rotation earlier in T0; same failure mode applies here.
- **Don't commit the token to any repo, even draft.** `.env` is in `.gitignore` (T0.A7) — keep it that way.
- **Don't paste the token into chat tools, screenshots, or remote screen-share.** Any of those is a leak.

What would automate this:

- Per-deploy rotation (T4.11 cuts a fresh token on every deploy and bakes into the UI build) — deferred per architect review (over-engineering at T1).
- Vault-issued short-lived tokens — Stage 2 work alongside user auth.

---

_Maintenance: Re-verify this runbook after any change to `auth.py` or the deployment env-var pipeline. Update "Last verified" date when re-tested._
