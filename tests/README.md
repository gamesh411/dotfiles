# Agent setup checks

Run from the chezmoi source checkout:

```sh
python3 -B -m unittest discover -s tests -v
```

The tests execute the real chezmoi renderer and the generated Codex modifier, inspect the hook's emitted context, and exercise Claude quota against native cache fixtures and updater behavior through controlled fake executables.
They make no model requests and perform no package upgrades.
Chezmoi must be installed for the instruction-rendering checks.

After applying the source changes on a host with installation and network access:

1. Inspect `agent-tools-update --json`, then run `agent-tools-update --apply`.
2. Check updater output for declined, failed, or manual actions.
3. Run `agent-capacity --json --task routine` and inspect each provider's status.
4. Start fresh client sessions and verify their native instruction context includes the shared delegation preference once.
5. Open a Lavish artifact and exercise feedback polling from a session with localhost access.

Offline tests establish the generated instruction contract and executable behavior.
They do not establish that a live client loaded the deployed files, that a model will follow every instruction, that tools are current upstream, or that a branch was pushed.
