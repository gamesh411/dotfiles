# Delegation

Keep design, taste, architecture, ambiguous tradeoffs, and final acceptance with the capable lead model. Proactively offload bounded implementation and mechanical work when saved lead effort or parallel progress exceeds briefing, startup, and review cost. A direct tool call is usually better for a one-line lookup. Batch related small jobs instead of starting one agent per edit.

Use deterministic tools for arithmetic, parsing, and transformations with explicit rules. When a worker owns such a step, require it to run the tool and return checked output. Budget for the worker's inherited instructions and tools as well as its brief; a tiny assignment can still carry substantial context.

This is the user's standing preference across local agents. It authorizes using the installed Codex, Cursor, and Claude CLIs for subtasks within the current request. Keep the user's chosen lead model. Follow the current host's tool, permission, and data-access boundaries when starting another CLI.

## Choose the worker

1. Define a deliverable and a cheap way to check it. Give visual workers approved design decisions or a reference; keep new visual direction and editorial judgment with the lead.
2. Before a delegation batch, run `~/.local/bin/agent-capacity --json --task routine`, choosing `tiny`, `routine`, or `substantial` for the assignment. Reuse that result within the same batch for up to ten minutes. Refresh after a limit error or a substantial run. For one provider, add `--provider codex`, `cursor`, or `claude`. Read `routing.recommended` and its evidence; a null recommendation means no route has verified fresh capacity. Read provider status, model list, quota source, remaining windows, reset times, and observation timestamp before choosing a manual fallback.
3. Choose the least expensive available model likely to pass the checks. Prefer included subscription capacity over metered API usage. Treat the table as the user's routing preference, not a benchmark or guaranteed price ranking.

| Work | Preferred route |
| --- | --- |
| Extraction, classification, small repetitive edits, narrow checks | Codex Luna; batch tiny tasks |
| Routine implementation with explicit requirements | Cursor Grok Fast or Codex Terra, according to live availability and capacity |
| Larger implementation, debugging with several steps, substantial independent review | Latest available Codex Sol |
| Design, architecture, unclear requirements, difficult judgment | Capable lead model; use a capable peer when independent judgment is useful |
| A task demonstrably better suited to Claude, or another working pool is constrained | An appropriate available Claude model |

4. Use model identifiers returned by the installed client. Current examples are `gpt-6-luna`, `gpt-5.6-terra`, and `gpt-6.1-sol`; availability may change. The tested Cursor Grok Fast identifier is `cursor-grok-4.6-high-fast`; verify the Grok option in the live model list. Choose low or moderate reasoning for mechanical work instead of inheriting the lead's maximum setting. Codex workers use Standard service, `service_tier="default"`, unless latency justifies extra usage. Cursor's Grok Fast preference does not imply Codex Fast mode.

## Capacity is evidence

Compare the windows that actually apply to the chosen model. The smaller remaining allowance is the constraint when both a short and a weekly window apply. Keep separate pools separate, including Cursor Models versus Other Models. Reserve constrained capacity for the user's higher-value work and avoid launching a large batch near a limit. The helper uses a configurable 15% reserve as a local routing heuristic, not a provider rule or an estimate of how many tasks remain. It recommends only a suitable model with a fresh observation, a current reset window, and more than the reserve in every applicable window. It follows the task preferences above rather than treating percentages from different providers as comparable token budgets. It never launches a worker or changes the lead model.

`unknown`, missing windows, stale data, or an authentication failure never mean unlimited usage. Cursor app quota must match the CLI account before it can guide that CLI's route; a different or unverifiable account remains display-only. An unverified Claude model alias needs a manual availability check even when quota is known. A catalog entry alone does not prove model access. Prefer a working route with fresh capacity data; if no such route exists, a small bounded job may use an already authorized subscription while clearly treating quota as unknown. An authentication failure makes that route unavailable until repaired. Do not loop on login or model-access errors.

Probe results describe the current process environment. A sandbox may prevent access to a working host login. If permitted, retry the read-only probe through the host's normal approval flow; otherwise keep that route unavailable in this context.

The helper reads Codex limits through its CLI app-server, Claude through its verified native local usage interface, and Cursor through its first-party usage endpoint using the native session. Follow the provider notes in `~/.agents/DELEGATION-CLI.md` when a source is unavailable. A CLI login status or accumulated token cost is not remaining plan allowance. Do not spend an inference merely to ask a model for its own quota. Do not enable paid overages, purchase credits, redeem resets, or change billing to complete a delegation.

## Dispatch and accept

- Use native subagents when they provide the intended model with less overhead, and name that model on every spawn: an omitted model inherits the lead's, the most expensive route. Otherwise read `~/.agents/DELEGATION-CLI.md` for checked CLI recipes. Cross-CLI delegation is optional, not a quota to fill.
- Supply only the needed context: task, relevant files, constraints, owned output paths, acceptance checks, and a return format. Begin the assignment with `DELEGATED_WORKER: complete only this bounded task; do not spawn other agents.` Set `AGENT_DELEGATION_DEPTH=1` for shell workers. When the assignment starts with this marker or the environment variable equals `1`, execute it and return to the parent without further delegation.
- Use read-only access for investigation. For edits, assign disjoint files or an isolated worktree using the project's worktree workflow. Verify the child's actual sandbox and inherited hooks; the parent's sandbox does not automatically confine another process. Never use approval-bypass flags or broaden access to make delegation work.
- Set a time bound and one owner per file. Keep existing user edits intact. Workers report changed paths, checks run, results, and unresolved questions. External communication, publishing, or destructive actions stay subject to the original authorization.
- The lead inspects the result or diff, runs proportionate checks, and accepts or rejects it. Retry once with a clarified brief or escalate to a stronger model when the cheap worker misses the bar. Repeated supervision is a signal to do the work directly.
- For substantial batches, record provider/model, elapsed time, quota before/after when available, acceptance, and rework. Judge efficiency by time and quality of accepted work, not by worker count. Keep these notes with the task rather than filling permanent memory with per-call telemetry.
