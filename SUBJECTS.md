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

## Selected: CardDemo (S3)

The 2 September programme note names S3 as CardDemo COBOL, no legacy tests. The public CardDemo is AWS Mainframe Modernization CardDemo (IBM-style COBOL/CICS/JCL). This is a pin and a fail-closed compile script. GnuCOBOL can compile the pinned POSTTRAN program `CBTRN02C`. That is not a paper execution of S3 and it does not record a mutation score.

| Field | Record |
|---|---|
| Upstream | https://github.com/aws-samples/aws-mainframe-modernization-carddemo |
| Pin | `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e` (16 October 2025) |
| Licence | Apache-2.0 (`subjects/carddemo/batch/LICENSE`) |
| Slice | POSTTRAN / `CBTRN02C` plus five `COPY` books |
| Legacy tests | none (no `tests/` tree; `test_paths = []`) |
| Test command | `python3.12 subjects/carddemo/check-pins.py` then `sudo apt-get install -y gnucobol` then `./subjects/carddemo/run-cobol.sh` |
| Compile | GnuCOBOL `cobc` 3.1.2 (`apt` package `gnucobol`) compiles `CBTRN02C`; IBM `cob2` is absent; no tests; runner exits 2 |
| Working tree | `subjects/carddemo/` |
