"""Pydantic response DTOs for serialized ChangeGuard findings."""

from pydantic import BaseModel, ConfigDict


class FindingDto(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    level: str
    summary: str
    evidence_paths: list[str]
