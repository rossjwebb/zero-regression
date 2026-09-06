#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Compile pinned CBTRN02C (via run-cobol.sh) then run POSTTRAN against
# synthetic GnuCOBOL INDEXED/sequential fixtures.
#
# This is not IBM VSAM, not CICS, not IBM LE, not paper S3, and not a
# mutation score. Compile-only remains run-cobol.sh (exit 2).
#
# Exit codes:
#   0  job ran; work/POSTTRAN records posttran_job=run
#   1  GnuCOBOL compile error (S3 COBC FAIL)
#   2  fail-closed (missing pin, cobc, fixtures, indexed handler, or
#      the binary did not produce the expected job displays)
set -euo pipefail

SUBJECT="$(cd "$(dirname "$0")" && pwd)"
WORK="$SUBJECT/work"
FILES="$WORK/files"
SEEDER="$SUBJECT/runtime/seed-indexed.cbl"
STUB="$SUBJECT/runtime/cee3abd.cbl"
COPYBOOKS="$SUBJECT/batch/app/cpy"
export PYTHONPATH="$SUBJECT${PYTHONPATH:+:$PYTHONPATH}"

fail() {
  echo "S3 FAIL-CLOSED: $*" >&2
  exit 2
}

job_fail() {
  echo "S3 POSTTRAN FAIL: $*" >&2
  exit 2
}

[[ -x "$SUBJECT/run-cobol.sh" ]] || fail "run-cobol.sh is missing or not executable"
[[ -f "$SEEDER" ]] || fail "missing seeder $SEEDER"
[[ -f "$STUB" ]] || fail "missing CEE3ABD stub $STUB"
[[ -f "$SUBJECT/runtime/FIXTURE.md" ]] || fail "missing runtime/FIXTURE.md"

if [[ -d "$SUBJECT/legacy" ]]; then
  fail "legacy/ must not exist. CardDemo at this pin has no legacy tests. Do not invent a suite."
fi
if [[ -d "$SUBJECT/golden" ]]; then
  fail "golden/ must not exist. S3 has no golden-file oracle."
fi

set +e
compile_out="$("$SUBJECT/run-cobol.sh" 2>&1)"
compile_status=$?
set -e
printf '%s\n' "$compile_out"

if [[ -f "$WORK/COBC-FAIL" ]] || printf '%s\n' "$compile_out" | grep -q "S3 COBC FAIL"; then
  echo "S3 POSTTRAN: compile failed (S3 COBC FAIL). The job was not run." >&2
  exit 1
fi

if [[ ! -f "$WORK/COMPILE" ]] || [[ ! -x "$WORK/CBTRN02C" ]]; then
  fail "compile did not produce work/COMPILE and work/CBTRN02C. Skip is not a pass."
fi

if ! grep -q "result=compile-ok" "$WORK/COMPILE"; then
  fail "work/COMPILE is not compile-ok"
fi

toolchain_out="$(python3.12 "$SUBJECT/toolchain.py" --emit "$WORK")" || exit 2
eval "$toolchain_out"
[[ -x "${S3_COBC:-}" ]] || fail "toolchain did not emit a pinned cobc"

info="$("$S3_COBC" --info 2>&1 || true)"
if ! printf '%s\n' "$info" | grep -q "indexed file handler[[:space:]]*:[[:space:]]*BDB"; then
  fail "pinned cobc indexed file handler is not BDB. Refusing to pretend VSAM or invent a sequential substitute silently. Observed: $(printf '%s\n' "$info" | grep -i "indexed file handler" || echo missing)"
fi

export PATH="$S3_COBC_DIR:$PATH"
hash -r

rm -rf "$FILES" "$WORK/SEEDIDX" "$WORK/CEE3ABD" "$WORK/CEE3ABD.so" "$WORK/POSTTRAN" \
  "$WORK/posttran.out" "$WORK/posttran.err" "$WORK/seed.out" "$WORK/seed.err"
mkdir -p "$FILES"

echo "S3: compiling fixture seeder and CEE3ABD stub with pinned $S3_COBC" >&2
set +e
"$S3_COBC" -std=ibm -I "$COPYBOOKS" -x -o "$WORK/SEEDIDX" "$SEEDER" >"$WORK/seed-cobc.out" 2>"$WORK/seed-cobc.err"
seed_cobc=$?
set -e
if [[ $seed_cobc -ne 0 ]] || [[ ! -x "$WORK/SEEDIDX" ]]; then
  cat "$WORK/seed-cobc.out" >&2 || true
  cat "$WORK/seed-cobc.err" >&2 || true
  fail "seeder did not compile. This is not a mutation result and no score is recorded."
fi

set +e
"$S3_COBC" -std=ibm -m -o "$WORK/CEE3ABD" "$STUB" >"$WORK/stub-cobc.out" 2>"$WORK/stub-cobc.err"
stub_cobc=$?
set -e
if [[ $stub_cobc -ne 0 ]]; then
  cat "$WORK/stub-cobc.out" >&2 || true
  cat "$WORK/stub-cobc.err" >&2 || true
  fail "CEE3ABD stub did not compile. This is not IBM Language Environment."
