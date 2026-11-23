# Delegation

Keep design, taste, architecture, ambiguous tradeoffs, and final acceptance with the capable lead model. Proactively offload bounded implementation and mechanical work when saved lead effort or parallel progress exceeds briefing, startup, and review cost. A direct tool call is usually better for a one-line lookup. Batch related small jobs instead of starting one agent per edit.

Use deterministic tools for arithmetic, parsing, and transformations with explicit rules. When a worker owns such a step, require it to run the tool and return checked output. Budget for the worker's inherited instructions and tools as well as its brief; a tiny assignment can still carry substantial context.

This is the user's standing preference across local agents. It authorizes using the installed Codex, Cursor, and Claude CLIs for subtasks within the current request. Keep the user's chosen lead model. Follow the current host's tool, permission, and data-access boundaries when starting another CLI.

Apply this preference equally when the lead is Codex, Claude, Cursor, or another supported client.
Choose workers by their observed capabilities, authentication, and task fit.
CLI version numbers are diagnostic information, never an eligibility gate.
Unknown quota does not prohibit delegation: use a bounded authorized worker when appropriate and report that its remaining capacity is unknown.

## Choose the worker

1. Define a deliverable and a cheap way to check it. Give visual workers approved design decisions or a reference; keep new visual direction and editorial judgment with the lead.
2. Before a delegation batch, run `~/.local/bin/agent-capacity --json --task routine`, choosing `tiny`, `routine`, `substantial`, `review`, `research`, `computer_use`, or `aesthetic` for the assignment. Reuse that result within the same batch for up to ten minutes. Refresh after a limit error or a substantial run. For one provider, add `--provider codex`, `cursor`, or `claude`. Read `routing.recommended` and its evidence; a null recommendation means the helper cannot make an automatic choice, so choose a bounded worker manually from the available native agents or authenticated CLIs. Read provider status, model list, quota source, remaining windows, reset times, and observation timestamp before that choice.
3. Quality comes first: use the highest tier below that has a qualifying route. Code work prefers Claude Opus and Fable; QA, review, research, and the remaining work go to the other providers, and computer use goes to Codex. The user's second goal is to use every subscription before it resets, so within a tier prefer the pool furthest ahead of its own even spending pace, the one most likely to reset with allowance unused. `agent-capacity` reports this as `slack_percent` and already orders by it. Prefer included subscription capacity over metered API usage. Treat the table as the user's routing preference, not a benchmark or guaranteed price ranking.

| Work | Quality tiers, best first; "or" joins routes in one tier |
| --- | --- |
| Search, lookup, extraction, classification, small repetitive edits, narrow checks (`tiny`) | Codex Luna, Codex Terra or Cursor Grok Fast, then Claude Haiku; batch tiny tasks |
| Routine code with explicit requirements (`routine`) | Claude Opus or Fable, then Codex Terra, then Codex Luna, then Cursor Grok Fast or Claude Haiku |
| Diligent code work: larger implementation, debugging with several steps (`substantial`) | Claude Opus or Fable, then Codex Sol |
| Review and QA (`review`) | Latest available Codex Sol, then Claude Opus |
| Research: reading sources, gathering facts, comparisons (`research`) | Codex Sol, then Codex Terra, then Cursor Grok Fast or Claude Haiku |
| Computer use: driving desktop apps or a browser (`computer_use`) | Codex Sol, then Codex Terra; never another provider |
| Aesthetic execution from an approved direction: visual polish, layout, tone (`aesthetic`) | Claude Fable, then Codex Astra |
| Design, architecture, unclear requirements, difficult judgment | Capable lead model; use a capable peer when independent judgment is useful |

Cursor Grok Fast counts as Haiku-class: it ranks where Claude Haiku does and never handles review or substantial code work. The exception is tiny work, where it shares Codex's top tier so the Cursor subscription is not starved.
Prefer Claude Opus over Claude Sonnet; Sonnet is the last tier wherever Opus appears.

Claude routes never qualify automatically: the client lists no model catalog, and model-scoped limits such as Fable's are often stale even when the statusline record keeps the shared windows fresh. When a route in a higher tier than the recommendation is blocked only by missing measurements, the helper returns it as `preferred_unverified`. Missing measurements include stale or absent quota data and windows whose scope cannot be mapped to the model; a last known reading at or below the reserve with its reset still ahead, or a mismatched Cursor account, is a known limit and is never surfaced. Use that route unless a manual check shows it constrained; a lower tier is a fallback for a known limit, not for an unmeasured one.

