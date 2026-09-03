#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Attempt to compile the pinned CardDemo POSTTRAN batch program.
# Fail closed. Do not invent tests or a mutation score.
set -euo pipefail

SUBJECT="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SUBJECT/../.." && pwd)"
WORK="$SUBJECT/work"
PROGRAM="$SUBJECT/batch/app/cbl/CBTRN02C.cbl"
COPYBOOKS="$SUBJECT/batch/app/cpy"

fail() {
  echo "S3 FAIL-CLOSED: $*" >&2
  exit 2
}

command -v python3.12 >/dev/null || fail "python3.12 is not on PATH"
python3.12 "$SUBJECT/check-pins.py" || fail "pin check failed"

if [[ -d "$SUBJECT/legacy" ]]; then
  fail "legacy/ must not exist. CardDemo at this pin has no legacy tests. Do not invent a suite."
fi
if [[ -d "$SUBJECT/golden" ]]; then
  fail "golden/ must not exist. S3 has no golden-file oracle."
fi
[[ -f "$PROGRAM" ]] || fail "missing pinned program $PROGRAM"

# IBM Enterprise COBOL (cob2 / igyclib) is the native compiler for this
# mainframe source. GnuCOBOL (cobc) is the usual public substitute.
COMPILER=""
for candidate in cobc cob cob2; do
  if command -v "$candidate" >/dev/null 2>&1; then
    COMPILER="$candidate"
    break
  fi
done

if [[ -z "$COMPILER" ]]; then
  fail "no COBOL compiler on PATH (looked for cobc, cob, cob2). IBM Enterprise COBOL is not on this VM. GnuCOBOL is not installed. The pinned POSTTRAN program CBTRN02C was not compiled. This is not a mutation result and no score is recorded."
fi

mkdir -p "$WORK"
echo "S3: compiling $PROGRAM with $COMPILER" >&2

set +e
if [[ "$COMPILER" == "cobc" ]]; then
  "$COMPILER" -std=ibm -I "$COPYBOOKS" -C -o "$WORK/CBTRN02C" "$PROGRAM" >"$WORK/cobc.out" 2>"$WORK/cobc.err"
else
  "$COMPILER" -I "$COPYBOOKS" -o "$WORK/CBTRN02C" "$PROGRAM" >"$WORK/cobc.out" 2>"$WORK/cobc.err"
fi
status=$?
set -e

if [[ $status -ne 0 ]]; then
  echo "----- $COMPILER stdout -----" >&2
  cat "$WORK/cobc.out" >&2 || true
  echo "----- $COMPILER stderr -----" >&2
  cat "$WORK/cobc.err" >&2 || true
  fail "$COMPILER exited $status compiling CBTRN02C. The program is IBM batch COBOL with INDEXED/VSAM SELECT clauses. This is not a mutation result and no score is recorded."
fi

# Compile succeeded. There is still no test suite at this pin.
fail "$COMPILER compiled CBTRN02C, but this pin has no legacy tests. Refusing to invent a suite or a mutation score. Root: $ROOT"
