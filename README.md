<img height="128" src="data/io.github.sarok_exe.Translvinia.svg" align="left"/>

# Translvinia

A translation app for GNOME.

Translvinia is based on [Dialect](https://github.com/dialect-app/dialect) by
The Dialect Authors, and this fork is maintained by
[sarok-exe](https://github.com/sarok-exe). The original project's
GPL-3.0-or-later license and attribution are preserved.

![Translvinia](preview.png?raw=true)

## Translation Providers

- Proprietary:
    - [Google Translate](https://translate.google.com/)
    - [DeepL](https://www.deepl.com/en/translator) - Requires a Free or Paid API key.
    - [Kagi Translate](https://translate.kagi.com/) - Requires session token (not complete URL) from [Kagi settings](https://kagi.com/settings/user_details) as API Key.
    - [Microsoft Translator (Bing)](https://www.bing.com/translator)
    - [Yandex Translate](https://translate.yandex.com/)
- Open Source:
    - LibreTranslate - Use any public instance, defaults to [our own](https://lt.dialectapp.org/).
    - Lingva Translate - Use any public instance, defaults to [our own](https://lingva.dialectapp.org/).

## Features

- Persistent translation history, searchable and available after restarts
- Automatic language detection
- Text to speech
- Clipboard buttons
- Resilient network layer:
    - Per-request timeout instead of hanging forever
    - Automatic retries with exponential backoff and jitter for transient
      HTTP statuses and network failures
    - Honours `Retry-After` from rate-limited providers
    - Clear inline error banner with a Retry action, even for malformed
      or non-JSON provider responses
    - Stale results are discarded when a newer translation starts

## Installation

Translvinia is a fork and is not currently published on Flathub or packaged by
Linux distributions. Build it from source using the instructions below.

## Building

### Requirements

- Python 3 (>=3.10) `python`
- PyGObject (>=3.51.0) `python-gobject`
- GTK4 (>= 4.17.5) `gtk4`
- libadwaita (>= 1.7.0) `libadwaita`
- libsoup (>= 3.0) `libsoup`
- libsecret
- libspelling
- GStreamer 1.0 `gstreamer`
- Meson `meson`
- Ninja `ninja`
- Blueprint compiler `blueprint-compiler`
- gTTS `python-gtts`
- Beautiful Soup `python-beautifulsoup4`

If official packages are not available for any of the python dependencies, you can install them from pip:

```bash
pip install gtts
```

### Building from Git

Install for the current user without root:

```bash
git clone --recurse-submodules https://github.com/sarok-exe/translvinia.git
cd translvinia
meson setup builddir --prefix="$HOME/.local"
meson compile -C builddir
meson install -C builddir
```

This installs the launcher to `~/.local/bin/translvinia`, the desktop entry
to `~/.local/share/applications`, and the icons and GSettings schema under
`~/.local/share`. Make sure `~/.local/bin` is on your `PATH`.

For a system-wide install:

```bash
meson setup builddir --prefix=/usr/local
sudo meson install -C builddir
```

For testing and development purposes, you may run a local build:

```bash
git clone --recurse-submodules https://github.com/sarok-exe/translvinia.git
cd Translvinia
meson builddir
meson configure builddir -Dprefix=$(pwd)/builddir/testdir
ninja -C builddir install
ninja -C builddir run
```

Run the network-layer unit tests from the repository root:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

### Translations

Translvinia reuses the upstream Dialect translations (see the [translations repository](https://github.com/dialect-app/po/blob/main/README.md) file). Please help translate the shared strings into more languages through [Weblate](https://hosted.weblate.org/engage/dialect/).

<a href="https://hosted.weblate.org/engage/dialect/">
<img src="https://hosted.weblate.org/widgets/dialect/-/dialect/multi-auto.svg" alt="Translation status" />
</a>

## License

[GNU General Public License 3 or later](https://www.gnu.org/licenses/gpl-3.0.en.html)
