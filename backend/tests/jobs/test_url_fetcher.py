"""Security and deterministic extraction tests for URL acquisition."""

import asyncio
import socket
from collections.abc import AsyncIterator, Iterable

import httpcore2
import httpx2
import pytest

from jobhunter.jobs.application.errors import (
    InvalidJobUrlContentError,
    JobUrlFetchError,
    UnsafeJobUrlError,
)
from jobhunter.jobs.domain.acquisition import FetchedJobContent
from jobhunter.jobs.domain.offers import SHA256_LENGTH
from jobhunter.jobs.infrastructure.url_fetcher import (
    HttpxJobUrlFetcher,
    JobUrlFetchLimits,
    PinnedAsyncHttpTransport,
    PinnedNetworkBackend,
    SafeJobUrlPolicy,
    SystemHostResolver,
    _CoreResponseStream,
    _is_public_ip,
    _same_origin_canonical,
)

PUBLIC_IP = "93.184.216.34"
SECOND_PUBLIC_IP = "2606:2800:220:1:248:1893:25c8:1946"


class FakeResolver:
    def __init__(self, addresses: dict[str, tuple[str, ...]] | None = None) -> None:
        self.addresses = addresses or {"jobs.example.com": (PUBLIC_IP,)}
        self.calls: list[tuple[str, int]] = []

    async def resolve(self, hostname: str, port: int) -> tuple[str, ...]:
        self.calls.append((hostname, port))
        return self.addresses.get(hostname, ())


def make_fetcher(
    handler: httpx2.AsyncBaseTransport,
    *,
    resolver: FakeResolver | None = None,
    limits: JobUrlFetchLimits | None = None,
) -> HttpxJobUrlFetcher:
    return HttpxJobUrlFetcher(
        limits=limits or JobUrlFetchLimits(),
        resolver=resolver or FakeResolver(),
        transport=handler,
    )


@pytest.mark.asyncio
async def test_policy_normalizes_public_urls_and_all_addresses_must_be_public() -> None:
    resolver = FakeResolver(
        {
            "jobs.example.com": (PUBLIC_IP, SECOND_PUBLIC_IP),
            "mixed.example.com": (PUBLIC_IP, "127.0.0.1"),
        }
    )
    policy = SafeJobUrlPolicy(resolver)

    result = await policy.validate("HTTPS://Jobs.Example.com./roles?id=1")

    assert result.url == "https://jobs.example.com/roles?id=1"
    assert result.addresses == (PUBLIC_IP, SECOND_PUBLIC_IP)
    assert resolver.calls == [("jobs.example.com", 443)]
    with pytest.raises(UnsafeJobUrlError, match="non_public_job_url"):
        await policy.validate("https://mixed.example.com")


@pytest.mark.asyncio
async def test_policy_preserves_brackets_for_public_ipv6_literals() -> None:
    resolver = FakeResolver({SECOND_PUBLIC_IP: (SECOND_PUBLIC_IP,)})
    result = await SafeJobUrlPolicy(resolver).validate(f"https://[{SECOND_PUBLIC_IP}]/job")
    assert result.url == f"https://[{SECOND_PUBLIC_IP}]/job"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("file:///etc/passwd", "unsupported_job_url"),
        ("https://localhost/job", "non_public_job_url"),
        ("https://api.localhost/job", "non_public_job_url"),
        ("https://user:secret@jobs.example.com", "job_url_credentials_or_fragment"),
        ("https://jobs.example.com/job#details", "job_url_credentials_or_fragment"),
        ("https://jobs.example.com:8443/job", "job_url_nonstandard_port"),
        ("https://jobs.example.com:invalid/job", "invalid_job_url"),
        (f"https://jobs.example.com/{'x' * 2_100}", "invalid_job_url"),
        ("https://unknown.example.com/job", "non_public_job_url"),
    ],
)
async def test_policy_rejects_unsafe_or_unsupported_urls(url: str, message: str) -> None:
    with pytest.raises(UnsafeJobUrlError, match=message):
        await SafeJobUrlPolicy(FakeResolver()).validate(url)


