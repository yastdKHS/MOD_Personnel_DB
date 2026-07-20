from datetime import date

import pytest

from mod_personnel_db.models import ValidationError, ValidationRuleSet
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.validators import RuleEngine, Validator

from .conftest import make_item, make_knowledge, make_record, make_rule_set

# --- Validation Rule評価（allowed_value_set） ---


def test_validator_passes_when_value_in_allowed_set(context: PipelineContext) -> None:
    knowledge = make_knowledge((make_item(1, "layout", "format_a.column_1", "rank"),))
    rules = make_rule_set((make_item(2, "validation", "rank", "陸将補"),))
    record = make_record({"column_1": "陸将補"})

    result = Validator(rules, knowledge).run(context, record)

    assert result.status == "passed"
    assert result.candidates[0].errors == ()


def test_validator_fails_when_value_not_in_allowed_set(context: PipelineContext) -> None:
    knowledge = make_knowledge((make_item(1, "layout", "format_a.column_1", "rank"),))
    rules = make_rule_set((make_item(2, "validation", "rank", "陸将補"),))
    record = make_record({"column_1": "不明階級"})

    result = Validator(rules, knowledge).run(context, record)

    assert result.status == "failed"
    error = result.candidates[0].errors[0]
    assert error.rule_id == "validation.rank.allowed_value_set"


def test_validator_multiple_allowed_values_for_same_field(context: PipelineContext) -> None:
    knowledge = make_knowledge((make_item(1, "layout", "format_a.column_1", "rank"),))
    rules = make_rule_set(
        (
            make_item(2, "validation", "rank", "陸将補"),
            make_item(3, "validation", "rank", "陸将"),
        )
    )
    record = make_record({"column_1": "陸将"})

    result = Validator(rules, knowledge).run(context, record)

    assert result.status == "passed"


def test_validator_field_without_rule_is_unconstrained(context: PipelineContext) -> None:
    knowledge = make_knowledge((make_item(1, "layout", "format_a.column_1", "name"),))
    rules = make_rule_set()
    record = make_record({"column_1": "山田太郎"})

    result = Validator(rules, knowledge).run(context, record)

    assert result.status == "passed"
    assert result.candidates[0].evidence.rules_evaluated == 1


# --- 意味的フィールド名未解決（Warning） ---


def test_validator_unmapped_field_produces_warning_not_error(context: PipelineContext) -> None:
    knowledge = make_knowledge()
    rules = make_rule_set()
    record = make_record({"column_1": "不明"})

    result = Validator(rules, knowledge).run(context, record)

    candidate = result.candidates[0]
    assert result.status == "passed"
    assert candidate.errors == ()
    assert len(candidate.warnings) == 1
    assert candidate.warnings[0].rule_id == "layout.unmapped_field"
    assert candidate.evidence.rules_evaluated == 0


# --- effective_from/effective_to による絞り込み（layoutマッピング解決） ---


def test_validator_ignores_layout_mapping_outside_effective_range(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge(
        (make_item(1, "layout", "format_a.column_1", "rank", effective=(date(2030, 1, 1), None)),),
        as_of=date(2026, 1, 1),
    )
    rules = make_rule_set()
    record = make_record({"column_1": "陸将補"})

    result = Validator(rules, knowledge).run(context, record)

    assert len(result.candidates[0].warnings) == 1


# --- 複数フィールド・Confidence ---


def test_validator_score_is_fraction_of_checkable_fields_without_error(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "rank"),
            make_item(2, "layout", "format_a.column_2", "name"),
        )
    )
    rules = make_rule_set((make_item(3, "validation", "rank", "陸将補"),))
    record = make_record({"column_1": "不明階級", "column_2": "山田太郎"})

    result = Validator(rules, knowledge).run(context, record)

    assert result.confidence.score == pytest.approx(0.5)
    assert result.status == "failed"


def test_validator_all_fields_unmapped_yields_medium_confidence(context: PipelineContext) -> None:
    knowledge = make_knowledge()
    rules = make_rule_set()
    record = make_record({"column_1": "不明"})

    result = Validator(rules, knowledge).run(context, record)

    assert result.confidence.score == pytest.approx(0.5)
    assert result.confidence.band.value == "medium"


def test_validator_confidence_band_high_for_mostly_passing_fields(context: PipelineContext) -> None:
    knowledge = make_knowledge(
        (
            make_item(1, "layout", "format_a.column_1", "rank"),
            make_item(2, "layout", "format_a.column_2", "name"),
            make_item(3, "layout", "format_a.column_3", "organization"),
            make_item(4, "layout", "format_a.column_4", "position"),
        )
    )
    rules = make_rule_set((make_item(5, "validation", "rank", "陸将補"),))
    record = make_record(
        {
            "column_1": "不明階級",
            "column_2": "山田太郎",
            "column_3": "第1師団",
            "column_4": "師団長",
        }
    )

    result = Validator(rules, knowledge).run(context, record)

    assert result.confidence.score == pytest.approx(0.75)
    assert result.confidence.band.value == "high"


def test_validator_all_checkable_fields_pass_yields_verified_confidence(
    context: PipelineContext,
) -> None:
    knowledge = make_knowledge((make_item(1, "layout", "format_a.column_1", "rank"),))
    rules = make_rule_set((make_item(2, "validation", "rank", "陸将補"),))
    record = make_record({"column_1": "陸将補"})

    result = Validator(rules, knowledge).run(context, record)

    assert result.confidence.score == 1.0
    assert result.confidence.band.value == "verified"


# --- ValidationResult/ValidationEvidence ---


def test_validator_evidence_reports_record_index_and_layout_id(context: PipelineContext) -> None:
    knowledge = make_knowledge()
    rules = make_rule_set()
    record = make_record({"column_1": "不明"}, layout_id="format_b", record_index=3)

    result = Validator(rules, knowledge).run(context, record)

    evidence = result.candidates[0].evidence
    assert evidence.record_index == 3
    assert evidence.layout_id == "format_b"


def test_validator_candidates_always_length_one(context: PipelineContext) -> None:
    knowledge = make_knowledge()
    rules = make_rule_set()
    record = make_record({"column_1": "x", "column_2": "y"})

    result = Validator(rules, knowledge).run(context, record)

    assert len(result.candidates) == 1


# --- NormalizedRecordは読み取り専用 ---


def test_validator_does_not_mutate_input_record(context: PipelineContext) -> None:
    knowledge = make_knowledge((make_item(1, "layout", "format_a.column_1", "rank"),))
    rules = make_rule_set((make_item(2, "validation", "rank", "陸将補"),))
    record = make_record({"column_1": "陸将補"})
    original_fields = dict(record.normalized_fields)

    Validator(rules, knowledge).run(context, record)

    assert dict(record.normalized_fields) == original_fields


# --- RuleEngineのコンストラクタ注入 ---


def test_validator_accepts_custom_rule_engine(context: PipelineContext) -> None:
    class _AlwaysPassEngine(RuleEngine):
        def evaluate_field(
            self, field_name: str, value: str, rules: ValidationRuleSet
        ) -> ValidationError | None:
            return None

    knowledge = make_knowledge((make_item(1, "layout", "format_a.column_1", "rank"),))
    rules = make_rule_set((make_item(2, "validation", "rank", "陸将補"),))
    record = make_record({"column_1": "不明階級"})

    result = Validator(rules, knowledge, engine=_AlwaysPassEngine()).run(context, record)

    assert result.status == "passed"
