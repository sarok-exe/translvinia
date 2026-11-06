# Copyright 2024 Mufeed Ali
# Copyright 2024 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later


def translation_matches(original, *, src: str | None, dest: str | None, text: str) -> bool:
    """
    Check if a translation request still matches the current UI state.

    Args:
        original: TranslationRequest-like object with ``src``, ``dest`` and ``text``.
        src: Currently selected source language.
        dest: Currently selected destination language.
        text: Current source text.
    """
    if original.dest != dest or original.text != text:
        return False

    return src == "auto" or not original.src or original.src == src


def find_item_match(list1: list[str], list2: list[str]) -> str | None:
    """
    Get the first occurrence in two lists.

    Args:
        list1: List to iterate
        list2: List to check against
    """
    set_to_check = set(list2)
    return next((i for i in list1 if i in set_to_check), None)


def first_exclude(list_: list[str], exclude: str) -> str | None:
    """
    Get the first item that is not excluded.

    Args:
        list_: List of items
        exclude: Item to ignore
    """
    return next((x for x in list_ if x != exclude), None)
