from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import CandidateId, FeatureVector
from mod_personnel_db.models.values import ModelValidationError


def test_feature_vector_normal_construction() -> None:
    vector = FeatureVector(
        subject_ref=CandidateId(1),
        features={"ocr_confidence": 0.87, "layout_match_score": 0.95, "is_ocr": True},
        feature_set_version="v1",
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert vector.features["ocr_confidence"] == 0.87
    assert vector.features["is_ocr"] is True


def test_feature_vector_rejects_empty_features() -> None:
    with pytest.raises(ModelValidationError):
        FeatureVector(
            subject_ref=CandidateId(1),
            features={},
            feature_set_version="v1",
            computed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_feature_vector_rejects_empty_version() -> None:
    with pytest.raises(ModelValidationError):
        FeatureVector(
            subject_ref=CandidateId(1),
            features={"x": 1.0},
            feature_set_version="",
            computed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_feature_vector_boundary_single_feature() -> None:
    vector = FeatureVector(
        subject_ref=CandidateId(1),
        features={"only_feature": "value"},
        feature_set_version="v1",
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert len(vector.features) == 1


def test_feature_vector_accepts_mixed_value_types() -> None:
    vector = FeatureVector(
        subject_ref=CandidateId(1),
        features={"a": 1.0, "b": "text", "c": False},
        feature_set_version="v2",
        computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert vector.features["b"] == "text"
    assert vector.features["c"] is False
