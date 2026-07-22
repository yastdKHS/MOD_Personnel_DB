"""`DefaultFeatureStore`の単体テスト（Phase7 Task16-2）。"""

from datetime import UTC, datetime

from mod_personnel_db.features import FEATURE_SET_VERSION, DefaultFeatureStore
from mod_personnel_db.learning import LearningService
from mod_personnel_db.models import (
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    NormalizedRecord,
    NormalizedValue,
    RawRecord,
)


def _raw_record(
    raw_fields: dict[str, str], *, layout_id: str = "format_a", record_index: int = 0
) -> RawRecord:
    return RawRecord(
        section_ref=None,
        layout_id=layout_id,
        record_index=record_index,
        raw_fields=raw_fields,
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


class _StubLearningService:
    """`LearningService`Protocolを満たす最小限のテスト用スタブ。"""

    def __init__(self, open_count: int) -> None:
        self._open_count = open_count

    def record_error(self, entry: LearningRecord) -> LearningRecordId:
        raise NotImplementedError

    def transition(
        self, record_id: LearningRecordId, new_status: LearningStatus, **fields: object
    ) -> LearningRecord:
        raise NotImplementedError

    def list_open(self) -> tuple[LearningRecord, ...]:
        return tuple(range(self._open_count))  # type: ignore[arg-type]

    def summarize_by_error_category(self) -> dict[str, int]:
        raise NotImplementedError


def test_compute_returns_feature_vector_with_expected_version() -> None:
    store = DefaultFeatureStore()

    vector = store.compute(_raw_record({"name": "田中太郎", "rank": "1佐"}))

    assert vector.feature_set_version == FEATURE_SET_VERSION
    assert vector.features["raw_field_fill_rate"] == 1.0
    assert vector.features["ocr_suspicious_char_rate"] == 0.0


def test_compute_fill_rate_reflects_empty_fields() -> None:
    store = DefaultFeatureStore()

    vector = store.compute(_raw_record({"name": "田中太郎", "rank": "", "org": "  "}))

    assert vector.features["raw_field_fill_rate"] == 1 / 3


def test_compute_fill_rate_is_zero_when_all_fields_are_blank() -> None:
    store = DefaultFeatureStore()

    vector = store.compute(_raw_record({"name": "", "rank": "  "}))

    assert vector.features["raw_field_fill_rate"] == 0.0


def test_compute_detects_suspicious_characters() -> None:
    store = DefaultFeatureStore()

    vector = store.compute(_raw_record({"name": "田中太郎", "rank": "�1佐"}))

    assert vector.features["ocr_suspicious_char_rate"] == 0.5


def test_compute_with_normalized_record_adds_change_rate() -> None:
    store = DefaultFeatureStore()
    raw = _raw_record({"rank": "1佐", "org": "陸上自衛隊"})
    normalized = NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={
            "rank": NormalizedValue(value="一等陸佐", raw="1佐"),
            "org": NormalizedValue(value="陸上自衛隊", raw="陸上自衛隊"),
        },
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    vector = store.compute(normalized)

    assert vector.features["normalization_change_rate"] == 0.5


def test_compute_without_normalized_record_omits_change_rate() -> None:
    store = DefaultFeatureStore()

    vector = store.compute(_raw_record({"rank": "1佐"}))

    assert "normalization_change_rate" not in vector.features


def test_compute_without_learning_service_omits_open_error_count() -> None:
    store = DefaultFeatureStore()

    vector = store.compute(_raw_record({"rank": "1佐"}))

    assert "learning_open_error_count" not in vector.features


def test_compute_with_learning_service_adds_open_error_count() -> None:
    learning_service: LearningService = _StubLearningService(open_count=3)
    store = DefaultFeatureStore(learning_service=learning_service)

    vector = store.compute(_raw_record({"rank": "1佐"}))

    assert vector.features["learning_open_error_count"] == 3.0


def test_subject_ref_is_deterministic_for_identical_input() -> None:
    store = DefaultFeatureStore()
    record = _raw_record({"rank": "1佐"}, layout_id="format_a", record_index=5)

    first = store.compute(record)
    second = store.compute(record)

    assert first.subject_ref == second.subject_ref


def test_subject_ref_differs_for_different_record_index() -> None:
    store = DefaultFeatureStore()

    first = store.compute(_raw_record({"rank": "1佐"}, record_index=0))
    second = store.compute(_raw_record({"rank": "1佐"}, record_index=1))

    assert first.subject_ref != second.subject_ref
