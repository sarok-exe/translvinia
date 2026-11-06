# Copyright 2026 Translvinia contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from support import install_define_stub

install_define_stub()

from translvinia.providers.errors import (
    InvalidResponse,
    NetworkError,
    ProviderError,
    RateLimitError,
    RequestError,
    RequestTimeout,
)


class ErrorHierarchyTest(unittest.TestCase):
    def test_timeout_is_a_request_error(self):
        self.assertTrue(issubclass(RequestTimeout, RequestError))

    def test_network_error_is_a_request_error(self):
        self.assertTrue(issubclass(NetworkError, RequestError))

    def test_rate_limit_is_a_provider_error(self):
        self.assertTrue(issubclass(RateLimitError, ProviderError))

    def test_invalid_response_is_a_provider_error(self):
        self.assertTrue(issubclass(InvalidResponse, ProviderError))

    def test_provider_errors_are_not_request_errors(self):
        self.assertFalse(issubclass(RateLimitError, RequestError))
        self.assertFalse(issubclass(InvalidResponse, RequestError))


if __name__ == "__main__":
    unittest.main()
