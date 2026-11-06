# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""Shared helpers for tests that import provider modules."""

import sys
import types

import gi

gi.require_version("Secret", "1")
gi.require_version("Soup", "3.0")


def install_define_stub() -> None:
    """Provide the build-generated translvinia.define module to source-tree tests."""
    if "translvinia.define" in sys.modules:
        return

    define = types.ModuleType("translvinia.define")
    define.APP_ID = "io.github.sarok_exe.Translvinia"
    define.RES_PATH = "/io/github/sarok_exe/Translvinia"
    define.VERSION = "0"
    define.LANGUAGES = {}
    define.LANG_ALIASES = {}
    sys.modules["translvinia.define"] = define
