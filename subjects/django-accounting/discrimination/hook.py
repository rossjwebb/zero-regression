# SPDX-License-Identifier: Apache-2.0
"""Import hook that patches pin callables without editing legacy/.

The pin is imported from ``legacy/`` through the ordinary path finder.
This module then wraps the named probe's target callables on the
already-imported classes. A guarded ``builtins.__import__`` hook keeps
those patches in place if ``oracle.py`` later imports ``accounting.*``
(the objects in ``sys.modules`` are the patched ones).
"""
from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path
from typing import Any, Callable

DISCRIMINATION = Path(__file__).resolve().parent
SUBJECT = DISCRIMINATION.parent
STUBS = SUBJECT / "stubs"
LEGACY = SUBJECT / "legacy"

_HOOK_INSTALLED = False
_ORIGINAL_IMPORT = builtins.__import__


def ensure_pin_path() -> None:
    for path in (STUBS, LEGACY, DISCRIMINATION):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def load_probe(name: str):
    ensure_pin_path()
    return importlib.import_module(f"probes.{name}")


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


def install_probe(name: str) -> None:
    """Load the pin, then wrap the probe's target callables."""
    global _HOOK_INSTALLED
    ensure_pin_path()
    probe = load_probe(name)
    applying = {"on": False}

    def apply() -> None:
        if applying["on"]:
            return
        applying["on"] = True
        try:
            probe.install()
        finally:
            applying["on"] = False

    # Import the pin with the original importer *before* installing the
    # hook so probe.install() can see fully-initialised classes.
    _import_pin_modules()
    apply()

    if not _HOOK_INSTALLED:
        builtins.__import__ = lambda *args, **kwargs: _patched_import(
            *args,
            apply=apply,
            **kwargs,
        )
        _HOOK_INSTALLED = True
