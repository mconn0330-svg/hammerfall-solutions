# Runbook 0004 — Git push hangs in non-interactive shell (Antigravity, Claude Code)

**Status:** Active
**Created:** 2026-04-26
**Last verified:** 2026-04-26
**Owner:** Maxwell McConnell

## Symptom

`git push` to a GitHub HTTPS remote hangs indefinitely with no output, no error, no exit. The same command run in a normal interactive terminal (Windows Terminal, Git Bash, VS Code integrated terminal) completes immediately.

- Push command appears to start, then no progress is shown
- No prompt for credentials, no error message
- Process must be killed manually (Ctrl-C or terminate from outside)
- Command completes normally when re-run in an interactive shell

## Diagnosis

Confirm the hang is the credential-prompt issue (not network or repo-side):

```bash
# Check whether GITHUB_TOKEN is set in the current environment
echo "GITHUB_TOKEN length: ${#GITHUB_TOKEN}"
```

If `GITHUB_TOKEN` is set **and** the surface is a non-interactive shell (Antigravity, Claude Code, any agent runner without a TTY), this runbook applies.

## Fix

Use the inline-token URL form so Git Credential Manager (GCM) is bypassed entirely:

```powershell
$token = $env:GITHUB_TOKEN
git push "https://$token@github.com/mconn0330-svg/hammerfall-solutions.git" main
```

For other repos, swap the URL for the appropriate GitHub repo path. For non-default branches, swap `main` for the branch name.

Bash equivalent (Git Bash, WSL):

```bash
git push "https://${GITHUB_TOKEN}@github.com/mconn0330-svg/hammerfall-solutions.git" main
```

**Verification:** the push completes within a few seconds and prints the usual `To https://github.com/...` confirmation lines.

## Root cause

`GITHUB_TOKEN` set as a shell environment variable causes Git Credential Manager (GCM) to intercept all HTTPS pushes and validate the token interactively. In a non-interactive shell (no TTY), GCM cannot surface its prompt and silently waits forever.

Inline-token URLs bypass GCM because the credential is embedded in the URL itself — Git uses it directly without consulting any helper.

- Related issue: [git-credential-manager#765 — non-interactive hang](https://github.com/git-ecosystem/git-credential-manager/issues/765) (illustrative; check upstream for current status)

## Prevention

Long-term: configure GCM to skip credential validation in non-interactive contexts (`credential.helper` = `""` for affected remotes) or migrate to SSH for agent-driven pushes. Both are larger changes; the inline-token workaround above is the operational fix today.

If you remove `GITHUB_TOKEN` from your global environment (e.g., to fix the related "stale token" issue documented in [docs/onboarding.md](../onboarding.md)), the GCM hang stops occurring because GCM no longer activates without credentials present — but tools that legitimately need a GitHub token (gh CLI, scripts) lose access. The right fix depends on which symptom matters more day-to-day.

---

_Maintenance: Re-verify this runbook after any change to the underlying system. Update the "Last verified" date when re-tested._
