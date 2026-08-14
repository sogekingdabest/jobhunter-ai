"""Small, dependency-free HTTP observability boundary."""

import logging
import re
from time import perf_counter
from typing import Final
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("jobhunter.http")

_REQUEST_ID: Final = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestObservabilityMiddleware:
    """Correlate requests and expose coarse server timing without logging payloads."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        supplied_id = next(
            (
                value.decode("ascii", errors="ignore")
                for name, value in scope.get("headers", ())
                if name.lower() == b"x-request-id"
            ),
            "",
        )
        request_id = supplied_id if _REQUEST_ID.fullmatch(supplied_id) else str(uuid4())
        started = perf_counter()
        status_code = 500

        async def send_with_observability(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration_ms = (perf_counter() - started) * 1_000
                headers = list(message.get("headers", ()))
                headers.extend(
                    (
                        (b"x-request-id", request_id.encode("ascii")),
                        (b"server-timing", f"app;dur={duration_ms:.2f}".encode("ascii")),
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self._app(scope, receive, send_with_observability)
        finally:
            duration_ms = (perf_counter() - started) * 1_000
            logger.info(
                "request_completed request_id=%s method=%s path=%s status_code=%d duration_ms=%.2f",
                request_id,
                scope.get("method", "UNKNOWN"),
                scope.get("path", ""),
                status_code,
                duration_ms,
            )
