# April 2026 certificate — superseded

The April 2026 kill-rate figure of **91.0% / 279 mutants** is superseded. Do not cite it.

The live executed certificates on `master` are the three retained `accounting-service` chains. Their CONFIG and CERTIFICATE hashes are the values already documented in `README.md` and in each `certificate.txt`. This marker does not rewrite those chains.

| Chain | Why it is kept | CONFIG hash | CERTIFICATE hash | Kill rate |
|---|---|---|---|---|
| `fixtures/accounting-service/` | Post-approval chain. OVERRIDE records were written after the principal signed the four equivalents. | `8ecb042134c8fb756f2e3686489681b96c26b9f111b6b84b614c72f95729b455` | `26075fb863d02f812b7e0c5cd0022c331d300a5504a03074c06b1e901891c72e` | 248/252 |
| `fixtures/accounting-service/superseded/publish-4/` | Same remediation, but its OVERRIDE records predate that approval; superseded, not deleted. | `059f40e476d9e8d1d5be65e241e28acc334f110b7523d5bf3a562e4b2117e97e` | `4e9557b03e12a533d7d5e2579133af94162fe0a8232f9d2a9749f3927f4da5d4` | 248/252 |
| `fixtures/accounting-service/pre-remediation/` | The executed chain that found the two gaps. | `1c206c919541b9d95637837e60570cd9ca466c2450cb4a6c2ee7f74e2f66581e` | `937af6a8368a3ab2104aed6e8a62803c2055a68e7dabc405921dccdebefffb40` | 246/252 |

`fixtures/accounting-service/superseded/publish-4/` is a different supersession (signature order). It is not the April 2026 91.0% / 279 figure.

This file is a marker only. It does not change evidence logs, certificates, or the mutation harness.

## How to check the live chains

From a fresh clone, with Python 3.12.3:

```bash
./verify.py fixtures/accounting-service/evidence.jsonl
./verify.py fixtures/accounting-service/pre-remediation/evidence.jsonl
./verify.py fixtures/accounting-service/superseded/publish-4/evidence.jsonl
```

Exit 0 on each command means that chain still holds.
