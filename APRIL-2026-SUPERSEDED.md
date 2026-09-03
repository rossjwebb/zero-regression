# April 2026 certificate — superseded

The April 2026 kill-rate figure of **91.0% / 279 mutants** is superseded. Do not cite it.

The live executed certificates on `master` are the three retained `accounting-service` chains. Their CONFIG and CERTIFICATE hashes are the values already documented in `README.md` and in each `certificate.txt`. This marker does not rewrite those chains.

| Chain | Why it is kept | CONFIG hash | CERTIFICATE hash | Kill rate |
|---|---|---|---|---|
| `fixtures/accounting-service/` | Post-approval chain. OVERRIDE records were written after the principal signed the four equivalents. | `60df647fc89a72ea0627b9bf933482bea4e9259f53f6614c4b61c78590a8be06` | `fe677dfcbee1e89de2a62509f1fb48bee8d5bce4508bb4e1cfde90cb1b9c9cd4` | 248/252 |
| `fixtures/accounting-service/superseded/publish-4/` | Same remediation, but its OVERRIDE records predate that approval; superseded, not deleted. | `eccc17cdcc1f82072451ef9a38a5555457b4d75aedf5112ab75d1c09f40b321b` | `05e14679f7a53a1958321d510280366d3c8b2c8faebb30156b736f02d7e05788` | 248/252 |
| `fixtures/accounting-service/pre-remediation/` | The executed chain that found the two gaps. | `1c7f02cc4305fc0aae65bb6f1ed8d62aaeda67fa793c579004143717926a3afd` | `9035f4357e14af7e610d93911cd8eefbbaf253f3e4f90bc789bea683fc41f811` | 246/252 |

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