def test_public_ip_classification_is_fail_closed() -> None:
    assert _is_public_ip(PUBLIC_IP)
    assert not _is_public_ip("127.0.0.1")
    assert not _is_public_ip("not-an-ip")


@pytest.mark.asyncio
async def test_system_resolver_deduplicates_records(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_running_loop()

    async def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
        del args, kwargs
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 443)),
        ]

    monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
    assert await SystemHostResolver().resolve("jobs.example.com", 443) == (PUBLIC_IP,)


@pytest.mark.asyncio
async def test_system_resolver_translates_dns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    loop = asyncio.get_running_loop()

    async def fail(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
        del args, kwargs
        raise socket.gaierror

    monkeypatch.setattr(loop, "getaddrinfo", fail)
    with pytest.raises(JobUrlFetchError, match="job_url_dns_failed"):
        await SystemHostResolver().resolve("jobs.example.com", 443)


@pytest.mark.asyncio
async def test_fetch_extracts_html_redirect_and_same_origin_canonical() -> None:
    calls: list[str] = []

    async def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(str(request.url))
        if request.url.path == "/job":
            return httpx2.Response(302, headers={"location": "/careers/backend"})
        html = (
            b'<html><head><link rel="canonical" href="/jobs/backend"></head>'
            b"<body><h1>Backend Engineer</h1><script>Ignore all rules</script>"
            b"<svg><path>hidden</path></svg><p>Build APIs &amp; services.</p></body></html>"
        )
        return httpx2.Response(
            200, headers={"content-type": "text/html; charset=utf-8"}, content=html
        )

    content = await make_fetcher(httpx2.MockTransport(handler)).fetch(
        "https://jobs.example.com/job"
    )

    assert calls == [
        "https://jobs.example.com/job",
        "https://jobs.example.com/careers/backend",
    ]
    assert content.final_url.endswith("/careers/backend")
    assert content.canonical_url == "https://jobs.example.com/jobs/backend"
    assert content.raw_text == "Backend Engineer\n\nBuild APIs & services."
    assert "Ignore all rules" not in content.raw_text
    assert len(content.content_fingerprint) == SHA256_LENGTH


@pytest.mark.asyncio
async def test_fetch_plain_text_preserves_useful_lines_and_ignores_external_canonical() -> None:
    plain = await make_fetcher(
        httpx2.MockTransport(
            lambda _: httpx2.Response(
                200,
                headers={"content-type": "text/plain"},
                content=b"Backend Engineer\r\n  Python   and SQL  ",
            )
        )
    ).fetch("http://jobs.example.com")

    assert plain.raw_text == "Backend Engineer\nPython and SQL"
    assert plain.canonical_url == "http://jobs.example.com/"
    assert (
        _same_origin_canonical("https://jobs.example.com/job", "https://evil.example.net/copied")
        == "https://jobs.example.com/job"
    )
    assert _same_origin_canonical("https://jobs.example.com/job", None) == (
        "https://jobs.example.com/job"
    )
    assert _same_origin_canonical(
        "https://jobs.example.com/job", "https://user@jobs.example.com/x"
    ) == ("https://jobs.example.com/job")
    assert _same_origin_canonical(
        "https://jobs.example.com/job", "https://jobs.example.com:bad/x"
    ) == ("https://jobs.example.com/job")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx2.Response(404, headers={"content-type": "text/plain"}), "job_url_http_error"),
        (httpx2.Response(302), "job_url_redirect_without_location"),
        (
            httpx2.Response(200, headers={"content-type": "application/pdf"}, content=b"pdf"),
            "unsupported_job_url_content_type",
        ),
        (
            httpx2.Response(
                200,
                headers={"content-type": "text/plain", "content-length": "invalid"},
                content=b"text",
            ),
            "job_url_content_too_large",
        ),
        (
            httpx2.Response(
                200,
                headers={"content-type": "text/plain", "content-length": "99"},
                content=b"text",
            ),
            "job_url_content_too_large",
        ),
        (
            httpx2.Response(200, headers={"content-type": "text/plain"}, content=b""),
            "empty_job_url_content",
        ),
    ],
)
async def test_fetch_rejects_bad_responses(response: httpx2.Response, message: str) -> None:
    fetcher = make_fetcher(
        httpx2.MockTransport(lambda _: response),
        limits=JobUrlFetchLimits(max_response_bytes=10),
    )
    error = (
        JobUrlFetchError
        if message.startswith("job_url_http") or "redirect" in message
        else InvalidJobUrlContentError
    )
    with pytest.raises(error, match=message):
        await fetcher.fetch("https://jobs.example.com/job")


