#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <subject-dir>" >&2
  exit 64
fi

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${HARNESS_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m zero_regression_harness.certify "$1"
