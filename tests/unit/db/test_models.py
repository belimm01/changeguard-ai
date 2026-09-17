from typing import cast

from sqlalchemy import Table, UniqueConstraint

from changeguard.db.models import UNIQUE_JOB_IDENTITY, AnalysisJobRecord
from changeguard.domain.jobs import AnalysisJobIdentity


def test_table_name() -> None:
    assert AnalysisJobRecord.__tablename__ == "analysis_jobs"


def test_identity_columns_present() -> None:
    columns = set(AnalysisJobRecord.__table__.columns.keys())
    identity_fields = set(AnalysisJobIdentity.__dataclass_fields__)
    assert identity_fields <= columns


def test_unique_constraint_covers_identity() -> None:
    table = cast(Table, AnalysisJobRecord.__table__)
    constraints = {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert UNIQUE_JOB_IDENTITY in constraints
    covered = {column.name for column in constraints[UNIQUE_JOB_IDENTITY].columns}
    assert covered == set(AnalysisJobIdentity.__dataclass_fields__)


def test_lease_fields_are_nullable_placeholders() -> None:
    table = AnalysisJobRecord.__table__
    assert table.columns["lease_owner"].nullable
    assert table.columns["lease_expires_at"].nullable
    assert table.columns["completed_at"].nullable
