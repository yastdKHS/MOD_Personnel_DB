"""`MockFeatureStore`の単体テスト（Phase7 Task16-2）。"""

from datetime import UTC, datetime

from mod_personnel_db.features import MockFeatureStore, default_feature_vector
from mod_personnel_db.models import CandidateId, FeatureVector, RawRecord


def _raw_record(record_index: int = 0) -> RawRecord:
    return RawRecord(
        section_ref=None,
        layout_id="format_a",
        record_index=record_index,
        raw_fields={"rank": "1佐"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_default_feature_vector_has_default_subject_ref() -> None:
    vector = default_feature_vector()

    assert vector.subject_ref == CandidateId(0)
    assert vector.features


def test_default_feature_vector_accepts_explicit_subject_ref() -> None:
    vector = default_feature_vector(subject_ref=CandidateId(42))

    assert vector.subject_ref == CandidateId(42)


def test_mock_returns_default_when_no_responses_configured() -> None:
    store = MockFeatureStore()

    vector = store.compute(_raw_record())
    expected = default_feature_vector(subject_ref=vector.subject_ref)

    assert vector.subject_ref == CandidateId(0)
    assert vector.features == expected.features
    assert vector.feature_set_version == expected.feature_set_version


def test_mock_records_calls() -> None:
    store = MockFeatureStore()
    record = _raw_record()

    store.compute(record)

    assert store.calls == [record]


def test_mock_returns_preconfigured_responses_in_order() -> None:
    preset_a = default_feature_vector(subject_ref=CandidateId(1))
    preset_b = default_feature_vector(subject_ref=CandidateId(2))
    store = MockFeatureStore(responses=[preset_a, preset_b])

    first = store.compute(_raw_record(0))
    second = store.compute(_raw_record(1))

    assert first is preset_a
    assert second is preset_b


def test_mock_response_is_a_feature_vector() -> None:
    store = MockFeatureStore()

    vector = store.compute(_raw_record())

    assert isinstance(vector, FeatureVector)
