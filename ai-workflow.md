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

## Tool Versions (installed 2026-07-04)

| Tool | Version | Install/Update |
|------|---------|---------------|
| treehouse | v2.0.0 | `curl -fsSL https://kunchenguid.github.io/treehouse/install.sh \| sh` |
| no-mistakes | v1.31.2 | `curl -fsSL https://raw.githubusercontent.com/kunchenguid/no-mistakes/main/docs/install.sh \| sh` |
| gnhf | 0.1.41 | `npm install -g gnhf` |
| firstmate | repo clone | `cd ~/firstmate && git pull` |
| gh-axi | npm | `npm install -g gh-axi` |
| lavish-axi | npm | `npm install -g lavish-axi` |
| chrome-devtools-axi | npm | `npm install -g chrome-devtools-axi` |
| tasks-axi | npm | `npm install -g tasks-axi` |

---

## Zellij Notes

- Firstmate creates session named `firstmate` with one tab per crewmate (`fm-<task-id>`)
- Attach to watch: `zellij attach firstmate`
- Dead EXITED sessions block new ones: `zellij delete-session firstmate --force`
- Peek at crewmate: `zellij -s firstmate action dump-screen --pane-id <id> --full --path /tmp/peek.txt`

---

## Preventing Rot

- **Monthly:** `npm update -g gnhf gh-axi lavish-axi chrome-devtools-axi tasks-axi`
- **Monthly:** `cd ~/firstmate && git pull` (check AGENTS.md for breaking changes)
- **Quarterly:** Re-run model benchmark (~/blender-ab-test/run-experiment.sh) -- model pricing and quality shift
- **When things break:** Check `bin/fm-bootstrap.sh` output for missing tools
