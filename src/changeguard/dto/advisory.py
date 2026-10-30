"""Structured advisory answer the language model must return, and its parser."""

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    quote: str


class AdvisoryAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    citations: list[Citation]


class MalformedAdvisoryError(ValueError):
    """Model output is not valid JSON or does not match the advisory schema."""


def parse_advisory(raw: str) -> AdvisoryAnswer:
    try:
        return AdvisoryAnswer.model_validate_json(raw)
    except ValidationError as error:
        raise MalformedAdvisoryError("model output does not match schema") from error
