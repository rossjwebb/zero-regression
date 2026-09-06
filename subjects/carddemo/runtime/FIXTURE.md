# Synthetic POSTTRAN fixtures

These records are harness fixtures for a GnuCOBOL run of pinned `CBTRN02C`.
They are not IBM VSAM, not EBCDIC, not CICS, and not a legacy test suite.

`seed-indexed.cbl` writes them at job time using the pinned copybooks.

## Runtime label

`runtime=gnucobol-indexed-bdb-fixture`

GnuCOBOL 3.1.2.0 on this pin reports `indexed file handler : BDB`.
That is Berkeley DB under GnuCOBOL `ORGANIZATION IS INDEXED`. It is not
IBM VSAM/KSDS.

## Files CBTRN02C opens

| ASSIGN | JCL DD | Organization in CBTRN02C | Fixture role |
|---|---|---|---|
| `DALYTRAN` | `DALYTRAN` | sequential input | two synthetic daily transactions |
| `TRANFILE` | `TRANFILE` | indexed output | created empty by the program |
| `XREFFILE` | `XREFFILE` | indexed input | one card-to-account row |
| `DALYREJS` | `DALYREJS` | sequential output | created empty by the program |
| `ACCTFILE` | `ACCTFILE` | indexed I-O | one account row |
| `TCATBALF` | `TCATBALF` | indexed I-O | empty indexed file; program may create a key |

## Seeded values

Valid card `4000000000000001` maps to account `00000000001`.
Credit limit `99999.00`. Expiration `2099-12-31`.
Transaction `SYNTH00000000001` amount `+10.00`, origin `2024-06-01-10.00.00.000000`.

Invalid card `4000000000009999` on transaction `SYNTH00000000002` is
absent from the xref file so validation reason 100 rejects it.

Expected program displays after a clean run:

```
START OF EXECUTION OF PROGRAM CBTRN02C
TRANSACTIONS PROCESSED :000000002
TRANSACTIONS REJECTED  :000000001
END OF EXECUTION OF PROGRAM CBTRN02C
```

`CBTRN02C` sets `RETURN-CODE` to 4 when rejects are greater than zero.
That is the program's own rule, not a harness failure.

## What this is not

- Not IBM Language Environment (`CEE3ABD` is a harness stub)
- Not IBM VSAM
- Not CICS
- Not paper S3
- Not a mutation score
