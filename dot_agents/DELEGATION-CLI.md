# CLI workers

Read `~/.agents/DELEGATION.md` first. Check installed `--help` when a recipe no longer matches the client. Use an argument array through a process API, or quote shell arguments. Put long prompts in files or stdin; never interpolate prompt text into shell code.

Give every worker the marker `DELEGATED_WORKER: complete only this bounded task; do not spawn other agents.` Run from the task's intended directory and provide an explicit output contract. Set a finite timeout with the calling tool or a process wrapper; collect the exit status and final result before claiming completion.

## Codex

Read capacity without starting a model turn:

```sh
~/.local/bin/agent-capacity --provider codex --json
```

Example read-only worker, with the brief already saved at `work/worker-brief.txt`:

```sh
AGENT_DELEGATION_DEPTH=1 codex exec \
  --model gpt-6-luna \
  -c 'model_reasoning_effort="low"' \
  -c 'service_tier="default"' \
  --sandbox read-only --ephemeral \
  --output-last-message work/worker-result.txt \
  - < work/worker-brief.txt
```

Use an available Terra or Sol identifier when the task warrants it. Add `--skip-git-repo-check` only for an intentional task outside a repository. For authorized edits, use `--sandbox workspace-write` from the assigned worktree; inspect inherited hooks before dispatch. If noninteractive approval is required, let the worker report the blocked action for the parent to handle. Never add a bypass flag.

The helper's Codex protocol is `initialize`, `initialized`, `account/rateLimits/read`, and `model/list` over `codex app-server` stdio.
It does not start Codex threads or model turns.
Limits are shared with other usage of the account; model listing is a catalog, not proof of entitlement.
On Windows the helper reads that stdio stream from a thread, because `select()` cannot wait on pipes.

## Cursor

Check `cursor-agent --help`, `cursor-agent status --format json`, and `cursor-agent models`. A successful status alone is insufficient if model discovery fails. `agent-capacity` reports the contradiction instead of assuming readiness.

For read-only work, use `cursor-agent --print --mode ask --sandbox enabled --model '<verified model identifier>' --output-format json` with the brief passed as one argument through a process API. A real request verified `cursor-grok-4.6-high-fast` on 2026-10-13. Refresh the model list before using the example later. For authorized edits, use the client's normal mode in the assigned worktree with sandboxing enabled and the host's permission constraints. Do not use `--force` or unattended approval overrides to fix a blocked run.

Workspace trust is separate from login and command permissions.
When Cursor reports `Workspace Trust Required`, add `--trust`: the user gave standing approval on 2026-10-22 to trust the directory a delegated task runs in.
This flag persists trust for every effective workspace directory, including additional roots; restrict the invocation to the task's own directory.
It does not replace `--sandbox enabled` or grant permission for commands.
`--model` also persists as the interactive default model in `~/.cursor/cli-config.json`, so every worker run changes the user's Cursor selection.
Run `chezmoi apply ~/.cursor/cli-config.json` after a batch to restore the tracked choice.

The helper reads the first-party `/api/usage-summary` endpoint with the native Cursor session; no model prompt, browser-cookie extraction, or token refresh is used. It keeps the server-reported Cursor Models and Other Models percentages separate. Aggregate monetary fields do not reconstruct either pool. Cursor Models currently covers the supported Grok 4.5/4.6/4.7 routes. Auto and Router can consume either pool and receive no automatic recommendation. The endpoint is internal and may change; a missing field stays unknown.

A fresh CLI status is matched in memory to the native session before its allowance can guide a CLI worker.
Mismatched accounts stop the request; unverifiable matches remain display-only.
On macOS, the adapter can use the signed-in Cursor app when the CLI stores its token only in Keychain.
A CLI-only macOS machine without an accessible native file/app session returns unknown.
Native Linux session files are supported.
On Windows the helper reads `%APPDATA%\Cursor\auth.json` first.
A signed-in desktop install also stores `cursorAuth/accessToken` in `%APPDATA%\Cursor\User\globalStorage\state.vscdb`, which is the fallback when that auth file is absent.
The auth-file path was live-checked on 2026-10-14 and matched the CLI account.
An API-key or alternate endpoint override is not treated as included personal quota.
HTTP 429 reports a retry delay when available; wait for that delay instead of repeatedly probing.

## Claude

