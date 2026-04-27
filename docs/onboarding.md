# Onboarding

Setup reference for the local environment Hammerfall expects. This is contributor-environment guidance, not runtime configuration — runtime config lives in [`services/helm-runtime/config.yaml`](../services/helm-runtime/config.yaml) and is read at service startup.

> **Security note:** This file lists environment variable _names_, never values. Actual secrets live in your shell profile (`~/.zshrc` on Mac/Linux, User environment variables on Windows) and GitHub Secrets. This file is safe to commit.

---

## Required environment variables

The following must be set in your shell profile (`~/.zshrc` on Mac/Linux, or as User environment variables on Windows). Add once and they persist:

```bash
export GITHUB_TOKEN=ghp_your-github-pat-here              # GitHub PAT — repo + workflow + read:org + gist
export OPENAI_API_KEY=sk-your-openai-key-here             # Required for semantic memory (embeddings)
export SUPABASE_BRAIN_SERVICE_KEY=your-service-role-key   # Supabase brain — service role key
export SUPABASE_BRAIN_URL=https://<ref>.supabase.co       # Supabase brain — project URL
export SUPABASE_ACCESS_TOKEN=your-management-token        # Supabase CLI — `supabase link` / `supabase db push`
```

Optional, only if working on the relevant external surface:

```bash
export VERCEL_TOKEN=your-vercel-token-here                # Vercel deployments (web surfaces)
export REPLIT_TOKEN=your-replit-token-here                # Replit deployments
export EXPO_TOKEN=your-expo-token-here                    # EAS / Expo (mobile projects)
export ANTHROPIC_API_KEY=your-anthropic-key               # Claude API (helm-runtime helm_prime)
```

After editing your shell profile, run `source ~/.zshrc` (Mac/Linux) or restart the terminal (Windows) so the values load.

> **No Supabase password env var needed.** Bootstrap generates a unique cryptographically random password per project automatically.

---

## External service identities

When wiring a new project to one of these services, use the identifier below so deploys land in the right scope without prompting:

| Service    | Identifier                               | Notes                                                             |
| ---------- | ---------------------------------------- | ----------------------------------------------------------------- |
| GitHub     | user/org `mconn0330-svg`                 | All Hammerfall repos live under this account                      |
| Supabase   | brain project ref `zlcvrfmbtpxlhsqosdqf` | `https://zlcvrfmbtpxlhsqosdqf.supabase.co` (us-east-1)            |
| Vercel     | team id `team_8mxY3FJcuwUNbthWXlyPaIP7`  | Use as `--scope` arg when running `vercel link` / `vercel deploy` |
| Replit     | team `mconn0330`                         |                                                                   |
| EAS / Expo | account `Bandit0330`                     | Mobile projects only                                              |

---

## Known operational issues

- **Git push hangs in non-interactive shells (Antigravity, Claude Code).** See [docs/runbooks/0004-git-push-hangs.md](runbooks/0004-git-push-hangs.md) for the inline-token workaround. This is the most common surprise for first-time agent-driven pushes.

For a full list of known failure modes with diagnosis + fix steps, see [docs/runbooks/](runbooks/).

---

## Where to look next

- **[AGENTS.md](../AGENTS.md)** — operating contract for any agent (or human) working in this repo
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — commit conventions, branching, review gates
- **[V2 launch spec](stage1/Helm_T1_Launch_Spec_V2.md)** — canonical for all T1 work
