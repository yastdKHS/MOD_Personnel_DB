"""`ExportArtifact`のValidation Rule検証（ADR-0029、Phase6 Task14-4）。"""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from mod_personnel_db.models import ExportArtifact
from mod_personnel_db.models.values import ModelValidationError


def _base_kwargs() -> dict[str, object]:
    return {
        "export_id": "d3f6b2a0-0000-4000-8000-000000000000",
        "exported_at": datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC),
        "format": "csv",
        "record_count": 1,
        "sha256": "a" * 64,
    }


def test_export_artifact_rejects_empty_export_id() -> None:
    kwargs = _base_kwargs() | {"export_id": ""}
    with pytest.raises(ModelValidationError, match="export_id must not be empty"):
        ExportArtifact(**kwargs)  # type: ignore[arg-type]


def test_export_artifact_rejects_naive_exported_at() -> None:
    kwargs = _base_kwargs() | {"exported_at": datetime(2026, 7, 22, 12, 0, 0)}
    with pytest.raises(ModelValidationError, match="exported_at must be UTC"):
        ExportArtifact(**kwargs)  # type: ignore[arg-type]


def test_export_artifact_rejects_non_utc_offset() -> None:
    jst = timezone(timedelta(hours=9))
    kwargs = _base_kwargs() | {
        "exported_at": datetime(2026, 7, 22, 21, 0, 0, tzinfo=jst),
    }
    with pytest.raises(ModelValidationError, match="exported_at must be UTC"):
        ExportArtifact(**kwargs)  # type: ignore[arg-type]


def test_export_artifact_rejects_negative_record_count() -> None:
    kwargs = _base_kwargs() | {"record_count": -1}
    with pytest.raises(ModelValidationError, match="record_count must be >= 0"):
        ExportArtifact(**kwargs)  # type: ignore[arg-type]


def test_export_artifact_rejects_empty_sha256() -> None:
    kwargs = _base_kwargs() | {"sha256": ""}
    with pytest.raises(ModelValidationError, match="sha256 must not be empty"):
        ExportArtifact(**kwargs)  # type: ignore[arg-type]


def test_export_artifact_accepts_valid_utc_kwargs() -> None:
    artifact = ExportArtifact(**_base_kwargs())  # type: ignore[arg-type]

    assert artifact.export_id == "d3f6b2a0-0000-4000-8000-000000000000"
    assert artifact.format == "csv"
    assert artifact.record_count == 1
    assert artifact.sha256 == "a" * 64
