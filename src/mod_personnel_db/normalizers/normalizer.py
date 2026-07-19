"""Normalizer実装。docs/api/interfaces.md#normalizer, ADR-0040に対応する。

`RawRecord`（段階4の出力）のみを入力とする（段階5）。`KnowledgeSnapshot`は
コンストラクタで注入する（`run()`の単一入力化、ADR-0040）。意味的フィールド名
対応・Unicode正規化・表記ゆれ補正・別名解決・肩書/階級/部隊正規化・Knowledge
Lookupのみを行う。Validation・Review・Correction・Learning・Repository/SQLite
参照・JSON生成・FTP・Exportは行わない。
"""

import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime

from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    KnowledgeItem,
    KnowledgeItemId,
    KnowledgeSnapshot,
    NormalizationCandidate,
    NormalizationEvidence,
    NormalizationResult,
    NormalizedField,
    NormalizedRecord,
    NormalizedValue,
    RawRecord,
)
from mod_personnel_db.models.values import ModelValidationError
from mod_personnel_db.normalizers.exceptions import NormalizerError
from mod_personnel_db.pipeline import PipelineContext

DEFAULT_CONFIDENCE_THRESHOLD = 0.5

_FIELD_TO_CATEGORY = {
    "name": "alias",
    "rank": "rank",
    "organization": "organization",
    "position": "position",
}
_METHOD_SCORE = {"identity": 0.3, "typography": 0.6}
_SEMANTIC_MATCH_SCORE = 1.0


@dataclass(frozen=True, slots=True)
class _FieldResult:
    field: NormalizedField
    matched_item_ids: tuple[KnowledgeItemId, ...]
    score: float


class Normalizer:
    """`PipelineStage[RawRecord, NormalizationResult]`を実装する。公開APIは`run()`のみ。"""

    def __init__(
        self,
        knowledge: KnowledgeSnapshot,
        *,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._knowledge = knowledge
        self._confidence_threshold = confidence_threshold

    def run(self, context: PipelineContext, record: RawRecord) -> NormalizationResult:
        del context
        candidate = _evaluate_record(record, self._knowledge)
        records = _build_records(record, candidate, self._confidence_threshold)
        return NormalizationResult(
            records=records, candidates=(candidate,), confidence=_overall_confidence(candidate)
        )


def _evaluate_record(record: RawRecord, knowledge: KnowledgeSnapshot) -> NormalizationCandidate:
    results = [
        _normalize_field(record.layout_id, name, raw_value, knowledge)
        for name, raw_value in record.raw_fields.items()
    ]
    fields = tuple(result.field for result in results)
    matched_ids = tuple(item_id for result in results for item_id in result.matched_item_ids)
    score = sum(result.score for result in results) / len(results) if results else 0.0
    evidence = NormalizationEvidence(
        layout_id=record.layout_id,
        knowledge_version=knowledge.snapshot_checksum,
        matched_item_ids=matched_ids,
    )
    return NormalizationCandidate(
        record_index=record.record_index, score=score, fields=fields, evidence=evidence
    )


def _normalize_field(
    layout_id: str, name: str, raw_value: str, knowledge: KnowledgeSnapshot
) -> _FieldResult:
    typography_value, typo_ids = _apply_typography(raw_value, knowledge)
    semantic_name = _resolve_semantic_field_name(layout_id, name, knowledge)
    category = _FIELD_TO_CATEGORY.get(semantic_name or "")
    if category is not None:
        item = _lookup_knowledge_item(category, typography_value, knowledge)
        if item is not None:
            field = NormalizedField(
                name=name, raw=raw_value, value=item.canonical_value, normalization_method=category
            )
            return _FieldResult(
                field=field, matched_item_ids=(*typo_ids, item.id), score=_SEMANTIC_MATCH_SCORE
            )
    method = "typography" if typo_ids else "identity"
    field = NormalizedField(
        name=name, raw=raw_value, value=typography_value, normalization_method=method
    )
    return _FieldResult(field=field, matched_item_ids=typo_ids, score=_METHOD_SCORE[method])


def _resolve_semantic_field_name(
    layout_id: str, raw_field_name: str, knowledge: KnowledgeSnapshot
) -> str | None:
    item_key = f"{layout_id}.{raw_field_name}"
    item = _lookup_knowledge_item("layout", item_key, knowledge, key_field="item_key")
    return None if item is None else item.canonical_value


def _apply_typography(
    value: str, knowledge: KnowledgeSnapshot
) -> tuple[str, tuple[KnowledgeItemId, ...]]:
    normalized = unicodedata.normalize("NFKC", value)
    applied: list[KnowledgeItemId] = []
    for item in knowledge.items:
        if item.category != "typography" or item.item_key not in normalized:
            continue
        normalized = normalized.replace(item.item_key, item.canonical_value)
        applied.append(item.id)
    return normalized, tuple(applied)


def _lookup_knowledge_item(
    category: str, key: str, knowledge: KnowledgeSnapshot, *, key_field: str = "item_key"
) -> KnowledgeItem | None:
    for item in knowledge.items:
        if item.category != category or getattr(item, key_field) != key:
            continue
        if _within_effective_range(item, knowledge.as_of):
            return item
    return None


def _within_effective_range(item: KnowledgeItem, as_of: date) -> bool:
    if item.effective_from is not None and as_of < item.effective_from:
        return False
    return not (item.effective_to is not None and as_of > item.effective_to)


def _build_records(
    record: RawRecord, candidate: NormalizationCandidate, threshold: float
) -> tuple[NormalizedRecord, ...]:
    if candidate.score < threshold or not candidate.fields:
        return ()
    return (_to_normalized_record(record, candidate),)


def _to_normalized_record(record: RawRecord, candidate: NormalizationCandidate) -> NormalizedRecord:
    normalized_fields = {
        field.name: NormalizedValue(value=field.value, raw=field.raw) for field in candidate.fields
    }
    try:
        return NormalizedRecord(
            raw_record_ref=record,
            normalized_fields=normalized_fields,
            normalization_applied=candidate.evidence.matched_item_ids,
            normalized_at=datetime.now(UTC),
        )
    except ModelValidationError as exc:
        raise NormalizerError(
            f"failed to construct NormalizedRecord for record_index={record.record_index}"
        ) from exc


def _overall_confidence(candidate: NormalizationCandidate) -> Confidence:
    return Confidence(score=candidate.score, band=_confidence_band(candidate.score))


def _confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.9:
        return ConfidenceBand.VERIFIED
    if score >= 0.75:
        return ConfidenceBand.HIGH
    if score >= 0.5:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW
