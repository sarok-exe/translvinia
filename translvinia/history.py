# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""Persistent translation history.

Every successfully completed translation is appended to a JSON Lines file in
the user's data directory. JSONL keeps appends cheap even for a large history
and lets us recover gracefully from a truncated or corrupt line.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gi.repository import GLib

from translvinia.providers.base import Translation


@dataclass(frozen=True)
class HistoryEntry:
    """A translation that was completed and saved to disk."""

    id: str
    timestamp: str
    text: str
    translation: str
    src: str
    dest: str
    detected: str | None = None
    provider: str = ""
    mistakes: dict[str, str] | None = None
    pronunciation: dict[str, str | None] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entry to a JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistoryEntry:
        """Create an entry from a stored dictionary."""
        if not isinstance(data, dict):
            raise TypeError("history entry must be an object")

        text = data.get("text")
        translation = data.get("translation")
        src = data.get("src")
        dest = data.get("dest")
        if not all(isinstance(value, str) for value in (text, translation, src, dest)):
            raise ValueError("history entry is missing required text fields")

        detected = data.get("detected")
        provider = data.get("provider", "")

        return cls(
            id=str(data.get("id") or uuid.uuid4().hex),
            timestamp=str(data.get("timestamp") or datetime.now(timezone.utc).isoformat(timespec="seconds")),
            text=text,
            translation=translation,
            src=src,
            dest=dest,
            detected=str(detected) if detected else None,
            provider=str(provider) if provider else "",
            mistakes=data.get("mistakes") if isinstance(data.get("mistakes"), dict) else None,
            pronunciation=data.get("pronunciation") if isinstance(data.get("pronunciation"), dict) else None,
        )


class HistoryStore:
    """Append-only persistent history with an in-memory newest-first cache."""

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = Path(path) if path is not None else self.default_path()
        self._lock = threading.RLock()
        self._entries: list[HistoryEntry] | None = None

    @staticmethod
    def default_path() -> Path:
        """Return the default history path in the user's data directory."""
        return Path(GLib.get_user_data_dir()) / "translvinia" / "history" / "history.jsonl"

    def load(self) -> list[HistoryEntry]:
        """Load history from disk, newest first. Malformed lines are skipped."""
        with self._lock:
            if self._entries is not None:
                return self._entries

            entries: list[HistoryEntry] = []
            if self.path.exists():
                try:
                    with self.path.open("r", encoding="utf-8") as history_file:
                        for line_number, line in enumerate(history_file, 1):
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entries.append(HistoryEntry.from_dict(json.loads(line)))
                            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                                logging.warning(
                                    "Skipping invalid history entry at %s:%d: %s",
                                    self.path,
                                    line_number,
                                    exc,
                                )
                except OSError as exc:
                    logging.error("Could not read translation history: %s", exc)

            entries.reverse()
            self._entries = entries
            return entries

    def entries(self) -> list[HistoryEntry]:
        """Return a copy of the loaded history, newest first."""
        return list(self.load())

    def record(self, translation: Translation, provider: str = "") -> HistoryEntry:
        """Persist a completed translation and update the in-memory cache."""
        original = translation.original
        mistakes = None
        if translation.mistakes:
            mistakes = {
                "markup": translation.mistakes.markup,
                "text": translation.mistakes.text,
            }

        pronunciation = None
        if translation.pronunciation:
            pronunciation = {
                "src": translation.pronunciation.src,
                "dest": translation.pronunciation.dest,
            }

        entry = HistoryEntry(
            id=uuid.uuid4().hex,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            text=original.text,
            translation=translation.text,
            src=original.src,
            dest=original.dest,
            detected=translation.detected,
            provider=provider,
            mistakes=mistakes,
            pronunciation=pronunciation,
        )

        with self._lock:
            self._append(entry)
            if self._entries is not None:
                self._entries.insert(0, entry)
            # If the cache has not been loaded yet, leave it unloaded. The next
            # reader will load the file, including this entry.

        return entry

    def _append(self, entry: HistoryEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n"
        data = line.encode("utf-8")

        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            remaining = memoryview(data)
            while remaining:
                written = os.write(fd, remaining)
                remaining = remaining[written:]
            os.fsync(fd)
        finally:
            os.close(fd)


def provider_display_name(provider: Any) -> str:
    """Return a stable, human-readable provider name for history metadata."""
    if provider is None:
        return ""
    return getattr(provider, "prettyname", "") or getattr(provider, "name", "") or ""
