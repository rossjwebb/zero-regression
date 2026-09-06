# S1 Part B arm output slots

Three arms only: Cursor, Claude Code, Gemini.

- `cursor/` — executed. `arm.json` records the live replay-only
  oracle receipt. `oracle-receipt.json` is the probe output.
- `claude-code/` — executed. `arm.json` records the live replay-only
  oracle receipt. `oracle-receipt.json` is the probe output.
  `PROMPT.md` is the work order that was executed. This is the
  Claude Code arm slot, not a second Cursor arm.
- `gemini/` — `status=awaiting-external-run`. The paste-ready prompt
  is in `PROMPT.md` and on `arm.json`. It is not a result.

Shared probe: `run-arm-oracle.py`. It runs `oracle.py` and prints a
JSON receipt. It does not write `arm.json`.

There is no Codex slot. Codex is omitted on purpose.
