# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import tempfile
import unittest
from pathlib import Path

from support import install_define_stub

install_define_stub()

from translvinia.history import HistoryEntry, HistoryStore, provider_display_name
from translvinia.providers.base import Translation, TranslationMistake, TranslationPronunciation, TranslationRequest


def _translation(
    text: str = "Hello",
    translated: str = "Bonjour",
    src: str = "en",
    dest: str = "fr",
    detected: str | None = None,
    mistakes: TranslationMistake | None = None,
    pronunciation: TranslationPronunciation | None = None,
) -> Translation:
    return Translation(
        translated,
        TranslationRequest(text, src, dest),
        detected=detected,
        mistakes=mistakes,
        pronunciation=pronunciation or TranslationPronunciation(None, None),
    )


class HistoryStoreTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "history" / "history.jsonl"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_missing_file_is_empty(self):
        store = HistoryStore(self.path)
        self.assertEqual(store.entries(), [])

    def test_record_persists_across_reload(self):
        store = HistoryStore(self.path)
        store.record(_translation(), provider="Test Provider")

        reloaded = HistoryStore(self.path)
        entries = reloaded.entries()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].text, "Hello")
        self.assertEqual(entries[0].translation, "Bonjour")
        self.assertEqual(entries[0].src, "en")
        self.assertEqual(entries[0].dest, "fr")
        self.assertEqual(entries[0].provider, "Test Provider")
        self.assertTrue(entries[0].id)
        self.assertTrue(entries[0].timestamp)

    def test_entries_are_newest_first(self):
        store = HistoryStore(self.path)
        store.record(_translation(text="First"), provider="Test")
        store.record(_translation(text="Second"), provider="Test")

        entries = HistoryStore(self.path).entries()
        self.assertEqual([entry.text for entry in entries], ["Second", "First"])

    def test_loaded_cache_is_kept_in_sync(self):
        store = HistoryStore(self.path)
        self.assertEqual(store.entries(), [])
        store.record(_translation(text="Cached"), provider="Test")

        self.assertEqual(store.entries()[0].text, "Cached")
        self.assertEqual(HistoryStore(self.path).entries()[0].text, "Cached")

    def test_mistakes_and_pronunciation_are_saved(self):
        store = HistoryStore(self.path)
        store.record(
            _translation(
                mistakes=TranslationMistake("<b>Helo</b>", "Helo"),
                pronunciation=TranslationPronunciation("həˈloʊ", "bɔ̃ʒuʁ"),
            )
        )

        entry = HistoryStore(self.path).entries()[0]
        self.assertEqual(entry.mistakes, {"markup": "<b>Helo</b>", "text": "Helo"})
        self.assertEqual(entry.pronunciation, {"src": "həˈloʊ", "dest": "bɔ̃ʒuʁ"})

    def test_invalid_lines_are_skipped(self):
        self.path.parent.mkdir(parents=True)
        valid = HistoryEntry(
            id="1",
            timestamp="2026-01-01T00:00:00+00:00",
            text="Hello",
            translation="Bonjour",
            src="en",
            dest="fr",
        )
        self.path.write_text(
            json.dumps(valid.to_dict()) + "\n"
            "this is not json\n"
            '{"text": "missing fields"}\n'
            + json.dumps({**valid.to_dict(), "id": "2", "text": "Later"}) + "\n",
            encoding="utf-8",
        )

        entries = HistoryStore(self.path).entries()
        self.assertEqual([entry.id for entry in entries], ["2", "1"])

    def test_unicode_round_trip(self):
        store = HistoryStore(self.path)
        store.record(_translation(text="こんにちは", translated="Bonjour 👋"))

        entry = HistoryStore(self.path).entries()[0]
        self.assertEqual(entry.text, "こんにちは")
        self.assertEqual(entry.translation, "Bonjour 👋")

    def test_file_permissions_are_private(self):
        store = HistoryStore(self.path)
        store.record(_translation())

        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)


class ProviderNameTest(unittest.TestCase):
    def test_pretty_name_preferred(self):
        provider = type("Provider", (), {"name": "google", "prettyname": "Google Translate"})()
        self.assertEqual(provider_display_name(provider), "Google Translate")

    def test_missing_provider(self):
        self.assertEqual(provider_display_name(None), "")


if __name__ == "__main__":
    unittest.main()
