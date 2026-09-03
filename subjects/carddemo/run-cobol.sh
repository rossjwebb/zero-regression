#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Compile the pinned CardDemo POSTTRAN batch program CBTRN02C with the
# pinned GnuCOBOL cobc only. PATH cobc cannot silently mix.
#
# Exit codes (do not treat 2 as a GnuCOBOL error):
#   cobc itself returns 0 when CBTRN02C compiles. The harness then
#   exits 2 to mean posttran_job=not-run (not paper S3). That is
#   expected. Do not change compile-OK to exit 0: that would look
#   like a passing POSTTRAN job.
#   A GnuCOBOL compile error writes work/COBC-FAIL and prints
#   S3 COBC FAIL. Pin/PATH failures print S3 FAIL-CLOSED.
# Fail closed if cobc is missing, the pin mismatches, or compile fails.
# Compile OK is not a green POSTTRAN job. Do not invent tests or a score.
set -euo pipefail

SUBJECT="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SUBJECT/../.." && pwd)"
WORK="$SUBJECT/work"
PROGRAM="$SUBJECT/batch/app/cbl/CBTRN02C.cbl"
COPYBOOKS="$SUBJECT/batch/app/cpy"
export PYTHONPATH="$SUBJECT${PYTHONPATH:+:$PYTHONPATH}"

fail() {
  echo "S3 FAIL-CLOSED: $*" >&2
  exit 2
}

cobc_fail() {
  local cobc_status="$1"
  shift
  mkdir -p "$WORK"
  {
    echo "result=cobc-fail"
    echo "cobc_status=$cobc_status"
    echo "harness_exit=2"
    echo "harness_meaning=cobc-compile-failed"
    echo "posttran_job=not-run"
    echo "mutation_score=not-recorded"
  } >"$WORK/COBC-FAIL"
  echo "S3 COBC FAIL: pinned cobc exited $cobc_status compiling CBTRN02C. This is a GnuCOBOL compile error. The CI job must fail." >&2
  echo "S3 COBC FAIL: $*" >&2
  exit 2
}

job_not_run() {
  echo "S3 HARNESS EXIT 2: cobc_status=0. posttran_job=not-run. This is the harness job-not-run code, not a GnuCOBOL error." >&2
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

# Resolve the pinned cobc. Do not use PATH cobc, cob, or cob2.
mkdir -p "$WORK"
toolchain_out="$(python3.12 "$SUBJECT/toolchain.py" --emit "$WORK")" || exit 2
eval "$toolchain_out"

[[ -n "${S3_COBC:-}" ]] || fail "toolchain did not emit S3_COBC"
[[ -x "$S3_COBC" ]] || fail "pinned cobc is not executable: $S3_COBC"

export PATH="$S3_COBC_DIR:$PATH"
hash -r
resolved_cobc="$(command -v cobc || true)"
[[ "$resolved_cobc" == "$S3_COBC" ]] || fail "cobc on PATH is ${resolved_cobc:-missing}, not the pinned $S3_COBC"

"$S3_COBC" --version 2>&1 | grep -F "$S3_COBC_VERSION" >/dev/null \
  || fail "pinned cobc is not GnuCOBOL $S3_COBC_VERSION"

if command -v cob2 >/dev/null 2>&1; then
  echo "S3: ignoring PATH cob2; IBM Enterprise COBOL is not the pin" >&2
fi

rm -rf "$WORK/CBTRN02C" "$WORK/cobc.out" "$WORK/cobc.err" "$WORK/COMPILE" "$WORK/COBC-FAIL" "$WORK/cobc.version"
mkdir -p "$WORK"
echo "S3: compiling $PROGRAM with pinned $S3_COBC ($S3_COBC_PACKAGE)" >&2
"$S3_COBC" --version >"$WORK/cobc.version" 2>&1 || true

set +e
"$S3_COBC" -std=ibm -I "$COPYBOOKS" -x -o "$WORK/CBTRN02C" "$PROGRAM" >"$WORK/cobc.out" 2>"$WORK/cobc.err"
cobc_status=$?
set -e

if [[ $cobc_status -ne 0 ]]; then
  echo "----- cobc stdout -----" >&2
  cat "$WORK/cobc.out" >&2 || true
  echo "----- cobc stderr -----" >&2
  cat "$WORK/cobc.err" >&2 || true
  cobc_fail "$cobc_status" "GnuCOBOL did not compile CBTRN02C. This is not the harness job-not-run code and no score is recorded."
fi

if [[ ! -x "$WORK/CBTRN02C" ]]; then
  cobc_fail "missing-artifact" "pinned cobc reported success but produced no executable at $WORK/CBTRN02C. This is not a mutation result and no score is recorded."
fi

{
  echo "program=CBTRN02C"
  echo "job=POSTTRAN"
  echo "compiler=cobc"
  echo "compiler_release=$S3_COBC_RELEASE"
  echo "compiler_package=$S3_COBC_PACKAGE"
  echo "compiler_path=$S3_COBC"
  echo "artifact=work/CBTRN02C"
  echo "result=compile-ok"
  echo "cobc_status=0"
  echo "harness_exit=2"
  echo "harness_meaning=posttran-job-not-run"
  echo "legacy_tests=none"
  echo "posttran_job=not-run"
  echo "mutation_score=not-recorded"
} >"$WORK/COMPILE"

echo "S3 COMPILE OK: pinned cobc ($S3_COBC_PACKAGE) compiled POSTTRAN/CBTRN02C to $WORK/CBTRN02C" >&2
echo "S3 COMPILE OK: $($S3_COBC --version | head -n 1)" >&2
echo "S3 COMPILE OK: cobc_status=0. This is a compile only. It is not a green POSTTRAN job and not a CardDemo run." >&2

# Compile succeeded. There is still no test suite at this pin.
# Exit 2 here is the harness job-not-run code. cobc already returned 0.
job_not_run "pinned cobc compiled CBTRN02C (cobc_status=0), but this pin has no legacy tests. Refusing to invent a suite or claim a POSTTRAN job. Harness exit 2 means posttran_job=not-run, not a GnuCOBOL error. This is not a mutation result and no score is recorded. Runtime still cannot open DALYTRAN/VSAM files or resolve IBM Language Environment CEE3ABD. Root: $ROOT"
