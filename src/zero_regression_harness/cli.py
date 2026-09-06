# SPDX-License-Identifier: Apache-2.0
"""Console entry for the Zero-Regression harness."""
from __future__ import annotations

import argparse
from pathlib import Path

from .certify import certify_command
from .evidence import verify_log
from .public_subjects import looks_like_jsonl, protocol_for, resolve_subject, verify_public


def verify_command(target: Path) -> int:
    raw = Path(target)
    if looks_like_jsonl(raw):
        errors, summary = verify_log(raw)
        if errors:
            print(errors[0])
            return 1
        print(f"OK: {raw} ({summary['records']} records; certificate derives from chain)")
        return 0
    try:
        subject = resolve_subject(raw)
    except ValueError as exc:
        print(f"VERIFY FAILURE: {exc}")
        return 1
    if protocol_for(subject) == "mutmut":
        print(
            "VERIFY FAILURE: accounting-service verify still takes an evidence.jsonl chain, "
            "not the subject directory"
        )
        return 1
    return verify_public(subject)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zero-regression",
        description="Zero-Regression certification harness",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify_parser = sub.add_parser(
        "verify",
        help="verify an evidence.jsonl chain or a public S1–S3 posture pack",
    )
    verify_parser.add_argument(
        "log",
        type=Path,
        help="evidence.jsonl chain, or a public subject directory (s1/s2/s3)",
    )

    certify_parser = sub.add_parser(
        "certify",
        help="run the subject protocol (mutmut, or public S1–S3 gates)",
    )
    certify_parser.add_argument(
        "subject",
        type=Path,
        help="subject directory, or s1/s2/s3",
    )

    args = parser.parse_args(argv)
    if args.command == "verify":
        return verify_command(args.log)
    return certify_command(args.subject)


if __name__ == "__main__":
    raise SystemExit(main())
