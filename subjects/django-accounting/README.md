# django-accounting (S1)

Public-replication subject: [dulacp/django-accounting](https://github.com/dulacp/django-accounting), MIT, pinned at

**`2e61776a653e719a4c15578ab385603a6066c2b6`** (2 December 2017, `Remove old pip option --download-cache`).

The snapshot under `legacy/` is bit-identical to that commit for the files that were copied. The upstream MIT licence is `legacy/LICENSE`. Do not edit `legacy/` or `golden/`.

The subject is that pin. The files under `stubs/` are import shims so the pin can load on Python 3.12.3. They are not Django and they do not run ORM or SQL.

## Layout

- `legacy/` — frozen upstream slice (`Price`, sale-line totals, collected-profits calculator, and the import graph those modules need)
- `stubs/` — Django 1.7-era and Babel import shims only
- `oracle.py` — replay runner
- `ORACLE.md` — the claim in English
- `check-part-b.py` — Part B honesty gate; still requires the replay-only oracle stdout
- `evidence/` — Part B Stage B: Cursor arm executed against the replay-only oracle; Claude Code and Gemini awaiting external run. No mutation score. Codex omitted. Not paper S1. See `evidence/EVIDENCE.md`.
- `golden/expected.json` — recorded trace outputs; a Generator must not read this

Declared slice for a later certification run: `legacy/accounting/libs/prices.py` and `legacy/accounting/apps/books/calculators.py` (174 executable lines). Sale-line totals live on the models in `legacy/accounting/apps/books/models.py` and are exercised by the oracle as in-memory Python. Django persistence, UI, people/connect/reports, migrations, templates, and static files stay in `unverified_scope`.

## Oracle claim

The oracle **replays recorded traces**. A match is not a proof of accounting correctness. See `ORACLE.md`. S1 is not a paper execution until this pull request is merged and the paper says so.

## How to run the oracle

From the repository root, with Python 3.12.3:

```bash
python3.12 subjects/django-accounting/oracle.py
```

Stdout must be exactly:

```
ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only
```

`cases=19` fails. CI on this branch runs that same command and does not skip. A match is a replay, not paper S1. `--write` regenerates the golden file and is not part of ordinary use.

Part B Stage B (three arms, not a score) is in `evidence/`. Cursor is `status=executed` / `generators_run=true` with a live oracle receipt (27 matches / 0 mismatches). Claude Code and Gemini are `status=awaiting-external-run` / `generators_run=false` with paste-ready prompts in `evidence/arms/*/PROMPT.md`. Codex is omitted on purpose. Domain correctness is out of scope. Cursor’s zero-mismatch replay means the oracle is too thin to discriminate — not “four clean generators”.

```bash
python3.12 subjects/django-accounting/evidence/arms/run-arm-oracle.py
python3.12 subjects/django-accounting/check-part-b.py
python3.12 -m pytest tests/test_django_accounting_oracle.py tests/test_django_accounting_part_b.py
```

`check-part-b.py` still requires stdout from the oracle to include `ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only`. It stores no mutation score. It is not paper S1.
