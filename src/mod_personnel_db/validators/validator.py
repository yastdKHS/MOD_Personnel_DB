"""Validator実装。docs/api/interfaces.md#validator, ADR-0043に対応する。

`NormalizedRecord`（段階5の出力）のみを入力とする（段階6）。`ValidationRuleSet`・
`KnowledgeSnapshot`・`RuleEngine`はコンストラクタで注入する（`run()`の単一入力化、
ADR-0041/ADR-0043）。Validation Rule評価・制約チェック・必須項目チェック・形式
チェック・Knowledge Validation Rule適用・Warning/Error生成・Confidence判定のみを
行う。値の修正・名寄せ・正規化・Repository/SQLite参照・Review・Learning・
Correction・JSON生成・FTP・Exportは行わない。`NormalizedRecord`は読み取り専用
として扱い、値を一切変更しない。
"""

from datetime import UTC, date, datetime
from typing import Literal

from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    KnowledgeItem,
    KnowledgeSnapshot,
    NormalizedRecord,
    ValidationCandidate,
    ValidationError,
    ValidationEvidence,
    ValidationResult,
    ValidationRuleSet,
    ValidationWarning,
)
from mod_personnel_db.models.values import ModelValidationError
from mod_personnel_db.pipeline import PipelineContext
from mod_personnel_db.validators.exceptions import ValidatorError
from mod_personnel_db.validators.rule_engine import RuleEngine

_UNMAPPED_FIELD_RULE_ID = "layout.unmapped_field"
_UNMAPPED_FIELD_SCORE = 0.5


class Validator:
    """`PipelineStage[NormalizedRecord, ValidationResult]`を実装する。公開APIは`run()`のみ。"""

    def __init__(
        self,
        rules: ValidationRuleSet,
        knowledge: KnowledgeSnapshot,
        engine: RuleEngine | None = None,
    ) -> None:
        self._rules = rules
        self._knowledge = knowledge
        self._engine = engine if engine is not None else RuleEngine()

    def run(self, context: PipelineContext, record: NormalizedRecord) -> ValidationResult:
        del context
        candidate = _evaluate_record(record, self._rules, self._knowledge, self._engine)
        status: Literal["passed", "failed"] = "failed" if candidate.errors else "passed"
        try:
            return ValidationResult(
                status=status,
                candidates=(candidate,),
                confidence=Confidence(
                    score=candidate.score, band=_confidence_band(candidate.score)
                ),
                validated_at=datetime.now(UTC),
            )
        except ModelValidationError as exc:
            raise ValidatorError(
                f"failed to construct ValidationResult for record_index={candidate.record_index}"
            ) from exc


def _evaluate_record(
    record: NormalizedRecord,
    rules: ValidationRuleSet,
    knowledge: KnowledgeSnapshot,
    engine: RuleEngine,
) -> ValidationCandidate:
    raw = record.raw_record_ref
    errors: list[ValidationError] = []
    warnings: list[ValidationWarning] = []
    checkable_count = 0
    for field_name, normalized_value in record.normalized_fields.items():
        semantic_name = _resolve_semantic_field_name(raw.layout_id, field_name, knowledge)
        if semantic_name is None:
            warnings.append(
                ValidationWarning(
                    rule_id=_UNMAPPED_FIELD_RULE_ID,
                    message=f"no semantic mapping for field {field_name!r}",
                )
            )
            continue
        checkable_count += 1
        error = engine.evaluate_field(semantic_name, normalized_value.value, rules)
        if error is not None:
            errors.append(error)
    evidence = ValidationEvidence(
        record_index=raw.record_index, layout_id=raw.layout_id, rules_evaluated=checkable_count
    )
    return ValidationCandidate(
        record_index=raw.record_index,
        score=_score(checkable_count, len(errors)),
        errors=tuple(errors),
        warnings=tuple(warnings),
        evidence=evidence,
    )


def _score(checkable_count: int, error_count: int) -> float:
    if checkable_count == 0:
        return _UNMAPPED_FIELD_SCORE
    return (checkable_count - error_count) / checkable_count


def _resolve_semantic_field_name(
    layout_id: str, raw_field_name: str, knowledge: KnowledgeSnapshot
) -> str | None:
    item_key = f"{layout_id}.{raw_field_name}"
    item = _lookup_layout_item(item_key, knowledge)
    return None if item is None else item.canonical_value


def _lookup_layout_item(item_key: str, knowledge: KnowledgeSnapshot) -> KnowledgeItem | None:
    for item in knowledge.items:
        if item.category != "layout" or item.item_key != item_key:
            continue
        if _within_effective_range(item, knowledge.as_of):
            return item
    return None


def _within_effective_range(item: KnowledgeItem, as_of: date) -> bool:
    if item.effective_from is not None and as_of < item.effective_from:
        return False
    return not (item.effective_to is not None and as_of > item.effective_to)


def _confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.9:
        return ConfidenceBand.VERIFIED
    if score >= 0.75:
        return ConfidenceBand.HIGH
    if score >= 0.5:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW
