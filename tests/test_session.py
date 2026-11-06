# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

try:
    import gi

    gi.require_version("Soup", "3.0")
    from translvinia.session import Session
except (ImportError, ValueError):  # pragma: no cover - depends on host packages
    Session = None


@unittest.skipIf(Session is None, "PyGObject/libsoup unavailable")
class SessionDefaultsTest(unittest.TestCase):
    def test_request_timeout_is_bounded(self):
        self.assertEqual(Session.get().props.timeout, 15)

    def test_idle_timeout(self):
        self.assertEqual(Session.get().props.idle_timeout, 60)

    def test_connection_pool_is_larger_than_two(self):
        self.assertEqual(Session.get().props.max_conns_per_host, 6)

    def test_user_agent_identifies_fork(self):
        self.assertEqual(Session.get().props.user_agent, "Translvinia")


if __name__ == "__main__":
    unittest.main()