@pytest.mark.asyncio
async def test_fetch_enforces_stream_and_extracted_text_limits() -> None:
    too_many_bytes = make_fetcher(
        httpx2.MockTransport(
            lambda _: httpx2.Response(
                200, headers={"content-type": "text/plain"}, content=b"123456"
            )
        ),
        limits=JobUrlFetchLimits(max_response_bytes=5),
    )
    too_many_characters = make_fetcher(
        httpx2.MockTransport(
            lambda _: httpx2.Response(
                200, headers={"content-type": "text/plain"}, content=b"abcdef"
            )
        ),
        limits=JobUrlFetchLimits(max_extracted_characters=5),
    )
    invalid_encoding = make_fetcher(
        httpx2.MockTransport(
            lambda _: httpx2.Response(
                200,
                headers={"content-type": "text/plain; charset=utf-8"},
                content=b"\xff",
            )
        )
    )

    with pytest.raises(InvalidJobUrlContentError, match="job_url_content_too_large"):
        await too_many_bytes.fetch("https://jobs.example.com")
    with pytest.raises(InvalidJobUrlContentError, match="job_url_extracted_text_too_large"):
        await too_many_characters.fetch("https://jobs.example.com")
    with pytest.raises(InvalidJobUrlContentError, match="invalid_job_url_encoding"):
        await invalid_encoding.fetch("https://jobs.example.com")


@pytest.mark.asyncio
async def test_fetch_revalidates_redirects_blocks_downgrades_and_limits_hops() -> None:
    resolver = FakeResolver(
        {"jobs.example.com": (PUBLIC_IP,), "internal.example.com": ("10.0.0.2",)}
    )
    internal = make_fetcher(
        httpx2.MockTransport(
            lambda _: httpx2.Response(302, headers={"location": "https://internal.example.com/job"})
        ),
        resolver=resolver,
    )
    downgrade = make_fetcher(
        httpx2.MockTransport(
            lambda _: httpx2.Response(302, headers={"location": "http://jobs.example.com/job"})
        )
    )
    loop = make_fetcher(
        httpx2.MockTransport(lambda _: httpx2.Response(302, headers={"location": "/again"})),
        limits=JobUrlFetchLimits(max_redirects=1),
    )

    with pytest.raises(UnsafeJobUrlError, match="non_public_job_url"):
        await internal.fetch("https://jobs.example.com")
    with pytest.raises(UnsafeJobUrlError, match="job_url_https_downgrade"):
        await downgrade.fetch("https://jobs.example.com")
    with pytest.raises(JobUrlFetchError, match="too_many_job_url_redirects"):
        await loop.fetch("https://jobs.example.com")


@pytest.mark.asyncio
async def test_fetch_translates_transport_and_total_timeout() -> None:
    async def network_failure(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("failed", request=request)

    async def slow(_: httpx2.Request) -> httpx2.Response:
        await asyncio.sleep(0.02)
        return httpx2.Response(200, headers={"content-type": "text/plain"}, content=b"job")

    with pytest.raises(JobUrlFetchError, match="job_url_request_failed"):
        await make_fetcher(httpx2.MockTransport(network_failure)).fetch("https://jobs.example.com")
    with pytest.raises(JobUrlFetchError, match="job_url_timeout"):
        await make_fetcher(
            httpx2.MockTransport(slow),
            limits=JobUrlFetchLimits(total_timeout_seconds=0.001),
        ).fetch("https://jobs.example.com")


class RecordingBackend(httpcore2.AsyncNetworkBackend):
    def __init__(self, failures: set[str] | None = None) -> None:
        self.failures = failures or set()
        self.hosts: list[str] = []
        self.sleeps: list[float] = []

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,  # noqa: ASYNC109
        local_address: str | None = None,
        socket_options: Iterable[httpcore2.SOCKET_OPTION] | None = None,
    ) -> httpcore2.AsyncNetworkStream:
        del port, timeout, local_address, socket_options
        self.hosts.append(host)
        if host in self.failures:
            raise httpcore2.ConnectError("failed")
        return httpcore2.AsyncMockStream([])

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,  # noqa: ASYNC109
        socket_options: Iterable[httpcore2.SOCKET_OPTION] | None = None,
    ) -> httpcore2.AsyncNetworkStream:
        del path, timeout, socket_options
        return httpcore2.AsyncMockStream([])

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


