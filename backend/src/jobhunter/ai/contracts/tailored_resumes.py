"""Structured output contract for conservative resume rewrites."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from jobhunter.ai.domain.types import JSONObject


class ResumeRewrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    selection_id: UUID
    text: Annotated[str, Field(min_length=1, max_length=4_000)]


class TailoredResumeRewriteOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Annotated[str, Field(pattern=r"^1\.0$")]
    rewrites: Annotated[list[ResumeRewrite], Field(max_length=50)]


def tailored_resume_rewrite_schema() -> JSONObject:
    schema = TailoredResumeRewriteOutput.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:jobhunter-ai:ai:tailored-resume-rewrite:1.0"
    return schema