fi

export DD_DALYTRAN="$FILES/DALYTRAN"
export DD_TRANFILE="$FILES/TRANFILE"
export DD_XREFFILE="$FILES/XREFFILE"
export DD_DALYREJS="$FILES/DALYREJS"
export DD_ACCTFILE="$FILES/ACCTFILE"
export DD_TCATBALF="$FILES/TCATBALF"
export DALYTRAN="$DD_DALYTRAN"
export TRANFILE="$DD_TRANFILE"
export XREFFILE="$DD_XREFFILE"
export DALYREJS="$DD_DALYREJS"
export ACCTFILE="$DD_ACCTFILE"
export TCATBALF="$DD_TCATBALF"
export COB_LIBRARY_PATH="$WORK${COB_LIBRARY_PATH:+:$COB_LIBRARY_PATH}"

echo "S3: seeding GnuCOBOL INDEXED/sequential fixtures (not IBM VSAM)" >&2
set +e
"$WORK/SEEDIDX" >"$WORK/seed.out" 2>"$WORK/seed.err"
seed_status=$?
set -e
cat "$WORK/seed.out" >&2 || true
if [[ $seed_status -ne 0 ]]; then
  cat "$WORK/seed.err" >&2 || true
  fail "seeder exited $seed_status. Fixtures were not written."
fi
if ! grep -q "S3 SEEDIDX OK runtime=gnucobol-indexed-bdb-fixture" "$WORK/seed.out"; then
  fail "seeder did not print the fixture-ok marker"
fi
for required in DALYTRAN XREFFILE ACCTFILE TCATBALF; do
  if [[ ! -e "$FILES/$required" ]]; then
    fail "seeder did not create $FILES/$required"
  fi
done

echo "S3: executing work/CBTRN02C with fixture DD assignments" >&2
set +e
"$WORK/CBTRN02C" >"$WORK/posttran.out" 2>"$WORK/posttran.err"
job_status=$?
set -e
cat "$WORK/posttran.out"
if [[ -s "$WORK/posttran.err" ]]; then
  cat "$WORK/posttran.err" >&2
fi

if grep -q "S3 CEE3ABD STUB" "$WORK/posttran.out" "$WORK/posttran.err"; then
  job_fail "CBTRN02C called the CEE3ABD stub (I/O abend). runtime=gnucobol-indexed-bdb-fixture still holds; the job did not complete."
fi

if ! grep -q "START OF EXECUTION OF PROGRAM CBTRN02C" "$WORK/posttran.out"; then
  job_fail "CBTRN02C stdout missing START OF EXECUTION. Job did not run."
fi
if ! grep -q "END OF EXECUTION OF PROGRAM CBTRN02C" "$WORK/posttran.out"; then
  job_fail "CBTRN02C stdout missing END OF EXECUTION. Job did not finish."
fi
if ! grep -q "TRANSACTIONS PROCESSED :000000002" "$WORK/posttran.out"; then
  job_fail "expected TRANSACTIONS PROCESSED :000000002"
fi
if ! grep -q "TRANSACTIONS REJECTED  :000000001" "$WORK/posttran.out"; then
  job_fail "expected TRANSACTIONS REJECTED  :000000001"
fi
if [[ ! -s "$FILES/DALYREJS" ]]; then
  job_fail "expected DALYREJS sequential output from the reject path"
fi
if [[ ! -e "$FILES/TRANFILE" ]]; then
  job_fail "expected TRANFILE indexed output from the post path"
fi

# CBTRN02C moves 4 to RETURN-CODE when rejects > 0. That is a completed job.
if [[ "$job_status" -ne 4 ]]; then
  job_fail "expected program RETURN-CODE 4 (rejects>0); got $job_status"
fi

{
  echo "program=CBTRN02C"
  echo "job=POSTTRAN"
  echo "result=job-run"
  echo "posttran_job=run"
  echo "runtime=gnucobol-indexed-bdb-fixture"
  echo "ibm_vsam=false"
  echo "ibm_cics=false"
  echo "ibm_le_cee3abd=stub"
  echo "compiler=cobc"
  echo "compiler_release=$S3_COBC_RELEASE"
  echo "compiler_package=$S3_COBC_PACKAGE"
  echo "compiler_path=$S3_COBC"
  echo "indexed_file_handler=BDB"
  echo "program_return_code=$job_status"
  echo "transactions_processed=2"
  echo "transactions_rejected=1"
  echo "legacy_tests=none"
  echo "paper_s3=unexecuted"
  echo "mutation_score=not-recorded"
  echo "executed_job=true"
} >"$WORK/POSTTRAN"

echo "S3 POSTTRAN OK: posttran_job=run runtime=gnucobol-indexed-bdb-fixture program_return_code=4" >&2
echo "S3 POSTTRAN OK: GnuCOBOL INDEXED/BDB fixtures; not IBM VSAM; not CICS; not IBM LE; not paper S3." >&2
echo "S3 POSTTRAN OK: mutation_score=not-recorded paper_s3=unexecuted executed_job=true" >&2
exit 0
