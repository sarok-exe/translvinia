# Copyright 2022 Mufeed Ali
# Copyright 2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
from asyncio import sleep
from typing import Any

from gi.repository import Gio, GLib, Soup

from translvinia.net import (
    TRANSIENT_HTTP_STATUSES,
    RetryPolicy,
    describe_status,
    parse_retry_after,
)
from translvinia.providers.base import BaseProvider
from translvinia.providers.errors import (
    InvalidResponse,
    NetworkError,
    RateLimitError,
    RequestError,
    RequestTimeout,
    UnexpectedError,
)
from translvinia.session import Session

_IO_ERROR_QUARK = Gio.io_error_quark()
_TLS_ERROR_QUARK = GLib.quark_from_string("g-tls-error-quark")
_RESOLVER_ERROR_QUARK = GLib.quark_from_string("g-resolver-error-quark")

_NETWORK_ERROR_CODES = frozenset(
    {
        int(Gio.IOErrorEnum.CONNECTION_REFUSED),
        int(Gio.IOErrorEnum.NETWORK_UNREACHABLE),
        int(Gio.IOErrorEnum.HOST_UNREACHABLE),
        int(Gio.IOErrorEnum.CONNECTION_CLOSED),
        int(Gio.IOErrorEnum.BROKEN_PIPE),
        int(Gio.IOErrorEnum.WOULD_BLOCK),
        int(Gio.IOErrorEnum.NOT_CONNECTED),
        int(Gio.IOErrorEnum.PROXY_FAILED),
        int(Gio.IOErrorEnum.PROXY_AUTH_FAILED),
        int(Gio.IOErrorEnum.PROXY_NOT_ALLOWED),
    }
)


