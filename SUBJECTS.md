# Public-replication subject protocol

Each selected subject must be Python, permissively licensed, deterministic and green under its pinned checkout, and have no network dependency in its test suite. The certification scope must contain 150–600 executable source lines. Larger repositories are admissible only when the tested, configured source slice is independently runnable and its boundary is declared in `unverified_scope`.

Before selection, record the commit SHA, licence text, installation command, test command, source/test paths, offline-test evidence, and LOC count in the subject’s `zero-regression.toml` and `evidence/` folder. Do not certify a moving default branch. A green test suite is a precondition, not a result.

## Public-replication shortlist

| Public repository | Candidate slice | Fit note |
|---|---|---|
| [py-moneyed](https://github.com/py-moneyed/py-moneyed) | `src/moneyed/classes.py` plus directly exercised currency helpers | BSD-3-Clause money and currency primitives; a bounded arithmetic slice is appropriate for the target size. |
| [stockholm](https://github.com/kalaspuff/stockholm) | one `Money`/rounding module and its unit tests | MIT monetary-value library with an explicitly advertised high-coverage unit-test posture. |
| [money](https://github.com/carlospalol/money) | core Money arithmetic module | MIT money-value implementation; pin an interpreter-compatible historical commit before running. |
| [fintech-ledger-engine](https://github.com/stephenvelasquez/fintech-ledger-engine) | transaction balancing and posting core | MIT double-entry ledger logic; configure the invariant-heavy core as the bounded subject. |
| [financial-health-calculator](https://github.com/engineerinvestor/financial-health-calculator) | one deterministic CEFR or withdrawal-calculation module | MIT project with pytest; exclude Monte Carlo and UI/API paths unless their determinism is established. |

The entries are candidates, not completed replications. At selection time, reject any whose selected checkout cannot run offline under the exact certification pins. Record that rejection in the evidence folder rather than silently replacing the subject.

## Selected: django-accounting

| Field | Record |
|---|---|
| Upstream | https://github.com/dulacp/django-accounting |
| Pin | `2e61776a653e719a4c15578ab385603a6066c2b6` (2 December 2017) |
| Licence | MIT (`subjects/django-accounting/legacy/LICENSE`) |
| Slice | `Price` and the collected-profits calculator (174 executable lines) |
| Offline evidence | Import stubs only (no Django ORM/SQL). `python3.12 subjects/django-accounting/oracle.py` replays recorded traces against `golden/expected.json`. That match is not a proof of accounting correctness. |
| Test command | `python3.12 subjects/django-accounting/oracle.py` |
| Working tree | `subjects/django-accounting/` |
