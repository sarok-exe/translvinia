# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""Browse and copy the persistent translation history."""

from __future__ import annotations

from datetime import datetime

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from translvinia.history import HistoryEntry
from translvinia.languages import get_lang_name


class HistoryItem(GObject.Object):
    """A list item wrapping one persistent history entry."""

    __gtype_name__ = "TranslviniaHistoryItem"

    def __init__(self, entry: HistoryEntry):
        super().__init__()
        self.entry = entry


def _language_name(code: str) -> str:
    if not code:
        return _("Unknown")
    if code == "auto":
        return _("Auto")
    return get_lang_name(code) or code


def _format_timestamp(value: str) -> str:
    try:
        timestamp = datetime.fromisoformat(value)
        return timestamp.astimezone().strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return value


class HistoryRow(Adw.ActionRow):
    """An action row showing one translation and its copy buttons."""

    __gtype_name__ = "TranslviniaHistoryRow"

    def __init__(self, on_copy):
        super().__init__()
        self.entry: HistoryEntry | None = None
        self._on_copy = on_copy

        self.set_activatable(False)
        self.set_title_lines(1)
        self.set_subtitle_lines(3)
        self.set_use_markup(False)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_valign(Gtk.Align.CENTER)

        self.copy_source_btn = Gtk.Button(icon_name="edit-copy-symbolic", tooltip_text=_("Copy original text"))
        self.copy_source_btn.add_css_class("flat")
        self.copy_source_btn.connect("clicked", self._on_copy_source)
        button_box.append(self.copy_source_btn)

        self.copy_translation_btn = Gtk.Button(
            icon_name="edit-copy-symbolic", tooltip_text=_("Copy translated text")
        )
        self.copy_translation_btn.add_css_class("flat")
        self.copy_translation_btn.connect("clicked", self._on_copy_translation)
        button_box.append(self.copy_translation_btn)

        self.add_suffix(button_box)

    def bind(self, entry: HistoryEntry):
        self.entry = entry
        self.set_title(entry.text)

        languages = f"{_language_name(entry.src)} → {_language_name(entry.dest)}"
        metadata = [_format_timestamp(entry.timestamp), languages]
        if entry.provider:
            metadata.append(entry.provider)
        if entry.detected and entry.src == "auto":
            metadata.append(_("Detected: {language}").format(language=_language_name(entry.detected)))

        self.set_subtitle(f"{entry.translation}\n{' · '.join(metadata)}")
        self.copy_source_btn.set_sensitive(bool(entry.text))
        self.copy_translation_btn.set_sensitive(bool(entry.translation))

    def _on_copy_source(self, *_args):
        if self.entry and self.entry.text:
            self._on_copy(self.entry.text, _("Original text copied"))

    def _on_copy_translation(self, *_args):
        if self.entry and self.entry.translation:
            self._on_copy(self.entry.translation, _("Translation copied"))


class HistoryDialog(Adw.Dialog):
    """A searchable window over the complete persistent history."""

    __gtype_name__ = "TranslviniaHistoryDialog"

    def __init__(self, entries: list[HistoryEntry], parent: Gtk.Widget | None = None):
        super().__init__()
        self.set_title(_("Translation History"))
        self.set_content_width(780)
        self.set_content_height(620)

        self._store = Gio.ListStore(item_type=HistoryItem)
        for entry in entries:
            self._store.append(HistoryItem(entry))

        self._search = Gtk.SearchEntry(placeholder_text=_("Search translations"))
        self._search.connect("search-changed", self._on_search_changed)

        self._filter = Gtk.CustomFilter.new(self._filter_entry)
        self._filter_model = Gtk.FilterListModel(model=self._store, filter=self._filter)
        selection = Gtk.NoSelection(model=self._filter_model)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_list_item)
        factory.connect("bind", self._bind_list_item)
        self._list_view = Gtk.ListView(model=selection, factory=factory)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self._list_view)
        scrolled.set_vexpand(True)

        self._empty_page = Adw.StatusPage(
            icon_name="document-open-recent-symbolic",
            title=_("No translations yet"),
            description=_("Completed translations will appear here."),
            vexpand=True,
        )

        self._stack = Gtk.Stack()
        self._stack.add_named(scrolled, "list")
        self._stack.add_named(self._empty_page, "empty")

        toolbar = Adw.ToolbarView()
        toolbar.set_content(self._stack)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=_("Translation History")))
        close_button = Gtk.Button(icon_name="window-close-symbolic", tooltip_text=_("Close"))
        close_button.connect("clicked", lambda *_: self.close())
        header.pack_end(close_button)
        toolbar.add_top_bar(header)

        toolbar.add_top_bar(self._search)

        self._count_label = Gtk.Label(xalign=0)
        self._count_label.add_css_class("dim-label")
        self._count_label.add_css_class("caption")
        self._count_label.set_margin_start(12)
        self._count_label.set_margin_end(12)
        self._count_label.set_margin_top(6)
        self._count_label.set_margin_bottom(6)
        toolbar.add_bottom_bar(self._count_label)

        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(toolbar)
        self.set_child(self._toast_overlay)

        self._update_view()
        if parent is not None:
            self.present(parent)

    def _filter_entry(self, item: HistoryItem) -> bool:
        query = self._search.get_text().strip().casefold()
        if not query:
            return True
        entry = item.entry
        searchable = " ".join(
            [
                entry.text,
                entry.translation,
                entry.src,
                entry.dest,
                entry.detected or "",
                entry.provider,
            ]
        ).casefold()
        return query in searchable

    def _setup_list_item(self, _factory, list_item: Gtk.ListItem):
        list_item.set_child(HistoryRow(self._copy))

    def _bind_list_item(self, _factory, list_item: Gtk.ListItem):
        list_item.get_child().bind(list_item.get_item().entry)

    def _on_search_changed(self, *_args):
        self._filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_view()

    def _update_view(self):
        total = self._store.get_n_items()
        visible = self._filter_model.get_n_items()

        if total == 0:
            self._empty_page.set_title(_("No translations yet"))
            self._empty_page.set_description(_("Completed translations will appear here."))
            self._stack.set_visible_child_name("empty")
        elif visible == 0:
            self._empty_page.set_title(_("No matching translations"))
            self._empty_page.set_description(_("Try a different search term."))
            self._stack.set_visible_child_name("empty")
        else:
            self._stack.set_visible_child_name("list")

        if self._search.get_text().strip():
            self._count_label.set_label(_("{visible} of {total} translations").format(visible=visible, total=total))
        else:
            self._count_label.set_label(_("{count} translations").format(count=total))

    def _copy(self, text: str, message: str):
        display = Gdk.Display.get_default()
        if display is None:
            return
        display.get_clipboard().set(text)
        self._toast_overlay.add_toast(Adw.Toast.new(message, timeout=2))
