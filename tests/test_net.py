# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from datetime import datetime, timedelta, timezone

from translvinia.net import (
    TRANSIENT_HTTP_STATUSES,
    RetryPolicy,
    describe_status,
    is_transient_status,
    parse_retry_after,
)


class RetryPolicyTest(unittest.TestCase):
    def test_exponential_backoff(self):
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=10.0, jitter=0.0)
        self.assertEqual(policy.delay(1), 1.0)
        self.assertEqual(policy.delay(2), 2.0)
        self.assertEqual(policy.delay(3), 4.0)
        self.assertEqual(policy.delay(4), 8.0)
        self.assertEqual(policy.delay(5), 10.0)

    def test_backoff_is_capped(self):
        policy = RetryPolicy(base_delay=2.0, max_delay=3.0, jitter=0.0)
        for attempt in range(1, 10):
            self.assertLessEqual(policy.delay(attempt), 3.0)

    def test_jitter_stays_within_bounds(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=10.0, jitter=0.25)
        for _ in range(200):
            delay = policy.delay(1)
            self.assertGreaterEqual(delay, 0.75)
            self.assertLessEqual(delay, 1.25)

    def test_retry_after_is_respected_without_jitter(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=10.0, jitter=0.5)
        self.assertEqual(policy.delay(1, retry_after=3), 3.0)
        self.assertEqual(policy.delay(1, retry_after=30), 10.0)
        self.assertEqual(policy.delay(1, retry_after=-5), 0.0)


class ParseRetryAfterTest(unittest.TestCase):
    def test_delta_seconds(self):
        self.assertEqual(parse_retry_after("120"), 120.0)
        self.assertEqual(parse_retry_after("0"), 0.0)
        self.assertEqual(parse_retry_after("-1"), 0.0)

    def test_http_date_in_future(self):
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        value = (now + timedelta(seconds=90)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        self.assertAlmostEqual(parse_retry_after(value, now=now), 90.0, places=1)

    def test_http_date_in_past(self):
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        value = (now - timedelta(seconds=90)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        self.assertEqual(parse_retry_after(value, now=now), 0.0)

    def test_invalid_values(self):
        self.assertIsNone(parse_retry_after(None))
        self.assertIsNone(parse_retry_after(""))
        self.assertIsNone(parse_retry_after("not-a-date"))
        self.assertIsNone(parse_retry_after("nan"))


class StatusTest(unittest.TestCase):
    def test_transient_statuses(self):
        for status in TRANSIENT_HTTP_STATUSES:
            self.assertTrue(is_transient_status(status))
        self.assertFalse(is_transient_status(200))
        self.assertFalse(is_transient_status(404))

    def test_descriptions(self):
        self.assertEqual(describe_status(429), "rate limited")
        self.assertEqual(describe_status(503), "service unavailable")
        self.assertEqual(describe_status(418), "HTTP 418")


if __name__ == "__main__":
    unittest.main()
