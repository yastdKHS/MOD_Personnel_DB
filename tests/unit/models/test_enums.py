from mod_personnel_db.models import (
    ConfidenceBand,
    ErrorCategory,
    LearningStatus,
    PipelineStageName,
    RegressionStatus,
)


def test_confidence_band_values_match_json_schema_bands() -> None:
    assert {b.value for b in ConfidenceBand} == {"verified", "high", "medium", "low"}


def test_confidence_band_is_str_subclass() -> None:
    assert ConfidenceBand.HIGH.value == "high"
    assert isinstance(ConfidenceBand.HIGH, str)


def test_pipeline_stage_values_match_schema_check_constraint() -> None:
    assert {s.value for s in PipelineStageName} == {
        "layout_detector",
        "section_parser",
        "field_extractor",
        "normalizer",
        "validator",
    }


def test_error_category_values_match_schema_check_constraint() -> None:
    assert {c.value for c in ErrorCategory} == {
        "unknown_alias",
        "unknown_layout",
        "knowledge_gap",
        "layout_gap",
        "true_exception",
    }


def test_regression_status_values_match_schema_check_constraint() -> None:
    assert {r.value for r in RegressionStatus} == {"not_run", "passed", "failed"}


def test_learning_status_values_match_lifecycle() -> None:
    assert {s.value for s in LearningStatus} == {
        "open",
        "in_review",
        "reflected",
        "verified",
        "wontfix",
    }
