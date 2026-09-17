"""Request DTOs for the analysis HTTP boundary."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisRequest(BaseModel):
    """A bounded request to analyze one pull request revision."""

    model_config = ConfigDict(frozen=True)

    owner: str = Field(min_length=1)
    repository: str = Field(min_length=1)
    pull_request: int = Field(gt=0)
    base_sha: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    analysis_version: str = "1"

    @field_validator("owner", "repository", "base_sha", "head_sha", "analysis_version")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
