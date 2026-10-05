from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from changeguard.domain.content import Revision
from changeguard.domain.findings import RiskLevel


class SourceDto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: Annotated[str, Field(min_length=1, max_length=512)]
    side: Revision
    commit_sha: Annotated[str, Field(min_length=1, max_length=128)]
    blob_sha: Annotated[str, Field(min_length=1, max_length=128)]
    text: Annotated[str, Field(max_length=262_144)]


class RagFindingDto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rule_id: Annotated[str, Field(min_length=1, max_length=128)]
    level: RiskLevel
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    evidence_paths: Annotated[list[str], Field(max_length=32)]


class RagInputDto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    question: Annotated[str, Field(min_length=1, max_length=4000)]
    changed_paths: Annotated[list[str], Field(max_length=300)]
    findings: Annotated[list[RagFindingDto], Field(max_length=100)]
    sources: Annotated[list[SourceDto], Field(max_length=64)]
