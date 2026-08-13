"""Bounded HTTP(S) acquisition with SSRF-resistant DNS pinning."""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import ssl
from collections.abc import AsyncIterable, AsyncIterator, Iterable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol, cast
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpcore2
import httpx2

from jobhunter.jobs.application.errors import (
    InvalidJobUrlContentError,
    JobUrlFetchError,
    UnsafeJobUrlError,
)
from jobhunter.jobs.application.normalization import job_content_fingerprint
from jobhunter.jobs.domain.acquisition import FetchedJobContent

_ALLOWED_MEDIA_TYPES = {"text/html", "text/plain", "application/xhtml+xml"}
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_HTTPS_PORT = 443
_SUCCESS_MINIMUM = 200
_REDIRECT_MINIMUM = 300
_NO_PUBLIC_ADDRESS = "No public address available"
_UNIX_SOCKETS_DISABLED = "Unix sockets are disabled"
_MAX_URL_CHARACTERS = 2_048
_MAX_REDIRECT_LIMIT = 10
_SPACE = re.compile(r"[ \t\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_SKIPPED_ELEMENTS = {"script", "style", "noscript", "template", "svg", "canvas"}
_BLOCK_ELEMENTS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}


@dataclass(frozen=True, slots=True)
class JobUrlFetchLimits:
    """Operational bounds applied to every URL and redirect hop."""

    max_redirects: int = 5
    max_response_bytes: int = 2 * 1024 * 1024
    max_extracted_characters: int = 100_000
    connect_timeout_seconds: float = 5
    read_timeout_seconds: float = 10
    total_timeout_seconds: float = 20

    def __post_init__(self) -> None:
        if not 0 <= self.max_redirects <= _MAX_REDIRECT_LIMIT:
            raise ValueError("invalid_job_url_redirect_limit")
        if self.max_response_bytes <= 0 or self.max_extracted_characters <= 0:
            raise ValueError("invalid_job_url_content_limit")
        if (
            min(
                self.connect_timeout_seconds,
                self.read_timeout_seconds,
                self.total_timeout_seconds,
            )
            <= 0
        ):
            raise ValueError("invalid_job_url_timeout")


@dataclass(frozen=True, slots=True)
class ValidatedJobUrl:
    url: str
    hostname: str
    port: int
    addresses: tuple[str, ...]


class HostResolver(Protocol):
    async def resolve(self, hostname: str, port: int) -> tuple[str, ...]: ...


class SystemHostResolver:
    """Resolve both IPv4 and IPv6 without making an HTTP request."""

    async def resolve(self, hostname: str, port: int) -> tuple[str, ...]:
        loop = asyncio.get_running_loop()
        try:
            records = await loop.getaddrinfo(
                hostname,
                port,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as error:
            raise JobUrlFetchError("job_url_dns_failed") from error
        return tuple(dict.fromkeys(record[4][0] for record in records))


class SafeJobUrlPolicy:
    """Accept only public HTTP(S) destinations on their standard ports."""

    def __init__(self, resolver: HostResolver) -> None:
        self._resolver = resolver

    async def validate(self, value: str) -> ValidatedJobUrl:
        if len(value) > _MAX_URL_CHARACTERS:
            raise UnsafeJobUrlError("invalid_job_url")
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as error:
            raise UnsafeJobUrlError("invalid_job_url") from error
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise UnsafeJobUrlError("unsupported_job_url")
        if parsed.username is not None or parsed.password is not None or parsed.fragment:
            raise UnsafeJobUrlError("job_url_credentials_or_fragment")
        expected_port = 443 if parsed.scheme.lower() == "https" else 80
        resolved_port = port or expected_port
        if resolved_port != expected_port:
            raise UnsafeJobUrlError("job_url_nonstandard_port")

        hostname = parsed.hostname.rstrip(".").lower()
        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise UnsafeJobUrlError("non_public_job_url")
        addresses = await self._resolver.resolve(hostname, resolved_port)
        if not addresses or any(not _is_public_ip(address) for address in addresses):
            raise UnsafeJobUrlError("non_public_job_url")
        normalized_hostname = f"[{hostname}]" if ":" in hostname else hostname
        normalized = urlunsplit(
            (
                parsed.scheme.lower(),
                normalized_hostname,
                parsed.path or "/",
                parsed.query,
                "",
            )
        )
        return ValidatedJobUrl(normalized, hostname, resolved_port, addresses)


def _is_public_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


class PinnedNetworkBackend(httpcore2.AsyncNetworkBackend):
    """Resolve, validate, then connect to that exact address to prevent rebinding."""

    def __init__(
        self,
        policy: SafeJobUrlPolicy,
        backend: httpcore2.AsyncNetworkBackend | None = None,
    ) -> None:
        self._policy = policy
        self._backend = backend or httpcore2.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,  # noqa: ASYNC109 - interface parameter
        local_address: str | None = None,
        socket_options: Iterable[httpcore2.SOCKET_OPTION] | None = None,
    ) -> httpcore2.AsyncNetworkStream:
        if port not in {80, _HTTPS_PORT}:
            raise UnsafeJobUrlError("job_url_nonstandard_port")
        addresses: tuple[str, ...]
        if _is_public_ip(host):
            addresses = (host,)
        else:
            scheme = "https" if port == _HTTPS_PORT else "http"
            addresses = (await self._policy.validate(f"{scheme}://{host}")).addresses
        last_error: httpcore2.NetworkError | None = None
        for address in addresses:
            try:
                return await self._backend.connect_tcp(
                    address,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except httpcore2.NetworkError as error:
                last_error = error
        if last_error is not None:
            raise last_error
        raise httpcore2.ConnectError(_NO_PUBLIC_ADDRESS)  # pragma: no cover - policy rejects empty

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,  # noqa: ASYNC109 - interface parameter
        socket_options: Iterable[httpcore2.SOCKET_OPTION] | None = None,
    ) -> httpcore2.AsyncNetworkStream:
        del path, timeout, socket_options
        raise httpcore2.UnsupportedProtocol(_UNIX_SOCKETS_DISABLED)

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


