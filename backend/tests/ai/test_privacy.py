"""Tests for explicit AI processing consent."""

import pytest

from jobhunter.ai.domain.errors import PrivacyPolicyViolationError
from jobhunter.ai.domain.privacy import AIPrivacyPolicy
from jobhunter.ai.domain.types import ExecutionLocation, ProcessingConsent, ProviderInfo
from tests.ai.factories import make_provider_info, make_request


def test_local_non_retaining_provider_needs_no_cloud_consent() -> None:
    AIPrivacyPolicy().authorize(make_request(), make_provider_info())


@pytest.mark.parametrize(
    ("provider", "consent"),
    [
        (make_provider_info(execution_location=ExecutionLocation.CLOUD), ProcessingConsent()),
        (make_provider_info(retains_inputs=True), ProcessingConsent()),
        (make_provider_info(uses_inputs_for_training=True), ProcessingConsent()),
    ],
)
def test_policy_rejects_missing_explicit_consent(
    provider: ProviderInfo, consent: ProcessingConsent
) -> None:
    with pytest.raises(PrivacyPolicyViolationError):
        AIPrivacyPolicy().authorize(make_request(consent=consent), provider)


def test_policy_accepts_each_explicit_permission() -> None:
    provider = make_provider_info(
        execution_location=ExecutionLocation.CLOUD,
        retains_inputs=True,
        uses_inputs_for_training=True,
    )
    consent = ProcessingConsent(
        allow_cloud=True,
        allow_input_retention=True,
        allow_training=True,
    )

    AIPrivacyPolicy().authorize(make_request(consent=consent), provider)
