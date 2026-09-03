# April 2026 certificate — superseded

The April 2026 kill-rate figure of **91.0% / 279 mutants** (186 killed) is superseded. Do not cite it.

This directory keeps three April 2026 artifacts so the tree stays complete. Each is marked `SUPERSEDED` in place. They are not the live executed certificate:

- `CryptographicParityCertificate.json`
- `MutationTelemetry.json`
- `pattern_export/MutationTelemetry.pattern.json`

Those files are telemetry JSON. They are outside the certified module (`account_service_impl.py`) and are not part of any verified evidence chain.

The live executed certificates are the three retained `accounting-service` chains. See the repository-root marker [APRIL-2026-SUPERSEDED.md](../../APRIL-2026-SUPERSEDED.md). The post-approval chain is `fixtures/accounting-service/` at **248/252**.

This file is a marker only. It does not change evidence logs, CONFIG hashes, CERTIFICATE hashes, or the mutation harness.
