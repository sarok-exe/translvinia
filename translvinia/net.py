# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pure Python networking helpers shared by providers and the UI."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

TRANSIENT_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})
"""HTTP statuses that are considered worth retrying."""

_STATUS_DESCRIPTIONS = {
    408: "request timeout",
    425: "too early",
    429: "rate limited",
    500: "server error",
    502: "bad gateway",
    503: "service unavailable",
    504: "gateway timeout",
}


@dataclass(frozen=True)
class RetryPolicy:
    """Retry delays for transient request failures."""

    max_attempts: int = 3
    """Total number of attempts, including the first one."""

    base_delay: float = 0.75
    """Delay before the first retry, in seconds."""

    max_delay: float = 8.0
    """Maximum delay between attempts, in seconds."""

    jitter: float = 0.25
    """Relative jitter applied to computed delays, e.g. 0.25 means +/- 25%."""

    def delay(self, attempt: int, retry_after: float | None = None) -> float:
        """
        Get the delay before the next attempt.

        Args:
            attempt: 1-based number of the attempt that just failed.
            retry_after: Server-provided delay, in seconds, if any.

        Returns:
            The delay in seconds.
        """
        if retry_after is not None:
            # Respect server-provided Retry-After exactly, without jitter.
            return min(max(float(retry_after), 0.0), self.max_delay)

        exponent = max(attempt - 1, 0)
        delay = min(self.base_delay * (2**exponent), self.max_delay)

        jitter_amount = delay * self.jitter
        delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0.0, min(delay, self.max_delay))


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """
    Parse an HTTP ``Retry-After`` header.

    Args:
        value: Header value, either delta-seconds or an HTTP-date.
        now: Reference time for HTTP-dates. Defaults to the current UTC time.

    Returns:
        Seconds to wait (never negative), or None if absent or invalid.
    """
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        if not math.isfinite(seconds):
            return None
        return max(seconds, 0.0)

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if retry_at is None:
        return None

    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    return max((retry_at - now).total_seconds(), 0.0)


def is_transient_status(status: int) -> bool:
    """Return whether an HTTP status is worth retrying."""
    return status in TRANSIENT_HTTP_STATUSES


def describe_status(status: int) -> str:
    """Return a short human readable description of an HTTP status."""
    return _STATUS_DESCRIPTIONS.get(status, f"HTTP {status}")