class _CoreResponseStream(httpx2.AsyncByteStream):
    def __init__(self, stream: AsyncIterable[bytes]) -> None:
        self._stream = stream

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self._stream:
            yield chunk

    async def aclose(self) -> None:
        close = getattr(self._stream, "aclose", None)
        if close is not None:
            await close()


class PinnedAsyncHttpTransport(httpx2.AsyncBaseTransport):
    """Small public-httpcore adapter that installs the pinned network backend."""

    def __init__(self, network_backend: PinnedNetworkBackend) -> None:
        self._pool = httpcore2.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(),
            max_connections=10,
            max_keepalive_connections=0,
            http1=True,
            http2=False,
            network_backend=network_backend,
        )

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        response = await self._pool.handle_async_request(
            httpcore2.Request(
                method=request.method,
                url=httpcore2.URL(
                    scheme=request.url.raw_scheme,
                    host=request.url.raw_host,
                    port=request.url.port,
                    target=request.url.raw_path,
                ),
                headers=request.headers.raw,
                content=request.stream,
                extensions=request.extensions,
            )
        )
        return httpx2.Response(
            status_code=response.status,
            headers=response.headers,
            stream=_CoreResponseStream(cast(AsyncIterable[bytes], response.stream)),
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()


class _JobHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.canonical_href: str | None = None
        self._skipped_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in _SKIPPED_ELEMENTS:
            self._skipped_depth += 1
            return
        if self._skipped_depth:
            return
        attributes = {name.lower(): value for name, value in attrs}
        rel = set((attributes.get("rel") or "").lower().split())
        if lowered == "link" and "canonical" in rel and attributes.get("href"):
            self.canonical_href = attributes["href"]
        if lowered in _BLOCK_ELEMENTS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in _SKIPPED_ELEMENTS:
            self._skipped_depth = max(0, self._skipped_depth - 1)
            return
        if not self._skipped_depth and lowered in _BLOCK_ELEMENTS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skipped_depth:
            self.parts.append(data)


class HttpxJobUrlFetcher:
    """Fetch redirects manually and extract bounded deterministic text."""

    def __init__(
        self,
        *,
        limits: JobUrlFetchLimits,
        resolver: HostResolver | None = None,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._limits = limits
        self._resolver = resolver or SystemHostResolver()
        self._policy = SafeJobUrlPolicy(self._resolver)
        self._transport = transport or PinnedAsyncHttpTransport(PinnedNetworkBackend(self._policy))

    async def fetch(self, url: str) -> FetchedJobContent:
        requested = (await self._policy.validate(url)).url
        current = requested
        timeout = httpx2.Timeout(
            connect=self._limits.connect_timeout_seconds,
            read=self._limits.read_timeout_seconds,
            write=self._limits.read_timeout_seconds,
            pool=self._limits.connect_timeout_seconds,
        )
        try:
            async with asyncio.timeout(self._limits.total_timeout_seconds):
                async with httpx2.AsyncClient(
                    transport=self._transport,
                    follow_redirects=False,
                    timeout=timeout,
                    trust_env=False,
                    headers={"User-Agent": "JobHunter-AI/0.1 (+safe public job import)"},
                ) as client:
                    for redirect_count in range(self._limits.max_redirects + 1):
                        async with client.stream("GET", current) as response:
                            if response.status_code in _REDIRECT_STATUSES:
                                if redirect_count == self._limits.max_redirects:
                                    raise JobUrlFetchError("too_many_job_url_redirects")
                                location = response.headers.get("location")
                                if not location:
                                    raise JobUrlFetchError("job_url_redirect_without_location")
                                candidate = (
                                    await self._policy.validate(urljoin(current, location))
                                ).url
                                if current.startswith("https://") and candidate.startswith(
                                    "http://"
                                ):
                                    raise UnsafeJobUrlError("job_url_https_downgrade")
                                client.cookies.clear()
                                current = candidate
                                continue
                            if not _SUCCESS_MINIMUM <= response.status_code < _REDIRECT_MINIMUM:
                                raise JobUrlFetchError("job_url_http_error")
                            body = await self._read_bounded(response)
                            return self._extract(requested, current, response, body)
        except TimeoutError as error:
            raise JobUrlFetchError("job_url_timeout") from error
        except (httpx2.HTTPError, httpcore2.NetworkError, httpcore2.ProtocolError) as error:
            raise JobUrlFetchError("job_url_request_failed") from error
        raise JobUrlFetchError("job_url_fetch_failed")  # pragma: no cover

    def _extract(
        self,
        requested_url: str,
        final_url: str,
        response: httpx2.Response,
        body: bytes,
    ) -> FetchedJobContent:
        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type not in _ALLOWED_MEDIA_TYPES:
            raise InvalidJobUrlContentError("unsupported_job_url_content_type")
        content_length = response.headers.get("content-length")
        if content_length is not None and (
            not content_length.isdecimal() or int(content_length) > self._limits.max_response_bytes
        ):
            raise InvalidJobUrlContentError("job_url_content_too_large")
        try:
            decoded = body.decode(response.encoding or "utf-8")
        except (LookupError, UnicodeDecodeError) as error:
            raise InvalidJobUrlContentError("invalid_job_url_encoding") from error

        canonical = final_url
        if media_type in {"text/html", "application/xhtml+xml"}:
            parser = _JobHtmlParser()
            parser.feed(decoded)
            text = _normalize_extracted_text("".join(parser.parts))
            canonical = _same_origin_canonical(final_url, parser.canonical_href)
        else:
            text = _normalize_extracted_text(decoded)
        if not text:
            raise InvalidJobUrlContentError("empty_job_url_content")
        if len(text) > self._limits.max_extracted_characters:
            raise InvalidJobUrlContentError("job_url_extracted_text_too_large")
        return FetchedJobContent(
            requested_url=requested_url,
            final_url=final_url,
            canonical_url=canonical,
            raw_text=text,
            content_fingerprint=job_content_fingerprint(text),
            media_type=media_type,
        )

    async def _read_bounded(self, response: httpx2.Response) -> bytes:
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > self._limits.max_response_bytes:
                raise InvalidJobUrlContentError("job_url_content_too_large")
            chunks.append(chunk)
        return b"".join(chunks)


def _normalize_extracted_text(value: str) -> str:
    lines = (_SPACE.sub(" ", line).strip() for line in value.replace("\r", "").split("\n"))
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def _same_origin_canonical(final_url: str, href: str | None) -> str:
    if href is None:
        return final_url
    try:
        candidate = urljoin(final_url, href)
        final = urlsplit(final_url)
        parsed = urlsplit(candidate)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or (parsed.scheme.lower(), parsed.hostname, parsed.port)
            != (final.scheme.lower(), final.hostname, final.port)
        ):
            return final_url
        return urlunsplit(
            (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", parsed.query, "")
        )
    except ValueError:
        return final_url
