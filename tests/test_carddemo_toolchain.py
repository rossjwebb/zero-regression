# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SUBJECT = REPO / "subjects" / "carddemo"
if str(SUBJECT) not in sys.path:
    sys.path.insert(0, str(SUBJECT))

from toolchain import fail, resolve_cobc  # noqa: E402


class CardDemoToolchainTests(unittest.TestCase):
    def test_pins_record_fetch_url_and_hashes(self) -> None:
        pins = tomllib.loads((SUBJECT / "pins.toml").read_text(encoding="utf-8"))
        cfg = pins["gnucobol"]
        self.assertEqual(cfg["package"], "gnucobol3")
        self.assertEqual(cfg["version"], "3.1.2-5.1ubuntu1")
        self.assertEqual(cfg["release"], "3.1.2.0")
        self.assertEqual(cfg["version_marker"], "3.1.2.0")
        self.assertEqual(cfg["binary"], "/usr/bin/cobc")
        self.assertTrue(cfg["url"].endswith("gnucobol3_3.1.2-5.1ubuntu1_amd64.deb"))
        self.assertEqual(len(cfg["sha256"]), 64)
        self.assertEqual(len(cfg["cobc_sha256"]), 64)
        self.assertIn("gnucobol3=3.1.2-5.1ubuntu1", cfg["install"])
        self.assertEqual(len(pins["deb"]), 3)

    def test_runner_uses_pinned_cobc_and_refuses_path_mix(self) -> None:
        script = (SUBJECT / "run-cobol.sh").read_text(encoding="utf-8")
        self.assertIn("toolchain.py", script)
        self.assertIn("S3_COBC", script)
        self.assertIn("PATH cobc", script)
        self.assertIn("not the pinned", script)
        self.assertIn("not a green POSTTRAN job", script)
        self.assertNotIn("looked for cobc, cob, cob2", script)

    def test_missing_cobc_fails_closed_without_a_score(self) -> None:
        pins = tomllib.loads((SUBJECT / "pins.toml").read_text(encoding="utf-8"))
        pins = {**pins, "gnucobol": {**pins["gnucobol"], "binary": "/tmp/s3-missing-cobc"}}
        with self.assertRaises(SystemExit) as raised:
            resolve_cobc(pins)
        message = str(raised.exception)
        self.assertIn("S3 FAIL-CLOSED", message)
        self.assertIn("missing", message.lower())
        self.assertIn("no score is recorded", message)
        self.assertNotIn("killed/seeded", message)

    def test_hash_mismatch_fails_closed(self) -> None:
        pins = tomllib.loads((SUBJECT / "pins.toml").read_text(encoding="utf-8"))
        with TemporaryDirectory() as tmp:
            fake = Path(tmp) / "cobc"
            fake.write_text("not-the-pin\n", encoding="utf-8")
            fake.chmod(0o755)
            pins = {**pins, "gnucobol": {**pins["gnucobol"], "binary": str(fake)}}
            with self.assertRaises(SystemExit) as raised:
                resolve_cobc(pins)
            message = str(raised.exception)
            self.assertIn("hash", message.lower())
            self.assertIn("cannot silently mix", message)
            self.assertNotIn("killed/seeded", message)

    def test_path_cobc_mix_fails_closed(self) -> None:
        pins = tomllib.loads((SUBJECT / "pins.toml").read_text(encoding="utf-8"))
        cobc = Path(pins["gnucobol"]["binary"])
        if not cobc.is_file():
            self.skipTest("pinned cobc is not installed on this VM")
        with mock.patch("toolchain.shutil.which", return_value="/tmp/other-cobc"):
            with self.assertRaises(SystemExit) as raised:
                resolve_cobc(pins)
        message = str(raised.exception)
        self.assertIn("PATH cobc", message)
        self.assertIn("not the pinned", message)

    def test_fail_helper_is_fail_closed(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            fail("unit")
        self.assertEqual(str(raised.exception), "S3 FAIL-CLOSED: unit")

    def test_dedicated_compile_workflow_never_skips(self) -> None:
        workflow = (REPO / ".github" / "workflows" / "s3-carddemo-compile.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("This branch has subjects/carddemo/run-cobol.sh. Skip is not allowed.", workflow)
        self.assertIn("Exit 2 from the harness is the \"job not-run\" code, not a GnuCOBOL error.", workflow)
        self.assertNotIn("paths:", workflow)
        self.assertNotIn("if: ", workflow)
        self.assertNotIn("if [ ! -f", workflow)
        self.assertIn("run-cobol.sh is missing", workflow)
        self.assertIn("Skip is not a pass on this branch", workflow)
        self.assertIn("S3 COMPILE OK", workflow)
        self.assertIn("S3 HARNESS EXIT 2", workflow)
        self.assertIn("S3 COBC FAIL", workflow)
        self.assertIn("work/COBC-FAIL", workflow)
        self.assertIn("compile-OK must not exit 0", workflow)
        self.assertIn("posttran_job=not-run", workflow)
        self.assertIn("PATH=\"/tmp/fake-cobc:$PATH\"", workflow)
        self.assertIn("gnucobol3=3.1.2-5.1ubuntu1", workflow)
        self.assertIn("not paper S3", workflow)

    def test_pins_workflow_has_no_path_skip(self) -> None:
        workflow = (REPO / ".github" / "workflows" / "s3-carddemo.yml").read_text(encoding="utf-8")
        self.assertNotIn("paths:", workflow)
        self.assertIn("Skip is not a pass on this branch", workflow)
        self.assertIn("check-pins.py is missing", workflow)
        self.assertIn("not a GnuCOBOL error", workflow)
        self.assertIn("job not-run", workflow)
