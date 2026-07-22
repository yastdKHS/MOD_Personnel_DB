"""`FeatureStore`の標準実装。docs/api/package-design.md のfeatures/節
（Phase7 Task16-0で設計確定、Task16-2で実装）に対応する。

`RawRecord`/`NormalizedRecord`の内容のみから決定的に計算できる特徴量
（OCR抽出の充足率・疑わしい文字の混入率・正規化による変化率）に加え、
`LearningService`（`learning/`、Protocolとしてのみ依存、コンストラクタで
オプション注入）が利用可能な場合は、Learning Datasetの未解決エラー件数を
補助的な特徴量として追加する。V2.0時点では永続化しない（都度計算）。
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from mod_personnel_db.features.validation import validate_feature_ranges
from mod_personnel_db.learning import LearningService
from mod_personnel_db.models import CandidateId, FeatureVector, NormalizedRecord, RawRecord

FEATURE_SET_VERSION = "1.0.0"

_SUSPICIOUS_CHARACTERS = ("�", "\x00")


def _derive_subject_ref(raw: RawRecord) -> CandidateId:
    """`RawRecord`の内容から決定的な代理識別子を導出する。

    `compute()`呼び出し時点では`RawRecord`/`NormalizedRecord`はまだ
    `CandidateRepository`に永続化されておらず、実際のDB主キー（`CandidateId`）
    は存在しない。本関数は`layout_id`・`section_ref`・`record_index`から
    決定的（同一入力に対して常に同じ値）な代理識別子を導出する。実際の
    DB主キーとの対応付けは、呼び出し元（`JobRunner`、未実装）が
    `CandidateRepository`への永続化後に別途行う責務を持つ。
    """
    section_component = str(raw.section_ref) if raw.section_ref is not None else "-"
    digest_input = f"{raw.layout_id}:{section_component}:{raw.record_index}".encode()
    digest = hashlib.sha256(digest_input).digest()
    return CandidateId(int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF)


def _raw_field_fill_rate(raw: RawRecord) -> float:
    # RawRecord.__post_init__がraw_fieldsの非空を保証するため0除算は起こらない。
    filled = sum(1 for value in raw.raw_fields.values() if value.strip() != "")
    return filled / len(raw.raw_fields)


def _ocr_suspicious_char_rate(raw: RawRecord) -> float:
    suspicious = sum(
        1
        for value in raw.raw_fields.values()
        if any(marker in value for marker in _SUSPICIOUS_CHARACTERS)
    )
    return suspicious / len(raw.raw_fields)


def _normalization_change_rate(normalized: NormalizedRecord) -> float:
    # NormalizedRecord.__post_init__がnormalized_fieldsのキー一致（raw_fieldsと同一集合、
    # よって非空）を保証するため0除算は起こらない。
    fields = normalized.normalized_fields
    changed = sum(1 for value in fields.values() if value.value != value.raw)
    return changed / len(fields)


class DefaultFeatureStore:
    """`RawRecord`/`NormalizedRecord`から`FeatureVector`を都度計算する`FeatureStore`実装。"""

    def __init__(self, learning_service: LearningService | None = None) -> None:
        self._learning_service = learning_service

    def compute(self, subject: RawRecord | NormalizedRecord) -> FeatureVector:
        raw = subject if isinstance(subject, RawRecord) else subject.raw_record_ref

        features: dict[str, float | str | bool] = {
            "raw_field_fill_rate": _raw_field_fill_rate(raw),
            "ocr_suspicious_char_rate": _ocr_suspicious_char_rate(raw),
        }
        if isinstance(subject, NormalizedRecord):
            features["normalization_change_rate"] = _normalization_change_rate(subject)
        if self._learning_service is not None:
            features["learning_open_error_count"] = float(len(self._learning_service.list_open()))

        validate_feature_ranges(features)

        return FeatureVector(
            subject_ref=_derive_subject_ref(raw),
            features=features,
            feature_set_version=FEATURE_SET_VERSION,
            computed_at=datetime.now(UTC),
        )


__all__ = ["FEATURE_SET_VERSION", "DefaultFeatureStore"]
