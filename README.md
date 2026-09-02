# Zero-Regression Harness

This repository implements the paper’s deterministic acceptance protocol: exact environment check, twice-run baseline and coverage, mutation execution, human survivor queue, append-only hash chain, and an expiring three-line behavioural-parity certificate. It makes no LLM calls and stores all run artifacts below the subject’s `evidence/` directory.

## Exact certification environment

Certification accepts **only** Python 3.12.3, mutmut 3.6.0, pytest 9.1.1, and pytest-cov 7.1.0. A mismatch is an intentional certification failure before a CONFIG record is created.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-certification.txt
python --version  # must be Python 3.12.3
```

## Certify a subject

Pin the target repository to a commit, add `zero-regression.toml` from `subjects/template.zero-regression.toml`, and ensure its `pyproject.toml` has mutmut 3.6.0 configuration such as:

```toml
[tool.mutmut]
source_paths = ["src/package/"]
pytest_add_cli_args_test_selection = ["tests/"]
```

Then run one command:

```bash
./certify.sh /absolute/path/to/subject
```

The command writes `evidence/run-*/`: raw baseline and mutmut output, JUnit and coverage artifacts, `survivors.json`, `evidence.jsonl`, and `certificate.txt`. It moves a pre-existing mutmut `mutants/` cache into that run directory so a full run cannot silently reuse it.

The harness refuses a mutation run unless mutmut’s JUnit export gives one unique, parseable record per mutant. This is intentional: a summary score is not substitute evidence.

## Triage and signing

All survivors begin as `UNDER_INVESTIGATION`. A reviewer may set only `EQUIVALENT`, `GAP_REMEDIATED`, or `UNDER_INVESTIGATION` directly. `SIGNED_RESIDUAL` is possible only through a named override with a reason code and justification; each action appends records and reissues the certificate.

```bash
./triage.py /absolute/path/to/subject/evidence/run-... list
./triage.py /absolute/path/to/subject/evidence/run-... set 17 EQUIVALENT
./triage.py /absolute/path/to/subject/evidence/run-... override 18 --name "A. Reviewer" --reason-code "ACCEPTED_RISK" --justification "Explained residual risk and accountable owner."
```

If (and only if) the out-of-scope generation pipeline is re-run, its attributable spend can be added without making an LLM call from this harness:

```bash
./cost.py /absolute/path/to/subject/evidence/run-... --role generator --tokens 12345 --spend-usd 1.23 --reference pipeline-run-immutable-id
```

## Independent verification and paper table

Neither command runs Python tests or mutation testing. `verify.py` recomputes every canonical SHA-256 hash and predecessor link, then independently derives every certificate from the chain records. `results.py` includes only valid chains.

```bash
./verify.py /absolute/path/to/subject/evidence/run-.../evidence.jsonl
./results.py /absolute/path/to/parent-containing-subjects > replication-results.md
```

## Published fintx figures

The workspace supplied for this build contains the paper’s aggregate figures, but not the fintx source checkout, original evidence chain, or July ticket outputs. `reference_fintx.py` generates a hash-valid, explicitly labelled aggregate reconstruction (43 tests, 100% coverage, 252 mutants, 246 killed, 6 survived, 0 timeouts) for inspection and table wiring. Its six survivor classes remain `UNDER_INVESTIGATION`, rather than inventing undisclosed per-class counts. It is not an executed certification and must be replaced with the real pinned subject to make the production-replication claim.

```bash
./reference_fintx.py
./verify.py fixtures/fintx-accounting-migration/evidence/published-aggregate-reconstruction/evidence.jsonl
./results.py fixtures
```

`SUBJECTS.md` records the public-replication admission criteria and five candidates. Select only checkouts which demonstrably meet the exact environment and offline/determinism requirements.
