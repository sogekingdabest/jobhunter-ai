"""Outbound port for retrieving untrusted public job pages."""

from typing import Protocol

from jobhunter.jobs.domain.acquisition import FetchedJobContent


class JobUrlFetcher(Protocol):
    """Retrieve and deterministically extract one public HTTP(S) resource."""

    async def fetch(self, url: str) -> FetchedJobContent: ...
