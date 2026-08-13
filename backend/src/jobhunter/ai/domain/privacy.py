"""Deterministic privacy authorization for model execution."""

from jobhunter.ai.domain.errors import PrivacyPolicyViolationError
from jobhunter.ai.domain.types import ExecutionLocation, ProviderInfo, StructuredGenerationRequest


class AIPrivacyPolicy:
    """Require explicit permission for cloud, retention, and training use."""

    def authorize(self, request: StructuredGenerationRequest, provider: ProviderInfo) -> None:
        consent = request.consent
        if provider.execution_location is ExecutionLocation.CLOUD and not consent.allow_cloud:
            raise PrivacyPolicyViolationError
        if provider.retains_inputs and not consent.allow_input_retention:
            raise PrivacyPolicyViolationError
        if provider.uses_inputs_for_training and not consent.allow_training:
            raise PrivacyPolicyViolationError