class SoupProvider(BaseProvider):
    """Base class for providers needing libsoup helpers"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.retry_errors: tuple[int, ...] = tuple(sorted(TRANSIENT_HTTP_STATUSES))
        """ Error codes that should be retried automatically """
        self.max_retries = 2
        """ Max number of retries after the initial attempt """
        self.retry_policy = RetryPolicy(max_attempts=self.max_retries + 1)
        """ Policy controlling delays between attempts """

    def encode_data(self, data: Any) -> GLib.Bytes | None:
        """
        Convert Python data to JSON and bytes.

        Args:
            data: Data to encode, anything json.dumps can handle.

        Returns:
            The GLib Bytes or None if something failed.
        """
        data_glib_bytes = None
        try:
            data_bytes = json.dumps(data).encode("utf-8")
            data_glib_bytes = GLib.Bytes.new(data_bytes)
        except Exception as exc:
            logging.warning(exc)
        return data_glib_bytes

    def create_message(
        self, method: str, url: str, data: Any = {}, headers: dict = {}, form: bool = False
    ) -> Soup.Message:
        """
        Create a Soup's message.

        Encodes data and adds it to the message as the request body.

        Args:
            method: HTTP method of the message.
            url: Url of the message.
            data: Request body or form data.
            headers: HTTP headers of the message.
            form: If the data should be encoded as ``application/x-www-form-urlencoded``.

        Returns:
            The Soup Message for the given parameters.
        """

        if form and data:
            form_data = Soup.form_encode_hash(data)
            message = Soup.Message.new_from_encoded_form(method, url, form_data)
        else:
            message = Soup.Message.new(method, url)

        if message:
            if data and not form:
                data = self.encode_data(data)
                message.set_request_body_from_bytes("application/json", data)
            if headers:
                for name, value in headers.items():
                    message.get_request_headers().append(name, value)
            if "User-Agent" not in headers:
                message.get_request_headers().append("User-Agent", "Translvinia")

        return message  # type: ignore

    async def send_and_read(self, message: Soup.Message) -> bytes | None:
        """
        Helper method for Soup's send_and_read_async.

        Args:
            message: Message to send.

        Returns:
            The bytes of the response or None.
        """
        response: GLib.Bytes = await Session.get().send_and_read_async(message, 0)  # type: ignore
        return response.get_data() if response else None

    async def send_and_read_json(self, message: Soup.Message) -> Any:
        """
        Like ``SoupProvider.send_and_read`` but returns JSON parsed.

        Args:
            message: Message to send.

        Returns:
            The JSON of the response deserialized to a python object.
        """
        response = await self.send_and_read(message)
        return json.loads(response) if response else {}

    def check_known_errors(self, status: Soup.Status, data: Any) -> None:
        """
        Checks data for possible response errors and raises appropriated exceptions.

        This should be implemented by subclases.

        Args:
            status: HTTP status.
            data: Response body data.
        """

    @staticmethod
    def _request_host(message: Soup.Message) -> str:
        """Get a host name for error messages, falling back to a generic label."""
        try:
            uri = message.get_uri()
            host = uri.get_host() if uri else None
        except Exception:  # noqa: BLE001 - never let diagnostics break a request
            host = None
        return host or "provider"

    @staticmethod
    def _body_snippet(data: bytes, limit: int = 180) -> str:
        """Collapse a response body into a short single-line snippet."""
        text = data.decode("utf-8", errors="replace")
        text = " ".join(text.split())
        if len(text) > limit:
            text = text[: limit - 3].rstrip() + "..."
        return text

    def _classify_error(self, exc: GLib.Error) -> tuple[RequestError, bool, str]:
        """
        Convert a GLib error into a provider error.

        Returns:
            A tuple with the error to raise, whether it is retryable and a short reason.
        """
        message = exc.message or "request failed"
        domain = exc.domain
        if isinstance(domain, str):
            domain = GLib.quark_from_string(domain)
        code = int(exc.code)

        if domain == _TLS_ERROR_QUARK:
            return NetworkError(f"TLS error: {message}"), False, "TLS error"

        if domain == _RESOLVER_ERROR_QUARK:
            return NetworkError(f"name resolution failed: {message}"), True, "name resolution failure"

        if domain == _IO_ERROR_QUARK:
            if code == int(Gio.IOErrorEnum.TIMED_OUT):
                return RequestTimeout("Request timed out"), True, "timeout"
            if code == int(Gio.IOErrorEnum.CANCELLED):
                return RequestError("Request cancelled"), False, "cancelled"
            if code in _NETWORK_ERROR_CODES:
                return NetworkError(message), True, "network error"

        return RequestError(message), False, message

    def _log_retry(self, attempt: int, reason: str, delay: float) -> None:
        """Log a retry attempt with provider, attempt, reason and delay."""
        logging.warning(
            "%s: attempt %d/%d failed (%s), retrying in %.2fs",
            self.prettyname or self.name or self.__class__.__name__,
            attempt,
            self.retry_policy.max_attempts,
            reason,
            delay,
        )

    def _process_response(
        self,
        message: Soup.Message,
        status: int,
        raw: bytes | None,
        check_common: bool,
        return_json: bool,
    ) -> Any:
        """Parse and validate a response body, raising provider errors when needed."""
        body = raw or b""

        if return_json:
            try:
                text = body.decode("utf-8")
            except UnicodeDecodeError:
                # Keep diagnostics going; JSON parsing below will reject it.
                text = body.decode("utf-8", errors="replace")

            try:
                data = json.loads(text) if text.strip() else {}
            except json.JSONDecodeError as exc:
                # Let providers recognize their own error payloads first.
                self.check_known_errors(status, {})
                host = self._request_host(message)
                snippet = self._body_snippet(body)
                raise InvalidResponse(f"HTTP {status} from {host}: invalid JSON response: {snippet}") from exc
        else:
            data = body

        if check_common:
            self.check_known_errors(status, data)

        if status >= 400:
            host = self._request_host(message)
            if status == 429:
                raise RateLimitError(f"HTTP 429 from {host}: rate limit reached")
            raise UnexpectedError(f"HTTP {status} from {host}")

        return data

    async def send_and_read_and_process(
        self,
        message: Soup.Message,
        check_common: bool = True,
        return_json: bool = True,
    ) -> Any:
        """
        Helper mixing ``SoupProvider.send_and_read``, ``SoupProvider.send_and_read_json``
        and ``SoupProvider.check_known_errors``.

        This is a thin single-attempt helper kept for compatibility. Public requests
        should use ``SoupProvider.request``, which adds retries.

        Args:
            message: Message to send.
            check_common: If response data should be checked for errors using check_known_errors.
            return_json: If the response should be parsed as JSON.

        Returns:
            The JSON deserialized to a python object or bytes if ``json`` is ``False``.
        """
        try:
            response = await self.send_and_read(message)
        except GLib.Error as exc:
            error, _retryable, _reason = self._classify_error(exc)
            raise error from exc

        return self._process_response(message, int(message.get_status()), response, check_common, return_json)

    async def request(
        self,
        method: str,
        url: str,
        data: Any = {},
        headers: dict = {},
        form: bool = False,
        check_common: bool = True,
        return_json: bool = True,
    ) -> Any:
        """
        Helper for regular HTTP request.

        Retries transient HTTP statuses and network failures using a fresh message
        per attempt and an exponential backoff policy.

        Args:
            method: HTTP method of the request.
            url: Url of the request.
            data: Request body or form data.
            headers: HTTP headers of the message.
            form: If the data should be encoded as a form.
            check_common: If response data should be checked for errors using check_known_errors.
            return_json: If the response should be parsed as JSON.

        Returns:
            The JSON deserialized to a python object or bytes if ``json`` is ``False``.
        """
        attempt = 1

        while True:
            # A fresh message per attempt avoids stale statuses and headers.
            message = self.create_message(method, url, data, headers, form)

            try:
                response = await self.send_and_read(message)
            except GLib.Error as exc:
                error, retryable, reason = self._classify_error(exc)

                if retryable and attempt < self.retry_policy.max_attempts:
                    delay = self.retry_policy.delay(attempt)
                    self._log_retry(attempt, reason, delay)
                    await sleep(delay)
                    attempt += 1
                    continue

                raise error from exc

            status = int(message.get_status())

            if status in self.retry_errors and attempt < self.retry_policy.max_attempts:
                retry_after = parse_retry_after(message.get_response_headers().get_one("Retry-After"))
                delay = self.retry_policy.delay(attempt, retry_after)
                self._log_retry(attempt, f"HTTP {status} {describe_status(status)}", delay)
                await sleep(delay)
                attempt += 1
                continue

            return self._process_response(message, status, response, check_common, return_json)

    async def get(
        self,
        url: str,
        headers: dict = {},
        check_common: bool = True,
        return_json: bool = True,
    ) -> Any:
        """
        Helper for GET HTTP request.

        Args:
            url: Url of the request.
            headers: HTTP headers of the message.
            check_common: If response data should be checked for errors using check_known_errors.
            return_json: If the response should be parsed as JSON.

        Returns:
            The JSON deserialized to a python object or bytes if ``json`` is ``False``.
        """
        return await self.request("GET", url, headers=headers, check_common=check_common, return_json=return_json)

    async def post(
        self,
        url: str,
        data: Any = {},
        headers: dict = {},
        form: bool = False,
        check_common: bool = True,
        return_json: bool = True,
    ) -> Any:
        """
        Helper for POST HTTP request.

        Args:
            url: Url of the request.
            data: Request body or form data.
            headers: HTTP headers of the message.
            form: If the data should be encoded as a form.
            check_common: If response data should be checked for errors using check_known_errors.
            return_json: If the response should be parsed as JSON.

        Returns:
            The JSON deserialized to a python object or bytes if ``json`` is ``False``.
        """
        return await self.request("POST", url, data, headers, form, check_common, return_json)
