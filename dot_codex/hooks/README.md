# Codex lifecycle hooks

Managed by chezmoi. The AXI SessionStart hooks match Claude Code: gh-axi and
chrome-devtools-axi announce themselves, lavish-axi gets a one-line pointer.
Open Brain recall reuses `~/projects/ai-brain/hooks/session-start-recall.ts` on
startup, resume and clear, excluding compaction. The Python launcher calls the
repo's tsx through Node, including on Windows.

SessionEnd detaches `mine-codex.mjs` within Codex's three-second timeout. It reads
Codex JSONL messages and reuses ai-brain's extractor, capture API and ledger.
Records use corpus `codex`, source `codex-tail`, and trust `agent_inferred`.
Sessions with fewer than six messages and already-mined sessions are skipped.
Errors go to `~/.config/open-brain/codex-tail.log`. Unlike Claude Code, there is
currently no scheduled sweep for missed Codex SessionEnd events. A missing or
unsupported transcript cannot be mined; Codex's transcript format is not stable.

Dependencies: Python 3, Node on PATH, and the existing ai-brain checkout with its
npm dependencies and `~/.config/open-brain/.env`. No credentials are tracked here.
Hooks are enabled by default in Codex. After applying on a new machine, review
and trust the hooks through `/hooks`; trust is machine-local Codex state and is
not copied by chezmoi.

Reference: https://learn.chatgpt.com/docs/hooks
