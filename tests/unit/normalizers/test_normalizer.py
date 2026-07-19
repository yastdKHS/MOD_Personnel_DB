from datetime import date

import pytest

from mod_personnel_db.normalizers import Normalizer
from mod_personnel_db.pipeline.context import PipelineContext

from .conftest import make_item, make_knowledge, make_record

# --- 意味的フィールド名対応 + Knowledge Lookup ---


def test_normalizer_resolves_semantic_field_and_applies_alias(context: PipelineContext) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "name"),
            make_item(2, "alias", "山田太郎", "山田太郎"),
        )
    )
    record = make_record({"column_1": "山田太郎"})

    result = Normalizer(knowledge).run(context, record)

    assert len(result.records) == 1
    field = result.candidates[0].fields[0]
    assert field.name == "column_1"
    assert field.raw == "山田太郎"
    assert field.value == "山田太郎"
    assert field.normalization_method == "alias"


def test_normalizer_applies_rank_lookup(context: PipelineContext) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "rank"),
            make_item(2, "rank", "陸将補", "陸将補"),
        )
    )
    record = make_record({"column_1": "陸将補"})

    result = Normalizer(knowledge).run(context, record)

    field = result.candidates[0].fields[0]
    assert field.value == "陸将補"
    assert field.normalization_method == "rank"


def test_normalizer_falls_back_to_typography_when_no_semantic_match(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge((make_item(1, "typography", "太朗", "太郎"),))
    record = make_record({"column_1": "山田太朗"})

    result = Normalizer(knowledge).run(context, record)

    field = result.candidates[0].fields[0]
    assert field.value == "山田太郎"
    assert field.normalization_method == "typography"


def test_normalizer_applies_nfkc_normalization(context: PipelineContext) -> None:
    knowledge = make_knowledge()
    record = make_record({"column_1": "ＡＢＣ"})

    result = Normalizer(knowledge).run(context, record)

    field = result.candidates[0].fields[0]
    assert field.value == "ABC"
    assert field.normalization_method == "identity"


def test_normalizer_falls_back_to_identity_without_any_knowledge_match(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge()
    record = make_record({"column_1": "不明部隊"})

    result = Normalizer(knowledge).run(context, record)

    field = result.candidates[0].fields[0]
    assert field.value == "不明部隊"
    assert field.normalization_method == "identity"


def test_normalizer_ignores_semantic_mapping_for_unknown_layout(context: PipelineContext) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "other_format.column_1", "name"),
            make_item(2, "alias", "山田太郎", "山田太郎"),
        )
    )
    record = make_record({"column_1": "山田太郎"}, layout_id="format_a")

    result = Normalizer(knowledge).run(context, record)

    field = result.candidates[0].fields[0]
    assert field.normalization_method == "identity"


# --- effective_from/effective_to による絞り込み ---


def test_normalizer_ignores_knowledge_item_outside_effective_range(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "rank"),
            make_item(
                2,
                "rank",
                "陸将補",
                "陸将補(旧)",
                effective=(date(2000, 1, 1), date(2020, 12, 31)),
            ),
        ),
        as_of=date(2026, 1, 1),
    )
    record = make_record({"column_1": "陸将補"})

    result = Normalizer(knowledge).run(context, record)

    field = result.candidates[0].fields[0]
    assert field.normalization_method == "identity"
    assert field.value == "陸将補"


def test_normalizer_ignores_knowledge_item_before_effective_from(context: PipelineContext) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "rank"),
            make_item(2, "rank", "陸将補", "陸将補(新)", effective=(date(2030, 1, 1), None)),
        ),
        as_of=date(2026, 1, 1),
    )
    record = make_record({"column_1": "陸将補"})

    result = Normalizer(knowledge).run(context, record)

    field = result.candidates[0].fields[0]
    assert field.normalization_method == "identity"
    assert field.value == "陸将補"


# --- 複数フィールド・Confidence ---


def test_normalizer_multiple_fields_score_is_averaged(context: PipelineContext) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "name"),
            make_item(2, "alias", "山田太郎", "山田太郎"),
        )
    )
    record = make_record({"column_1": "山田太郎", "column_2": "不明部隊"})

    result = Normalizer(knowledge).run(context, record)

    assert result.confidence.score == pytest.approx((1.0 + 0.3) / 2)
    assert result.confidence.band.value == "medium"


def test_normalizer_all_semantic_matches_yield_verified_confidence(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "name"),
            make_item(2, "alias", "山田太郎", "山田太郎"),
        )
    )
    record = make_record({"column_1": "山田太郎"})

    result = Normalizer(knowledge).run(context, record)

    assert result.confidence.score == 1.0
    assert result.confidence.band.value == "verified"


def test_normalizer_confidence_band_high_for_mixed_scores(context: PipelineContext) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "name"),
            make_item(2, "alias", "山田太郎", "山田太郎"),
            make_item(3, "typography", "太朗", "太郎"),
        )
    )
    record = make_record({"column_1": "山田太郎", "column_2": "鈴木太朗"})

    result = Normalizer(knowledge).run(context, record)

    assert result.confidence.score == pytest.approx(0.8)
    assert result.confidence.band.value == "high"


# --- 低Confidence ---


def test_normalizer_below_default_threshold_excluded(context: PipelineContext) -> None:
    knowledge = make_knowledge()
    record = make_record({"column_1": "不明部隊"})

    result = Normalizer(knowledge).run(context, record)

    assert result.records == ()
    assert len(result.candidates) == 1
    assert result.candidates[0].score == pytest.approx(0.3)


def test_normalizer_custom_confidence_threshold_is_respected(context: PipelineContext) -> None:
    knowledge = make_knowledge()
    record = make_record({"column_1": "不明部隊"})

    result = Normalizer(knowledge, confidence_threshold=0.2).run(context, record)

    assert len(result.records) == 1


# --- NormalizedRecord（既存形状）・NormalizationEvidence ---


def test_normalizer_builds_normalized_record_with_existing_shape(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "name"),
            make_item(2, "alias", "山田太郎", "山田太郎"),
        ),
        checksum="chk-abc123",
    )
    record = make_record({"column_1": "山田太郎"})

    result = Normalizer(knowledge).run(context, record)

    normalized = result.records[0]
    assert normalized.raw_record_ref is record
    assert set(normalized.normalized_fields) == {"column_1"}
    assert normalized.normalized_fields["column_1"].value == "山田太郎"
    assert normalized.normalized_fields["column_1"].raw == "山田太郎"
    assert normalized.normalization_applied == (2,)


def test_normalizer_evidence_reports_layout_id_and_knowledge_version(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge(checksum="chk-xyz")
    record = make_record({"column_1": "不明"}, layout_id="format_b")

    result = Normalizer(knowledge).run(context, record)

    evidence = result.candidates[0].evidence
    assert evidence.layout_id == "format_b"
    assert evidence.knowledge_version == "chk-xyz"
    assert evidence.matched_item_ids == ()