Check `claude auth status --json` and `claude --help`. Select a model accepted by the installed client and account; aliases and availability change.

For a pure text transformation, `claude --print --model '<verified model>' --effort low --tools '' --strict-mcp-config --mcp-config '{"mcpServers":{}}' --no-session-persistence --output-format json` can read the brief from stdin. The tool flags disable built-in and MCP tools for that text-only job. For work requiring tools, grant only the tools and directories needed under the current permission policy. Use `--permission-prompts none` for headless runs only when unsupported approval requests should fail back to the parent. It does not grant approval.

For machine-checked output, add `--json-schema '<schema>'` and inspect `structured_output` in the response envelope. A text-only test verified the installed `haiku` alias on 2026-10-22 with Claude Code 2.1.304; that run reported `claude-haiku-5-5`. Do not assume an alias selects the newest generation.

Claude Code 2.1.286, 2.1.292, and 2.1.304 have a verified local `get_usage` control request.
The helper uses this native interface with tools, hooks, MCP servers, session persistence, and permission prompts disabled; it sends no model turn.
It checks the native account-bound cache timestamp so a silent stale fallback cannot masquerade as fresh quota.
This experimental control interface is enabled only for those verified versions; other versions return unknown until reverified.
2.1.292 was checked on Windows on 2026-10-14 and returned fresh subscription windows with no model turn.
2.1.304 was checked on macOS on 2026-10-22 with the same result.
Unavailable quota also returns unknown; never guess that an unverified `/usage` text prompt will stay local.
`--max-budget-usd` is not a subscription-allowance guard.

Use the minimum remaining allowance across the common session/week and applicable model-specific limits. The server's `is_active` flag chooses a headline display; it does not remove other applicable constraints. The native CLI does not advertise a machine-readable model catalog, so the helper exposes Claude aliases as manual choices whose availability must be checked separately.

## Routing and another machine

For quota-based advice, use `~/.local/bin/agent-capacity --json --task routine` (or `tiny` / `substantial`). Inspect `routing.recommended`, candidate reasons, and the observation timestamp. Advice never starts a worker. `--reserve-percent 15` is the default local reserve and can be adjusted for the batch. A partial result intentionally exits zero; JSON status fields determine readiness. Reuse fresh output for up to ten minutes; refresh after substantial work or a quota error, respecting server retry delays.

Chezmoi manages `~/.local/bin/agent-capacity`, its standard-library modules under `~/.local/lib/agent_capacity/`, both shared delegation documents, and the existing native instruction pointers.
Deploy the helper and modules together.
Paths resolve from the installed location and the current user's home.
Python 3 and the chosen provider CLI must be available on PATH.
The managed zsh setup adds `~/.local/bin`, or invoke its full path.
On Windows, PowerShell runs `agent-capacity.cmd` from that directory, which calls `python`.
Git Bash runs the extensionless script when `python3` is on PATH.
macOS is live-tested.
Linux paths are implemented but not live-tested.
Windows was live-tested on 2026-10-14: Codex app-server, Cursor usage, and Claude 2.1.292 quota all returned without a model turn.

Sign in to each provider locally on each machine. Credentials, usage snapshots, trust decisions, and native runtime caches stay on that machine; this helper adds no persistent cache or credentials to chezmoi. Cursor workspace trust remains a separate decision for the intended directory. Updating chezmoi source locally does not publish it to the Git remote.

## Sources checked 2026-10-13

- Installed Codex, Cursor Agent, and Claude Code help and read-only probes.
- [Codex app-server](https://learn.chatgpt.com/docs/app-server), [models](https://learn.chatgpt.com/docs/models), and [speed](https://learn.chatgpt.com/docs/agent-configuration/speed).
- [Claude statusline quota fields](https://code.claude.com/docs/en/statusline), [Claude model configuration](https://code.claude.com/docs/en/model-config), [Cursor headless mode](https://prod.cursor.com/docs/cli/headless), and [Cursor usage pools](https://prod.cursor.com/help/models-and-usage/usage-limits).
- [CodexBar Cursor provider](https://github.com/steipete/CodexBar/blob/main/docs/cursor.md) and its native-session usage implementation; checked against the installed client and live server response.
- Provider-specific quota limitations are also returned by `agent-capacity`. Refresh this reference when client capabilities change.
