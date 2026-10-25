# AI Workflow Reference

## Daily Modes

### Interactive (default)
```sh
cd ~/myproject && kiro-cli chat
```
Model: auto (1.00x). Hands-on work -- design, debugging, exploration.

### Parallel dispatch (active, you're present)
```sh
cd ~/firstmate && kiro-cli chat
```
Talk to firstmate, it spawns crewmates in zellij tabs via treehouse worktrees.
You answer escalations, approve merges.

### Background unattended (you're away)
```sh
cd ~/myproject && gnhf --agent "acp:kiro-cli acp --trust-all-tools" "objective"
```
Long-running loop. Each iteration commits. Set `--max-iterations` or `--max-tokens` to cap spend.

---

## Critical Incantations

### Firstmate crewmate raw launch command
```
kiro-cli chat --trust-all-tools --no-interactive "$(cat __BRIEF__)"
```
Pass this as the harness arg to `bin/fm-spawn.sh`. The `__BRIEF__` placeholder gets substituted.

### gnhf with kiro-cli
```sh
gnhf --agent "acp:kiro-cli acp --trust-all-tools" "reduce test flakiness"
```

### Treehouse (instant worktree)
```sh
cd ~/myproject && treehouse       # drops into isolated worktree subshell
exit                              # returns worktree to pool
treehouse status                  # see all worktrees
```

---

## Firstmate Config (~/firstmate/config/)

| File | Value | Purpose |
|------|-------|---------|
| `backend` | `zellij` | Session provider for crewmate tabs |
| `crew-harness` | `claude` | Default adapter (override with raw cmd at spawn) |

To spawn with kiro-cli explicitly, firstmate passes the raw command as the third arg to fm-spawn.sh.

---

## Model Routing (from 2026-07-04 benchmark)

| Task type | Model | Credits |
|-----------|-------|---------|
| Creative Blender / spatial reasoning | auto (minimum), opus for hero | 1.00-2.20x |
| Code implementation, bug fixes | auto | 1.00x |
| Mechanical refactors, simple Q&A | haiku-4.5 | 0.40x |
| Long background loops (gnhf) | auto | 1.00x |
| **Avoid for creative/spatial** | haiku, minimax, qwen3 | fail the task |

Auto (1.00x) beat sonnet (1.30x) on cost AND quality for Blender work.
Everything below auto fails at creative tasks.

---

## Tool upkeep

Chezmoi installs missing workflow and AXI tools through `run_after_install-agentic-tools.sh` and `run_after_install-axi-clis.sh`.
Existing tools are upgraded explicitly with `agent-tools-update --apply`; run it without flags first to inspect the plan.
The updater follows each active binary's installation manager and requests the current release rather than storing a version table here.
It covers installed agent clients, AXI packages, workflow helpers, and a clean tracked firstmate checkout.
A failed update remains visible and exits nonzero; an installed binary alone is not evidence that it is current.
Inspect native updater output for declined or skipped updates, since some clients exit successfully even when an update was not applied.
Run updates from a host terminal with package-install and network access.

Bundled AXI skills follow their package updates.
Cursor discovers those skills through the symlinks maintained by `run_after_install-axi-clis.sh`.
Claude Code and Codex also receive AXI discovery through their existing startup hooks.
Shared personal skills remain version controlled in chezmoi.

The delegation hint is rendered from one chezmoi template into each client's native global instructions.
It is placed near the start so Claude, Codex, Cursor, and the other clients receive the same standing preference.
Capacity checks validate observed behavior and response data, never an exact CLI version.
Unknown quota allows a bounded manual worker choice when appropriate.

---

## Zellij Notes

- Firstmate creates session named `firstmate` with one tab per crewmate (`fm-<task-id>`)
- Attach to watch: `zellij attach firstmate`
- Dead EXITED sessions block new ones: `zellij delete-session firstmate --force`
- Peek at crewmate: `zellij -s firstmate action dump-screen --pane-id <id> --full --path /tmp/peek.txt`

---

## Preventing Rot

- **Regularly:** `agent-tools-update --apply`, then inspect any failed or manual update steps.
- **After updates:** run `agent-capacity --json --task routine` and verify the native instruction context in new client sessions.
- **Quarterly:** Re-run model benchmark (~/blender-ab-test/run-experiment.sh) -- model pricing and quality shift
- **When things break:** Check `bin/fm-bootstrap.sh` output for missing tools
