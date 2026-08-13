"""Domain values produced by safe job-page acquisition."""

from dataclasses import dataclass

from jobhunter.jobs.domain.offers import SHA256_LENGTH


@dataclass(frozen=True, slots=True)
class FetchedJobContent:
    """Extracted text and auditable network identity for one job page."""

    requested_url: str
    final_url: str
    canonical_url: str
    raw_text: str
    content_fingerprint: str
    media_type: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.requested_url,
                self.final_url,
                self.canonical_url,
                self.raw_text,
                self.media_type,
            )
        ):
            raise ValueError("incomplete_fetched_job_content")
        if len(self.content_fingerprint) != SHA256_LENGTH:
            raise ValueError("invalid_fetched_job_fingerprint")
