#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run pinned PIT on Defects4J Csv-1f ExtendedBufferedReader.
# Fail closed. Do not invent or commit a mutation score.
#
# Toolchain: pinned Temurin 11.0.32.1+1 for javac/java/PIT. Subject
# bytecode is javac --release 8 (Java 8 classfiles). PATH Java 21 is
# not used. Mutators are the named DEFAULTS group only.
set -euo pipefail

SUBJECT="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SUBJECT/../.." && pwd)"
WORK="$SUBJECT/work"
LIB="$WORK/lib"
CLASSES="$WORK/classes"
TEST_CLASSES="$WORK/test-classes"
REPORT="$WORK/pit-reports"
PIT_LOG="$WORK/pit.log"
export PYTHONPATH="$SUBJECT${PYTHONPATH:+:$PYTHONPATH}"

fail() {
  echo "S2 FAIL-CLOSED: $*" >&2
  exit 2
}

command -v python3.12 >/dev/null || fail "python3.12 is not on PATH"
python3.12 "$SUBJECT/check-pins.py" || fail "pin check failed"

# Resolve the pinned JDK 11 and the PIT/JUnit jars. Do not use PATH java.
eval "$(
  python3.12 - "$WORK" <<'PY'
from pathlib import Path
import shlex
import sys
from toolchain import ensure_jdk, ensure_jars, load_pins

work = Path(sys.argv[1])
pins = load_pins()
home = ensure_jdk(work, pins)
jars = ensure_jars(work / "lib", pins)
pit = pins["pit"]

def emit(name: str, value: object) -> None:
    print(f"{name}={shlex.quote(str(value))}")

emit("S2_JAVA_HOME", home)
emit("S2_JAVAC", home / "bin" / "javac")
emit("S2_JAVA", home / "bin" / "java")
for key, path in jars.items():
    env = key.upper().replace("-", "_")
    emit(f"S2_JAR_{env}", path)
emit("S2_MUTATORS", pit["mutators"])
emit("S2_TARGET", pit["target_class"])
emit("S2_EXCLUDED_CLASSES", ",".join(pit["excluded_classes"]))
emit("S2_TARGET_TESTS", ",".join(pit["green_tests"]))
emit("S2_EXCLUDED_TESTS", ",".join(pit["excluded_tests"]))
emit("S2_THREADS", pit["threads"])
emit("S2_TIMEOUT_FACTOR", pit["timeout_factor"])
emit("S2_TIMEOUT_CONST", pit["timeout_const_ms"])
emit("S2_MINION_JVM_ARGS", pit["minion_jvm_args"])
emit("S2_GREEN_TESTS", " ".join(pit["green_tests"]))
PY
)"

[[ -x "${S2_JAVAC:-}" ]] || fail "pinned javac is not executable"
[[ -x "${S2_JAVA:-}" ]] || fail "pinned java is not executable"

# Refuse PATH java/javac so classloading cannot silently mix JDKs.
export JAVA_HOME="$S2_JAVA_HOME"
export PATH="$S2_JAVA_HOME/bin:$PATH"
hash -r

resolved_java="$(command -v java)"
resolved_javac="$(command -v javac)"
[[ "$resolved_java" == "$S2_JAVA" ]] || fail "java on PATH is $resolved_java, not the pinned $S2_JAVA"
[[ "$resolved_javac" == "$S2_JAVAC" ]] || fail "javac on PATH is $resolved_javac, not the pinned $S2_JAVAC"

"$S2_JAVA" -version 2>&1 | grep -F "11.0.32.1" >/dev/null \
  || fail "pinned java is not Temurin 11.0.32.1"

rm -rf "$CLASSES" "$TEST_CLASSES" "$REPORT" "$PIT_LOG"
mkdir -p "$CLASSES" "$TEST_CLASSES" "$REPORT"

