# SPDX-License-Identifier: Apache-2.0
"""Apply a Stage D candidate rewrite without editing legacy/.

The pin is imported from ``legacy/`` through the ordinary path finder.
This module then replaces the named class (or method) on the
already-imported pin module with the candidate's rewrite. A guarded
``builtins.__import__`` hook keeps the replacement in place if
``oracle.py`` later imports ``accounting.*``.

This is the Stage C import-hook spirit, used for produced candidate
modules rather than known-bad probes. It is not paper S1.
"""
from __future__ import annotations

import builtins
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

STAGE_D = Path(__file__).resolve().parent
SUBJECT = STAGE_D.parents[1]
STUBS = SUBJECT / "stubs"
LEGACY = SUBJECT / "legacy"
DEFAULT_ARM = "cursor"

_HOOK_INSTALLED = False
_ORIGINAL_IMPORT = builtins.__import__
_ACTIVE_ARM = DEFAULT_ARM


def candidates_dir(arm: str = DEFAULT_ARM) -> Path:
    return STAGE_D / "arms" / arm / "candidates"


# Back-compat alias used by evaluate receipts / older callers.
CANDIDATES = candidates_dir(DEFAULT_ARM)


def ensure_pin_path() -> None:
    for path in (STUBS, LEGACY):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def load_manifest(name: str, arm: str = DEFAULT_ARM) -> dict[str, Any]:
    path = candidates_dir(arm) / name / "manifest.json"
    if not path.is_file():
        raise SystemExit(f"missing candidate manifest {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("name") != name:
        raise SystemExit(f"manifest name {payload.get('name')!r} != {name!r}")
    return payload


def load_candidate_module(name: str, source_name: str, arm: str = DEFAULT_ARM):
    source = candidates_dir(arm) / name / source_name
    if not source.is_file():
        raise SystemExit(f"missing candidate source {source}")
    spec = importlib.util.spec_from_file_location(f"stage_d_candidate_{name}", source)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _import_pin_modules() -> None:
    _ORIGINAL_IMPORT("accounting.libs.prices")
    _ORIGINAL_IMPORT("accounting.apps.books.models")
    _ORIGINAL_IMPORT("accounting.apps.books.calculators")


def _patched_import(
    name: str,
    globals: dict | None = None,
    locals: dict | None = None,
    fromlist: tuple | list = (),
    level: int = 0,
    *,
    apply: Callable[[], None],
) -> Any:
    module = _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
    if name == "accounting" or name.startswith("accounting."):
        apply()
    return module


def _apply_replacement(manifest: dict[str, Any], candidate) -> None:
    target = manifest["target"]
    pin_module = importlib.import_module(target["module"])
    class_name = target["class"]
    exported = target.get("export", class_name)
    if "method" in target:
        pin_class = getattr(pin_module, class_name)
        setattr(pin_class, target["method"], getattr(candidate, target["method"]))
        return
    setattr(pin_module, class_name, getattr(candidate, exported))


def install_candidate(name: str, arm: str = DEFAULT_ARM) -> dict[str, Any]:
    """Load the pin, then replace the candidate's target callable."""
    global _HOOK_INSTALLED, _ACTIVE_ARM, CANDIDATES
    ensure_pin_path()
    _ACTIVE_ARM = arm
    CANDIDATES = candidates_dir(arm)
    manifest = load_manifest(name, arm=arm)
    applying = {"on": False}

    def apply() -> None:
        if applying["on"]:
            return
        applying["on"] = True
        try:
            candidate = load_candidate_module(name, manifest["source"], arm=arm)
            _apply_replacement(manifest, candidate)
        finally:
            applying["on"] = False

    _import_pin_modules()
    apply()

    if not _HOOK_INSTALLED:
        builtins.__import__ = lambda *args, **kwargs: _patched_import(
            *args,
            apply=apply,
            **kwargs,
        )
        _HOOK_INSTALLED = True
    return manifest
