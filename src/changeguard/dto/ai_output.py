from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from changeguard.domain.content import Revision
from changeguard.domain.findings import RiskLevel

ShortText = Annotated[str, Field(min_length=1, max_length=2000)]


class CitationDto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_id: Annotated[str, Field(min_length=1, max_length=64)]
    path: Annotated[str, Field(min_length=1, max_length=512)]
    side: Revision
    commit_sha: Annotated[str, Field(min_length=1, max_length=128)]
    blob_sha: Annotated[str, Field(min_length=1, max_length=128)]
    start_line: Annotated[int, Field(ge=1, strict=True)]
    end_line: Annotated[int, Field(ge=1, strict=True)]
    quote: ShortText


class AdvisoryDto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    advisory_explanation: ShortText
    advisory_severity: RiskLevel
    recommended_tests: Annotated[list[ShortText], Field(max_length=8)]
    migration_considerations: Annotated[str, Field(max_length=2000)]
    rollback_considerations: Annotated[str, Field(max_length=2000)]
    citations: Annotated[list[CitationDto], Field(min_length=1, max_length=8)]


class AiOutputDto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    advisories: Annotated[list[AdvisoryDto], Field(max_length=8)]