4. Use model identifiers returned by the installed client. Current examples are `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.2-sol`, and `gpt-6.2-astra`; availability may change. Cursor workers use the newest Grok version in the live catalog at high effort with Fast serving (`grok-4.7-high-fast` as of 2026-11-23, verified by a real request); a new version takes over automatically and other Grok entries never qualify. Choose low or moderate reasoning for mechanical work instead of inheriting the lead's maximum setting. Codex workers use Standard service, `service_tier="default"`, unless latency justifies extra usage. Cursor's Grok Fast preference does not imply Codex Fast mode.

## Capacity is evidence

Compare the windows that actually apply to the chosen model. The smaller remaining allowance is the constraint when both a short and a weekly window apply. Keep separate pools separate, including Cursor Models versus Other Models. Reserve constrained capacity for the user's higher-value work and avoid launching a large batch near a limit. The helper uses a configurable 15% reserve as a local routing heuristic, not a provider rule or an estimate of how many tasks remain. It recommends only a suitable model with a fresh observation, a current reset window, and more than the reserve in every applicable window. It ranks by the quality tiers above, then within a tier by each pool's headroom against its own even pace: remaining percent minus the percent of the window still to run, using the tightest applicable window. It never treats raw percentages from different providers as comparable token budgets. Within a tier, a pool with measured slack ranks ahead of one whose window length is unknown or inconsistent, and listed order breaks the remaining ties. It never launches a worker or changes the lead model.

`unknown`, missing windows, stale data, or an authentication failure never mean unlimited usage. Cursor app quota must match the CLI account before it can guide that CLI's route; a different or unverifiable account remains display-only. An unverified Claude model alias needs a manual availability check even when quota is known. A catalog entry alone does not prove model access. Prefer a working route with fresh capacity data; if no such route exists, a small bounded job may use an already authorized subscription while clearly treating quota as unknown. An authentication failure makes that route unavailable until repaired. Do not loop on login or model-access errors.

Probe results describe the current process environment. A sandbox may prevent access to a working host login. If permitted, retry the read-only probe through the host's normal approval flow; otherwise keep that route unavailable in this context.

The helper reads Codex limits through its CLI app-server, Claude from its native account-bound usage cache without launching the CLI, and Cursor through its first-party usage endpoint using the native session.
It checks cache freshness, account identity, and response shape rather than an exact CLI-version allowlist.
An unsupported interface makes that quota source unknown; it does not make an otherwise usable worker ineligible.
Follow the provider notes in `~/.agents/DELEGATION-CLI.md` when a source is unavailable.
A CLI login status or accumulated token cost is not remaining plan allowance.
Do not spend an inference merely to ask a model for its own quota.
Do not enable paid overages, purchase credits, redeem resets, or change billing to complete a delegation.

## Dispatch and accept

- Use native subagents when they provide the intended model with less overhead, and name that model on every spawn: an omitted model inherits the lead's, the most expensive route. Otherwise read `~/.agents/DELEGATION-CLI.md` for checked CLI recipes. Cross-CLI delegation is optional, not a quota to fill.
- Supply only the needed context: task, relevant files, constraints, owned output paths, acceptance checks, and a return format. Begin the assignment with `DELEGATED_WORKER: complete only this bounded task; do not spawn other agents.` Set `AGENT_DELEGATION_DEPTH=1` for shell workers. When the assignment starts with this marker or the environment variable equals `1`, execute it and return to the parent without further delegation.
- Use read-only access for investigation. For edits, assign disjoint files or an isolated worktree using the project's worktree workflow. Verify the child's actual sandbox and inherited hooks; the parent's sandbox does not automatically confine another process. Never use approval-bypass flags or broaden access to make delegation work.
- Set a time bound and one owner per file. Keep existing user edits intact. Workers report changed paths, checks run, results, and unresolved questions. External communication, publishing, or destructive actions stay subject to the original authorization.
- The lead inspects the result or diff, runs proportionate checks, and accepts or rejects it. Retry once with a clarified brief or escalate to a stronger model when the cheap worker misses the bar. Repeated supervision is a signal to do the work directly.
- For substantial batches, record provider/model, elapsed time, quota before/after when available, acceptance, and rework. Judge efficiency by time and quality of accepted work, not by worker count. Keep these notes with the task rather than filling permanent memory with per-call telemetry.
