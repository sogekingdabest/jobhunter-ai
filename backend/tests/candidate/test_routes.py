"""Direct route tests keep async control flow observable to coverage."""

from collections.abc import Awaitable
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from jobhunter.candidate.api.routes import (
    create_candidate_profile,
    delete_candidate_profile,
    get_candidate_profile,
    replace_candidate_profile,
)
from jobhunter.candidate.api.schemas import CandidateProfileInput
from jobhunter.candidate.application.service import CandidateProfileService
from tests.candidate.test_schemas import sample_payload
from tests.candidate.test_service import InMemoryCandidateRepository


@pytest.mark.asyncio
async def test_routes_manage_profile_lifecycle() -> None:
    service = CandidateProfileService(InMemoryCandidateRepository())
    payload = CandidateProfileInput.model_validate(sample_payload())

    created = await create_candidate_profile(payload, service)
    fetched = await get_candidate_profile(created.id, service)
    replaced = await replace_candidate_profile(created.id, payload, service)
    response = await delete_candidate_profile(created.id, service)

    assert fetched.id == created.id
    assert replaced.id == created.id
    assert replaced.created_at == created.created_at
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["get", "replace", "delete"])
async def test_routes_return_not_found(operation: str) -> None:
    service = CandidateProfileService(InMemoryCandidateRepository())
    profile_id = uuid4()
    payload = CandidateProfileInput.model_validate(sample_payload())

    coroutine: Awaitable[object]
    if operation == "get":
        coroutine = get_candidate_profile(profile_id, service)
    elif operation == "replace":
        coroutine = replace_candidate_profile(profile_id, payload, service)
    else:
        coroutine = delete_candidate_profile(profile_id, service)

    with pytest.raises(HTTPException) as captured:
        await coroutine

    assert captured.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_routes_translate_domain_validation_errors() -> None:
    service = CandidateProfileService(InMemoryCandidateRepository())
    valid = CandidateProfileInput.model_validate(sample_payload())
    created = await create_candidate_profile(valid, service)
    invalid_data = sample_payload()
    invalid_data["preferred_roles"] = ["Backend", " backend "]
    invalid = CandidateProfileInput.model_validate(invalid_data)

    with pytest.raises(HTTPException) as create_error:
        await create_candidate_profile(invalid, service)
    with pytest.raises(HTTPException) as replace_error:
        await replace_candidate_profile(created.id, invalid, service)

    assert create_error.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert replace_error.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_routes_reject_client_owned_or_foreign_nested_ids() -> None:
    service = CandidateProfileService(InMemoryCandidateRepository())
    valid = CandidateProfileInput.model_validate(sample_payload())
    created = await create_candidate_profile(valid, service)
    with_id_data = sample_payload()
    with_id_data["projects"] = [{"id": str(uuid4()), "name": "Untrusted identity"}]
    with_id = CandidateProfileInput.model_validate(with_id_data)

    with pytest.raises(HTTPException) as create_error:
        await create_candidate_profile(with_id, service)
    with pytest.raises(HTTPException) as replace_error:
        await replace_candidate_profile(created.id, with_id, service)

    assert create_error.value.detail == "unexpected_entity_id"
    assert replace_error.value.detail == "unknown_entity_id"
