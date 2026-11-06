# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

import gi

gi.require_version("Soup", "3.0")

from support import install_define_stub

install_define_stub()

from gi.repository import Gio, GLib

from translvinia.providers.errors import NetworkError, RequestError, RequestTimeout
from translvinia.providers.soup import SoupProvider


def _glib_error(domain: str, code: int, message: str) -> GLib.Error:
    return GLib.Error.new_literal(GLib.quark_from_string(domain), message, code)


class ClassifyErrorTest(unittest.TestCase):
    def setUp(self):
        self.provider = SoupProvider.__new__(SoupProvider)

    def test_timeout_domain_is_a_string(self):
        error = _glib_error("g-io-error-quark", int(Gio.IOErrorEnum.TIMED_OUT), "Socket I/O timed out")
        self.assertEqual(error.domain, "g-io-error-quark")

        classified, retryable, reason = self.provider._classify_error(error)

        self.assertIsInstance(classified, RequestTimeout)
        self.assertTrue(retryable)
        self.assertEqual(reason, "timeout")

    def test_connection_refused_is_retryable_network_error(self):
        error = _glib_error("g-io-error-quark", int(Gio.IOErrorEnum.CONNECTION_REFUSED), "Connection refused")
        classified, retryable, _reason = self.provider._classify_error(error)

        self.assertIsInstance(classified, NetworkError)
        self.assertTrue(retryable)

    def test_tls_error_is_not_retried(self):
        error = _glib_error("g-tls-error-quark", 1, "Handshake failed")
        classified, retryable, _reason = self.provider._classify_error(error)

        self.assertIsInstance(classified, NetworkError)
        self.assertFalse(retryable)

    def test_cancelled_request_is_not_retried(self):
        error = _glib_error("g-io-error-quark", int(Gio.IOErrorEnum.CANCELLED), "Operation was cancelled")
        classified, retryable, _reason = self.provider._classify_error(error)

        self.assertIsInstance(classified, RequestError)
        self.assertNotIsInstance(classified, RequestTimeout)
        self.assertFalse(retryable)


if __name__ == "__main__":
    unittest.main()