mapfile -t MAIN_SOURCES < <(find "$SUBJECT/legacy/src/main/java" -name '*.java' | sort)
[[ ${#MAIN_SOURCES[@]} -gt 0 ]] || fail "no main sources under legacy/"

# Java 8 bytecode from the pinned JDK 11 compiler. Not PATH javac --release 8
# on Java 21, which would still run PIT on a 21 VM.
"$S2_JAVAC" --release 8 -Xlint:-options -d "$CLASSES" "${MAIN_SOURCES[@]}" \
  || fail "javac failed on the pinned Commons-CSV main sources"

mapfile -t TEST_SOURCES < <(
  find "$SUBJECT/legacy/src/test/java" -name '*.java' \
    ! -name 'ExtendedBufferedReaderTest.java' \
    ! -name 'PerformanceTest.java' | sort
)
[[ ${#TEST_SOURCES[@]} -gt 0 ]] || fail "no green test sources under legacy/"

[[ -f "${S2_JAR_JUNIT:-}" ]] || fail "missing junit jar"
[[ -f "${S2_JAR_HAMCREST_CORE:-}" ]] || fail "missing hamcrest-core jar"
[[ -f "${S2_JAR_PITEST:-}" ]] || fail "missing pitest jar"
[[ -f "${S2_JAR_PITEST_COMMAND_LINE:-}" ]] || fail "missing pitest-command-line jar"
[[ -f "${S2_JAR_PITEST_ENTRY:-}" ]] || fail "missing pitest-entry jar"

"$S2_JAVAC" --release 8 -Xlint:-options \
  -cp "$CLASSES:$S2_JAR_JUNIT:$S2_JAR_HAMCREST_CORE" \
  -d "$TEST_CLASSES" \
  "${TEST_SOURCES[@]}" \
  || fail "javac failed on the green test sources"

python3.12 - "$CLASSES" <<'PY' || fail "subject classfiles are not Java 8"
from pathlib import Path
import sys
from toolchain import assert_java8_classfiles

assert_java8_classfiles(
    Path(sys.argv[1]),
    ["org/apache/commons/csv/ExtendedBufferedReader.class"],
)
PY

read -r -a GREEN_TESTS <<< "$S2_GREEN_TESTS"
for test_class in "${GREEN_TESTS[@]}"; do
  "$S2_JAVA" -cp "$CLASSES:$TEST_CLASSES:$S2_JAR_JUNIT:$S2_JAR_HAMCREST_CORE" \
    org.junit.runner.JUnitCore "$test_class" \
    || fail "green suite failed: $test_class"
done

# PIT HTML only. XML in 1.15.3 needs commons-text and would invite storing a score.
# Minion heap and timeout isolate one mutant; judge_pit_log still fail-closes
# if any mutant TIMED_OUT / MEMORY_ERROR / RUN_ERROR.
set +e
"$S2_JAVA" -cp "$CLASSES:$TEST_CLASSES:$S2_JAR_JUNIT:$S2_JAR_HAMCREST_CORE:$S2_JAR_PITEST:$S2_JAR_PITEST_COMMAND_LINE:$S2_JAR_PITEST_ENTRY" \
  org.pitest.mutationtest.commandline.MutationCoverageReport \
  --reportDir "$REPORT" \
  --targetClasses "$S2_TARGET" \
  --excludedClasses "$S2_EXCLUDED_CLASSES" \
  --targetTests "$S2_TARGET_TESTS" \
  --excludedTestClasses "$S2_EXCLUDED_TESTS" \
  --mutators "$S2_MUTATORS" \
  --sourceDirs "$SUBJECT/legacy/src/main/java" \
  --classPath "$CLASSES,$TEST_CLASSES,$S2_JAR_JUNIT,$S2_JAR_HAMCREST_CORE" \
  --outputFormats HTML \
  --timestampedReports false \
  --failWhenNoMutations true \
  --timeoutFactor "$S2_TIMEOUT_FACTOR" \
  --timeoutConst "$S2_TIMEOUT_CONST" \
  --threads "$S2_THREADS" \
  --jvmArgs "$S2_MINION_JVM_ARGS" \
  --jvmPath "$S2_JAVA" \
  >"$PIT_LOG" 2>&1
pit_rc=$?
set -e
cat "$PIT_LOG"

[[ "$pit_rc" -eq 0 ]] || fail "PIT process exited $pit_rc (see $PIT_LOG). No score is stored."

python3.12 - "$PIT_LOG" <<'PY' || fail "PIT log failed the fail-closed judge"
from pathlib import Path
import sys
from toolchain import judge_pit_log

errors = judge_pit_log(Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace"))
if errors:
    for error in errors:
        print(f"S2 FAIL-CLOSED: {error}", file=sys.stderr)
    sys.exit(2)
print("S2 PIT log: no isolated TIMED_OUT / MEMORY_ERROR / RUN_ERROR")
PY

[[ -f "$REPORT/index.html" ]] || fail "PIT finished without $REPORT/index.html"

echo "S2 PIT finished. Report: $REPORT/index.html"
echo "This script does not record a mutation score and does not claim a paper S2 result."
echo "Root: $ROOT"
