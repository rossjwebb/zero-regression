#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run pinned PIT on Defects4J Csv-1f ExtendedBufferedReader.
# Fail closed. Do not invent or commit a mutation score.
set -euo pipefail

SUBJECT="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SUBJECT/../.." && pwd)"
WORK="$SUBJECT/work"
LIB="$WORK/lib"
CLASSES="$WORK/classes"
TEST_CLASSES="$WORK/test-classes"
REPORT="$WORK/pit-reports"
PINS="$SUBJECT/pins.toml"

fail() {
  echo "S2 FAIL-CLOSED: $*" >&2
  exit 2
}

command -v python3.12 >/dev/null || fail "python3.12 is not on PATH"
python3.12 "$SUBJECT/check-pins.py" || fail "pin check failed"

command -v javac >/dev/null || fail "javac is not on PATH. PIT cannot run on this VM."
command -v java >/dev/null || fail "java is not on PATH. PIT cannot run on this VM."

# Maven is not required. PIT is the command-line jars pinned in pins.toml.
# Defects4J Major is not a substitute and is not invoked.

python3.12 - "$PINS" "$LIB" <<'PY' || fail "could not fetch or verify PIT/JUnit jars"
import hashlib
import sys
import tomllib
import urllib.request
from pathlib import Path

pins_path = Path(sys.argv[1])
lib = Path(sys.argv[2])
lib.mkdir(parents=True, exist_ok=True)
pins = tomllib.loads(pins_path.read_text(encoding="utf-8"))

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

for jar in pins["jar"]:
    dest = lib / f"{jar['artifact']}-{jar['version']}.jar"
    if dest.is_file() and sha256_file(dest) == jar["sha256"]:
        print(f"jar ok {dest.name}")
        continue
    print(f"fetch {jar['url']}")
    try:
        urllib.request.urlretrieve(jar["url"], dest)
    except Exception as exc:  # noqa: BLE001 — fail closed with the reason
        print(f"S2 FAIL-CLOSED: download failed for {jar['url']}: {exc}", file=sys.stderr)
        sys.exit(2)
    observed = sha256_file(dest)
    if observed != jar["sha256"]:
        print(f"S2 FAIL-CLOSED: jar hash mismatch {dest.name}: expected {jar['sha256']} observed {observed}", file=sys.stderr)
        sys.exit(2)
    print(f"jar ok {dest.name}")
PY

rm -rf "$CLASSES" "$TEST_CLASSES" "$REPORT"
mkdir -p "$CLASSES" "$TEST_CLASSES" "$REPORT"

mapfile -t MAIN_SOURCES < <(find "$SUBJECT/legacy/src/main/java" -name '*.java' | sort)
[[ ${#MAIN_SOURCES[@]} -gt 0 ]] || fail "no main sources under legacy/"

javac --release 8 -Xlint:-options -d "$CLASSES" "${MAIN_SOURCES[@]}" \
  || fail "javac failed on the pinned Commons-CSV main sources"

mapfile -t TEST_SOURCES < <(
  find "$SUBJECT/legacy/src/test/java" -name '*.java' \
    ! -name 'ExtendedBufferedReaderTest.java' \
    ! -name 'PerformanceTest.java' | sort
)
[[ ${#TEST_SOURCES[@]} -gt 0 ]] || fail "no green test sources under legacy/"

JUNIT="$LIB/junit-4.13.2.jar"
HAMCREST="$LIB/hamcrest-core-1.3.jar"
PIT="$LIB/pitest-1.15.3.jar"
PIT_CLI="$LIB/pitest-command-line-1.15.3.jar"
PIT_ENTRY="$LIB/pitest-entry-1.15.3.jar"
for jar in "$JUNIT" "$HAMCREST" "$PIT" "$PIT_CLI" "$PIT_ENTRY"; do
  [[ -f "$jar" ]] || fail "missing $jar"
done

javac --release 8 -Xlint:-options \
  -cp "$CLASSES:$JUNIT:$HAMCREST" \
  -d "$TEST_CLASSES" \
  "${TEST_SOURCES[@]}" \
  || fail "javac failed on the green test sources"

GREEN_TESTS=(
  org.apache.commons.csv.CSVParserTest
  org.apache.commons.csv.CSVLexerTest
  org.apache.commons.csv.CSVPrinterTest
  org.apache.commons.csv.CSVFormatTest
)

for test_class in "${GREEN_TESTS[@]}"; do
  java -cp "$CLASSES:$TEST_CLASSES:$JUNIT:$HAMCREST" \
    org.junit.runner.JUnitCore "$test_class" \
    || fail "green suite failed: $test_class"
done

# PIT HTML only. The XML reporter in 1.15.3 needs commons-text, which is
# not on this subject's classpath. HTML is still a PIT report.
java -cp "$CLASSES:$TEST_CLASSES:$JUNIT:$HAMCREST:$PIT:$PIT_CLI:$PIT_ENTRY" \
  org.pitest.mutationtest.commandline.MutationCoverageReport \
  --reportDir "$REPORT" \
  --targetClasses org.apache.commons.csv.ExtendedBufferedReader \
  --targetTests org.apache.commons.csv.CSVParserTest,org.apache.commons.csv.CSVLexerTest,org.apache.commons.csv.CSVPrinterTest,org.apache.commons.csv.CSVFormatTest \
  --sourceDirs "$SUBJECT/legacy/src/main/java" \
  --classPath "$CLASSES,$TEST_CLASSES,$JUNIT,$HAMCREST" \
  --outputFormats HTML \
  --timestampedReports false \
  --failWhenNoMutations true \
  --timeoutFactor 2 \
  --timeoutConst 4000 \
  --threads 1 \
  || fail "PIT did not complete"

[[ -f "$REPORT/index.html" ]] || fail "PIT finished without $REPORT/index.html"

echo "S2 PIT finished. Report: $REPORT/index.html"
echo "This script does not record a mutation score and does not claim a paper S2 result."
echo "Root: $ROOT"
