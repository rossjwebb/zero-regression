# S1 Part B arm output slots

Three arms only: Cursor, Claude Code, Gemini.

- `cursor/` — executed. `arm.json` records the live replay-only
  oracle receipt. `oracle-receipt.json` is the probe output.
- `claude-code/` — executed. `arm.json` records the live replay-only
  oracle receipt from `run-arm-oracle.py` on Python 3.12.3.
  `oracle-receipt.json` is the probe output. `PROMPT.md` is the
  work order that was packaged. This Cursor cloud agent is the git
  vehicle only: not a second Cursor arm and not a Claude · Max
  chat run.
- `gemini/` — executed. `arm.json` records the CoS-run replay-only
  oracle receipt attested by Gemini. `oracle-receipt.json` is that
  receipt. `PROMPT.md` remains as the historical work order.

Each arm has `candidate_artefacts.produced=false`. Each receipt is
27 matches / 0 mismatches. That is a thin-oracle replay, not paper
S1.

Shared probe: `run-arm-oracle.py`. It runs `oracle.py` and prints a
JSON receipt. It does not write `arm.json`.

There is no Codex slot. Codex is omitted on purpose.