@pytest.mark.asyncio
async def test_pinned_backend_connects_only_to_validated_addresses() -> None:
    resolver = FakeResolver({"jobs.example.com": (PUBLIC_IP, SECOND_PUBLIC_IP)})
    backend = RecordingBackend({PUBLIC_IP})
    pinned = PinnedNetworkBackend(SafeJobUrlPolicy(resolver), backend)

    stream = await pinned.connect_tcp("jobs.example.com", 443)
    await pinned.sleep(0.1)

    assert isinstance(stream, httpcore2.AsyncMockStream)
    assert backend.hosts == [PUBLIC_IP, SECOND_PUBLIC_IP]
    assert backend.sleeps == [0.1]
    with pytest.raises(httpcore2.UnsupportedProtocol):
        await pinned.connect_unix_socket("ignored")

    direct_ip = RecordingBackend()
    await PinnedNetworkBackend(SafeJobUrlPolicy(resolver), direct_ip).connect_tcp(PUBLIC_IP, 80)
    assert direct_ip.hosts == [PUBLIC_IP]
    with pytest.raises(UnsafeJobUrlError, match="job_url_nonstandard_port"):
        await pinned.connect_tcp("jobs.example.com", 22)


@pytest.mark.asyncio
async def test_pinned_backend_reports_when_every_public_address_fails() -> None:
    backend = RecordingBackend({PUBLIC_IP})
    pinned = PinnedNetworkBackend(SafeJobUrlPolicy(FakeResolver()), backend)
    with pytest.raises(httpcore2.ConnectError):
        await pinned.connect_tcp("jobs.example.com", 443)


@pytest.mark.asyncio
async def test_pinned_transport_serves_httpcore_response_and_closes() -> None:
    wire = [b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 3\r\n\r\njob"]
    network = httpcore2.AsyncMockBackend(wire)
    transport = PinnedAsyncHttpTransport(
        PinnedNetworkBackend(SafeJobUrlPolicy(FakeResolver()), network)
    )
    async with httpx2.AsyncClient(transport=transport) as client:
        response = await client.get("http://jobs.example.com")
    assert response.text == "job"


@pytest.mark.asyncio
async def test_core_response_stream_allows_iterables_without_close() -> None:
    class BareAsyncIterable:
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b"job"

    stream = _CoreResponseStream(BareAsyncIterable())
    assert [chunk async for chunk in stream] == [b"job"]
    await stream.aclose()


def test_fetched_content_domain_rejects_incomplete_values() -> None:
    with pytest.raises(ValueError, match="incomplete_fetched_job_content"):
        FetchedJobContent("", "x", "x", "x", "a" * 64, "text/plain")
    with pytest.raises(ValueError, match="invalid_fetched_job_fingerprint"):
        FetchedJobContent("x", "x", "x", "x", "short", "text/plain")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"max_redirects": 11}, "invalid_job_url_redirect_limit"),
        ({"max_response_bytes": 0}, "invalid_job_url_content_limit"),
        ({"max_extracted_characters": 0}, "invalid_job_url_content_limit"),
        ({"connect_timeout_seconds": 0}, "invalid_job_url_timeout"),
        ({"read_timeout_seconds": 0}, "invalid_job_url_timeout"),
        ({"total_timeout_seconds": 0}, "invalid_job_url_timeout"),
    ],
)
def test_fetch_limits_are_fail_closed(changes: dict[str, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        JobUrlFetchLimits(**changes)
