# S1 Part B arm output slots

Three arms only: Cursor, Claude Code, Gemini.

- `cursor/` — executed. `arm.json` records the live replay-only
  oracle receipt. `oracle-receipt.json` is the probe output.
- `claude-code/` and `gemini/` — `status=awaiting-external-run`.
  Paste-ready prompts are in `PROMPT.md` and on `arm.json`. They
  are not results.

Shared probe: `run-arm-oracle.py`. It runs `oracle.py` and prints a
JSON receipt. It does not write `arm.json`.

There is no Codex slot. Codex is omitted on purpose.
