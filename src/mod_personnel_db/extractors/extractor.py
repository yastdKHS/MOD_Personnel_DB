"""Field Extractor実装。docs/api/interfaces.md#fieldextractor, ADR-0038に対応する。

`PersonnelSection`（段階3の出力）のみを入力とする（段階4）。文字列抽出・
列認識・正規表現によるRawRecord生成のみを行う。名寄せ・階級変換・肩書
正規化・部隊正規化・Validation・Review・Learning・Repository/SQLite参照・
JSON生成・FTPは行わない。フィールド名は列位置ベースの汎用名（`column_N`）
であり、意味的フィールド名への対応付けは行わない（ADR-0038）。
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from mod_personnel_db.extractors.exceptions import FieldExtractorError
from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    ExtractionCandidate,
    ExtractionEvidence,
    FieldExtractionResult,
    PersonnelSection,
    RawField,
    RawRecord,
)
from mod_personnel_db.models.values import ModelValidationError
from mod_personnel_db.pipeline import PipelineContext

DEFAULT_CONFIDENCE_THRESHOLD = 0.5
_COLUMN_SPLIT_PATTERN = re.compile(r"\s{2,}")


@dataclass(frozen=True, slots=True)
class _Columns:
    """1行から構造的に認識した列（Field Extractor外部には公開しない）。"""

    line: str
    values: tuple[str, ...]


class FieldExtractor:
    """`PipelineStage[PersonnelSection, FieldExtractionResult]`を実装する。公開APIは`run()`のみ。"""

    def __init__(self, *, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
        self._confidence_threshold = confidence_threshold

    def run(self, context: PipelineContext, section: PersonnelSection) -> FieldExtractionResult:
        del context
        lines = _lines(section.section_text)
        candidates = tuple(_evaluate_line(index, line) for index, line in enumerate(lines))
        records = _build_records(candidates, section.layout_id, self._confidence_threshold)
        return FieldExtractionResult(
            records=records, candidates=candidates, confidence=_overall_confidence(candidates)
        )


def _lines(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def _split_columns(line: str) -> _Columns:
    values = tuple(value for value in _COLUMN_SPLIT_PATTERN.split(line) if value.strip())
    return _Columns(line=line, values=values)


def _evaluate_line(record_index: int, line: str) -> ExtractionCandidate:
    columns = _split_columns(line)
    fields = tuple(
        RawField(name=f"column_{index + 1}", value=value)
        for index, value in enumerate(columns.values)
    )
    evidence = ExtractionEvidence(line=columns.line, column_count=len(columns.values))
    score = _score(len(columns.values))
    return ExtractionCandidate(
        record_index=record_index, score=score, evidence=evidence, fields=fields
    )


def _score(column_count: int) -> float:
    if column_count >= 2:
        return 1.0
    if column_count == 1:
        return 0.4
    return 0.0


def _build_records(
    candidates: tuple[ExtractionCandidate, ...], layout_id: str, threshold: float
) -> tuple[RawRecord, ...]:
    records: list[RawRecord] = []
    for candidate in candidates:
        if candidate.score < threshold:
            continue
        if not candidate.fields:
            continue
        records.append(_to_raw_record(candidate, layout_id))
    return tuple(records)


def _to_raw_record(candidate: ExtractionCandidate, layout_id: str) -> RawRecord:
    raw_fields = {field.name: field.value for field in candidate.fields}
    try:
        return RawRecord(
            section_ref=None,
            layout_id=layout_id,
            record_index=candidate.record_index,
            raw_fields=raw_fields,
            extracted_at=datetime.now(UTC),
        )
    except ModelValidationError as exc:
        raise FieldExtractorError(
            f"failed to construct RawRecord for record_index={candidate.record_index}"
        ) from exc


def _overall_confidence(candidates: tuple[ExtractionCandidate, ...]) -> Confidence:
    if not candidates:
        return Confidence(score=0.0, band=ConfidenceBand.LOW)
    average = sum(candidate.score for candidate in candidates) / len(candidates)
    return Confidence(score=average, band=_confidence_band(average))


def _confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.9:
        return ConfidenceBand.VERIFIED
    if score >= 0.75:
        return ConfidenceBand.HIGH
    if score >= 0.5:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW
