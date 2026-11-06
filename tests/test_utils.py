# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from dataclasses import dataclass

from translvinia.utils import translation_matches


@dataclass
class _Original:
    text: str
    src: str
    dest: str


class TranslationMatchesTest(unittest.TestCase):
    def test_same_source(self):
        original = _Original("hola", "es", "en")
        self.assertTrue(translation_matches(original, src="es", dest="en", text="hola"))

    def test_auto_source_matches_any_detected_source(self):
        original = _Original("hola", "es", "en")
        self.assertTrue(translation_matches(original, src="auto", dest="en", text="hola"))

    def test_different_source_does_not_match(self):
        original = _Original("hola", "es", "en")
        self.assertFalse(translation_matches(original, src="fr", dest="en", text="hola"))

    def test_different_destination_does_not_match(self):
        original = _Original("hola", "es", "en")
        self.assertFalse(translation_matches(original, src="es", dest="fr", text="hola"))

    def test_different_text_does_not_match(self):
        original = _Original("hola", "es", "en")
        self.assertFalse(translation_matches(original, src="es", dest="en", text="adios"))


if __name__ == "__main__":
    unittest.main()
