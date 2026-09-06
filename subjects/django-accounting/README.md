# django-accounting (S1)

Public-replication subject: [dulacp/django-accounting](https://github.com/dulacp/django-accounting), MIT, pinned at

**`2e61776a653e719a4c15578ab385603a6066c2b6`** (2 December 2017, `Remove old pip option --download-cache`).

The snapshot under `legacy/` is bit-identical to that commit for the files that were copied. The upstream MIT licence is `legacy/LICENSE`. Do not edit `legacy/` or `golden/`.

The subject is that pin. The files under `stubs/` are import shims so the pin can load on Python 3.12.3. They are not Django and they do not run ORM or SQL. Stage C adds a discrimination gate: replay plus known-bad probes that must fail. Org-level aggregates use a separate Django 5.2.17 pin under `orm/`. That is still not paper S1.

## Layout

- `legacy/` — frozen upstream slice (`Price`, sale-line totals, collected-profits calculator, and the import graph those modules need)
- `stubs/` — Django 1.7-era and Babel import shims only
- `oracle.py` — replay runner (27 traces; stdout unchanged)
- `ORACLE.md` — the claim in English (replay + rejects known-bad probes)
- `check-part-b.py` — Part B honesty gate; still requires the replay-only oracle stdout
- `check-discrimination.py` — Stage C gate: good pin passes; known-bad probes fail; golden echo fails invariants
- `discrimination/` — import-hook probes; does not edit `legacy/`
- `evidence/` — Part B historical thin-oracle record. Stage C posture is `evidence/discrimination/`. Stage D rewrite candidates versus that yardstick are `evidence/stage-d/`. Org-level ORM posture is `evidence/orm/`. No mutation score. Not paper S1.
- `check-stage-d.py` — Stage D honesty gate: good pin + discrimination still green; Cursor candidates evaluated; Claude Code and Gemini awaiting-external-run
- `orm/` — separate Django 5.2.17 pin + scaffold so org-level `turnover_*` / `debts_*` / `overdue_total` can issue real `SUM` SQL through the pin's manager QuerySets. The pin's `models.py` is not imported.
- `check-orm.py` — ORM honesty gate; fail-closed if Django is missing
- `golden/expected.json` — recorded trace outputs; a Generator must not read this

Declared slice for a later certification run: `legacy/accounting/libs/prices.py` and `legacy/accounting/apps/books/calculators.py` (174 executable lines). Sale-line totals live on the models in `legacy/accounting/apps/books/models.py` and are exercised by the oracle as in-memory Python. Django persistence, UI, people/connect/reports, migrations, templates, and static files stay in `unverified_scope`.

## Oracle claim

The oracle **replays recorded traces**. Stage C **rejects known-bad probes** that patch those same pin APIs. A match is not a proof of accounting correctness. See `ORACLE.md`. S1 is not a paper execution until the paper says so.

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

Stage C discrimination (not a score):

```bash
python3.12 subjects/django-accounting/check-discrimination.py
```

Good pin must still print the 27-trace OK line. Each known-bad probe must exit non-zero and name its mismatch case. A golden-echo stub that returns `expected.json` without calling the pin must fail the invariant gate. `known_bad_rejected=5` is a probe count, not a kill rate.

Part B (three arms, not a score) stays in `evidence/` as the Stage B historical thin-oracle record. Cursor, Claude Code, and Gemini are `status=executed` / `generators_run=true` with 27/0 receipts and `produced=false`. Codex is omitted on purpose. Domain correctness is out of scope. That three-arm comparison remains a Stage B thin-oracle reading — not “four clean generators” and not paper S1. Stage C posture is `evidence/discrimination/`. Stage D is a rewrite attempt against that Stage C yardstick (`evidence/stage-d/`); it is not paper S1.

```bash
python3.12 subjects/django-accounting/evidence/arms/run-arm-oracle.py
python3.12 subjects/django-accounting/check-part-b.py
python3.12 subjects/django-accounting/check-discrimination.py
python3.12 subjects/django-accounting/check-stage-d.py
python3.12 -m pytest tests/test_django_accounting_oracle.py tests/test_django_accounting_part_b.py tests/test_django_accounting_discrimination.py tests/test_django_accounting_stage_d.py tests/test_django_accounting_orm.py
```

`check-part-b.py` still requires stdout from the oracle to include `ORACLE OK pin=2e61776a653e719a4c15578ab385603a6066c2b6 cases=27 replay-only`. It stores no mutation score. It is not paper S1.
`check-discrimination.py` stores no mutation score either. `check-stage-d.py` re-evaluates produced Cursor rewrites against that yardstick and leaves Claude Code / Gemini awaiting-external-run. The org-level ORM path (`orm/`, `check-orm.py`) is a later scaffold: Django 5.2.17 + SQLite runs the pin's manager QuerySets as SQL; `models.py` stays blocked; the golden file stays at 27 traces. `paper_s1` stays unexecuted.

```bash
python3.12 -m pip install --require-hashes -r subjects/django-accounting/orm/requirements.lock
python3.12 subjects/django-accounting/check-orm.py
zero-regression certify subjects/django-accounting
```

`zr certify subjects/django-accounting` runs those same oracle, discrimination, Stage D, and ORM gates. It stores no mutation score and is not paper S1. The Django lock is required; a missing install is fail-closed.
