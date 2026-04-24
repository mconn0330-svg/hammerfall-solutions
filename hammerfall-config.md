# Hammerfall Config

Global configuration read by Helm and the runtime service at session start.
Maintained by Core Helm. Update this file when account details change.

> **SECURITY RULE:** This file never contains secret values — only environment variable
> names. Actual secrets live in your shell profile (`~/.zshrc`) and GitHub Secrets.
> This file is safe to commit.

---

## Identity

```
hammerfall_github_user: mconn0330-svg
hammerfall_github_org: mconn0330-svg
```

---

## Supabase

```
supabase_org_id: nninqwpylkzcpffccgvq
supabase_region: us-east-1
supabase_brain_project_ref: zlcvrfmbtpxlhsqosdqf
```

---
## Supabase Brain (Memory Store)
supabase_brain_project_ref: zlcvrfmbtpxlhsqosdqf
supabase_brain_url: https://zlcvrfmbtpxlhsqosdqf.supabase.co
supabase_brain_service_key_env: SUPABASE_BRAIN_SERVICE_KEY
supabase_brain_access_token_env: SUPABASE_ACCESS_TOKEN

## Memory Architecture

active_tier: T1
frame_offload_interval: 10        # Interval trigger: Projectionist offloads oldest warm frame every N turns
warm_queue_max_frames: 20         # Batch trigger: fires at exactly this count, takes priority over interval
frame_offload_conservative: true  # When true, interval trigger fires at 80% of interval

# Tier capability requirements:
# T1 — Any capable LLM with tool-use. Claude Code current implementation.
# T2 — T1 + persistent scheduler (cron or equivalent)
# T3 — Thor (RTX 6000 Ada, 85GB VRAM, MIG partitioning)
#       hosts Helm Prime, Projectionist, Archivist, Contemplator concurrently.
#
# active_tier is a config stub at T1. Maxwell is sole user.
# BA7 will wire Projectionist and Archivist to local Ollama models —
# active_tier remains T1, model substitution is transparent to this config.

---

## Session Management

session_watchdog_inactivity_minutes: 30

## GitHub

```
github_token_env: GITHUB_TOKEN
```

*Note: `gh auth login` handles most GitHub CLI operations. This token is used
for any programmatic API calls Helm needs to make (PR checks, file reads, etc.)*

### ⚠️ Known Issue — Git Push Hangs in Non-Interactive Shell (Antigravity / Claude Code)

**Root cause:** `GITHUB_TOKEN` is set as a shell environment variable, which causes Git Credential Manager (GCM) to intercept HTTPS pushes. In a non-interactive PowerShell session (Antigravity, Claude Code), GCM has no TTY to surface its authentication prompt and hangs silently.

**Standard push (works in a normal interactive terminal):**
```bash
git push origin main
```

**Fallback push (use when the above hangs in Antigravity or Claude Code):**
```powershell
$token = $env:GITHUB_TOKEN; git push "https://$token@github.com/mconn0330-svg/hammerfall-solutions.git" main
```
For project repos, replace the URL with the appropriate GitHub repo path.

---

## Vercel

```
vercel_team_id: team_8mxY3FJcuwUNbthWXlyPaIP7
vercel_token_env: VERCEL_TOKEN
```

*Vercel links automatically on first merge to main via bootstrap.*

---

## Replit

```
replit_team: mconn0330
replit_token_env: REPLIT_TOKEN
```

*Replit uses GitHub OAuth — token used for any direct Replit API calls if needed.*

---

## EAS / Expo (mobile projects)

```
eas_account: Bandit0330
eas_token_env: EXPO_TOKEN
```

*Only used when a project includes a mobile component. Bootstrap checks for
this when scaffolding mobile projects.*

---

## Scheduled Sync

```
sync_schedule_morning: 07:00
sync_schedule_midday: 12:00
sync_schedule_evening: 18:00
```

*These values are the canonical schedule times. If you change them here,
update the /schedule tasks in Claude Code to match.*

---

## Shell Profile Reference

The following env vars must be set in your shell profile (`~/.zshrc` on Mac/Linux,
or as User environment variables on Windows). Add these once and they persist:

```bash
export GITHUB_TOKEN=ghp_your-github-pat-here
export VERCEL_TOKEN=your-vercel-token-here
export REPLIT_TOKEN=your-replit-token-here
export EXPO_TOKEN=your-expo-token-here
export OPENAI_API_KEY=sk-your-openai-key-here   # Required for semantic memory (S1-BA2+)
```

*Note: No Supabase password env var needed. Bootstrap generates a unique
cryptographically random password per project automatically.*

After editing `~/.zshrc`, run: `source ~/.zshrc` to load immediately.

---

*Maintained by Core Helm · hammerfall-solutions/hammerfall-config.md*
