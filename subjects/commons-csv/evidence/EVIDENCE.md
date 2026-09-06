# S2 Commons-CSV live PIT evidence

This pack records a live fail-closed PIT run without a mutation score.
It is not paper S2. It is not a paper execution of S2.

Machine-readable copies: [`s2-posture.json`](s2-posture.json),
[`pit-receipt.json`](pit-receipt.json).

## Claims

- `mutation_score=not-stored`
- `paper_s2=unexecuted`
- `status=live-pit-executed`

No mutation score is stored. No kill-rate percentage is stored. The
paper has not executed S2.

## What ran

On Python 3.12.3 this slice ran `./subjects/commons-csv/run-pit.sh`.
That script fetched hash-checked Temurin 11.0.32.1+1, compiled the
Csv-1f pin with `javac --release 8` (classfile major 52), ran the
four green JUnit classes, then invoked PIT 1.15.3 with mutators
DEFAULTS on `ExtendedBufferedReader` only. The process exited 0.
`toolchain.py:judge_pit_log` reported no TIMED_OUT, MEMORY_ERROR, or
RUN_ERROR. PIT wrote a local HTML report under `work/pit-reports/`
(gitignored). The receipt does not copy that HTML or `pit.log`.

`check-pins.py` is still the pin gate. On this tree it was run with
Python 3.12.3 and exited 0. That exit is pin integrity, not a score.

The PR #12 pack was `scaffolding+runner-only` with
`executed_in_this_pack=false`. This slice advances that pack to a
live run. It does not invent a mutation percentage.

## What is not recorded

- No mutation score, no percentage, no CERTIFICATE.
- No PIT HTML. `work/pit-reports/` remains gitignored.
- No `killed` / `seeded` / `kill_rate` fields.
- No claim that paper S2 ran.

## How to re-run

```bash
python3.12 subjects/commons-csv/check-pins.py
./subjects/commons-csv/run-pit.sh
python3.12 subjects/commons-csv/record-pit-receipt.py --pit-exit 0 --stdout-only
python3.12 subjects/commons-csv/check-s2-pit.py --require-live
```

`--require-live` is fail-closed if `work/` is missing or the judge
fails. A skip is not a pass.
