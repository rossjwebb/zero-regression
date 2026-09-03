#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""S3 GnuCOBOL pin: fetch/check the Ubuntu .deb and refuse a mixed PATH cobc.

Compile of CBTRN02C is not a POSTTRAN job and is not a mutation result.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path

SUBJECT = Path(__file__).resolve().parent
PINS = SUBJECT / "pins.toml"


def load_pins() -> dict:
    if not PINS.is_file():
        raise SystemExit(f"S3 FAIL-CLOSED: missing {PINS}")
    with PINS.open("rb") as handle:
        return tomllib.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"S3 FAIL-CLOSED: {message}")


def cobc_version_text(cobc: Path) -> str:
    completed = subprocess.run(
        [str(cobc), "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    return (completed.stdout or "") + (completed.stderr or "")


def dpkg_version(package: str) -> str | None:
    completed = subprocess.run(
        ["dpkg-query", "-W", "-f=${Version}", package],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return (completed.stdout or "").strip() or None


def fetch_debs(work: Path, pins: dict | None = None) -> dict[str, Path]:
    """Download each pinned .deb and hash-check it. Do not install from PATH."""
    pins = pins or load_pins()
    lib = work / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    for deb in pins["deb"]:
        dest = lib / deb["filename"]
        if not (dest.is_file() and sha256_file(dest) == deb["sha256"]):
            print(f"fetch {deb['url']}", file=sys.stderr)
            try:
                urllib.request.urlretrieve(deb["url"], dest)
            except Exception as exc:  # noqa: BLE001
                fail(f"GnuCOBOL download failed for {deb['url']}: {exc}")
            observed = sha256_file(dest)
            if observed != deb["sha256"]:
                fail(
                    f"deb hash mismatch {dest.name}: expected {deb['sha256']} observed {observed}"
                )
        print(f"deb ok {dest.name}", file=sys.stderr)
        found[deb["package"]] = dest
    return found


def resolve_cobc(pins: dict | None = None) -> Path:
    """Return the pinned cobc. PATH cobc must be that same binary."""
    pins = pins or load_pins()
    cfg = pins["gnucobol"]
    cobc = Path(cfg["binary"])
    if not cobc.is_file():
        fail(
            "pinned cobc is missing at "
            f"{cobc}. IBM Enterprise COBOL is not used. Install the pin with: "
            f"{cfg['install']}. This is not a mutation result and no score is recorded."
        )
    observed_hash = sha256_file(cobc)
    if observed_hash != cfg["cobc_sha256"]:
        fail(
            f"cobc at {cobc} hash {observed_hash} is not the pinned "
            f"{cfg['cobc_sha256']}. PATH cobc cannot silently mix. "
            f"Install {cfg['package']}={cfg['version']}. "
            "This is not a mutation result and no score is recorded."
        )
    version = cobc_version_text(cobc)
    marker = cfg["version_marker"]
    if marker not in version:
        fail(
            f"cobc at {cobc} is not {cfg['release']}. Observed: {version.splitlines()[0]!r}. "
            "Version mismatch. This is not a mutation result and no score is recorded."
        )
    pkg_ver = dpkg_version(cfg["package"])
    if pkg_ver is None:
        fail(
            f"dpkg does not report {cfg['package']}. The pin is Ubuntu "
            f"{cfg['suite']} {cfg['package']}={cfg['version']}. "
            "This is not a mutation result and no score is recorded."
        )
    if pkg_ver != cfg["version"]:
        fail(
            f"{cfg['package']} is {pkg_ver}, not the pinned {cfg['version']}. "
            "PATH cobc cannot silently mix. This is not a mutation result and no score is recorded."
        )
    path_cobc = shutil.which("cobc")
    if path_cobc:
        resolved = Path(path_cobc).resolve()
        if resolved != cobc.resolve():
            fail(
                f"PATH cobc is {resolved}, not the pinned {cobc}. "
                "Refusing to mix compilers. This is not a mutation result and no score is recorded."
            )
        if sha256_file(resolved) != cfg["cobc_sha256"]:
            fail(
                f"PATH cobc {resolved} hash does not match the pin. "
                "This is not a mutation result and no score is recorded."
            )
    return cobc.resolve()


def emit(work: Path) -> None:
    import shlex

    pins = load_pins()
    fetch_debs(work, pins)
    cobc = resolve_cobc(pins)
    cfg = pins["gnucobol"]

    def out(name: str, value: object) -> None:
        print(f"{name}={shlex.quote(str(value))}")

    out("S3_COBC", cobc)
    out("S3_COBC_DIR", cobc.parent)
    out("S3_COBC_VERSION", cfg["version_marker"])
    out("S3_COBC_PACKAGE", f"{cfg['package']}={cfg['version']}")
    out("S3_COBC_RELEASE", cfg["release"])


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "--emit":
        print("usage: toolchain.py --emit WORKDIR", file=sys.stderr)
        return 2
    emit(Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
