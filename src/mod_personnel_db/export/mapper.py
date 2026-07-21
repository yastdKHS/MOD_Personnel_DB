"""`GoldRecord`から公開用`PersonnelRecord`への変換（ADR-0016、Phase6 Task14-2）。

外部公開契約の境界をここに一本化する。`ExportService`の公開API
（`export_all_records()`等、`export/service.py`）は、`GoldRecord`を
直接返さず、必ず本モジュールの`to_personnel_record()`を経由して
`PersonnelRecord`へ変換してから返す。
"""

from collections.abc import Mapping

from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    GoldRecord,
    GoldRecordId,
    NormalizedValue,
    PersonnelRecord,
    Provenance,
)

_RANK_KEYS = ("rank",)
_ORGANIZATION_KEYS = ("organization", "org")
_POSITION_KEYS = ("position",)


def to_personnel_record(gold_record: GoldRecord) -> PersonnelRecord:
    """`GoldRecord`を公開用`PersonnelRecord`へ変換する。

    - `person`: `GoldRecord.person_key`から直接導出する（常に解決可能）。
    - `rank`/`organization`/`position`: `GoldRecord.fields.normalized_fields`
      のキーが意味的フィールド名（`rank`/`organization`/`position`）と
      一致する場合のみ解決する。現在のNormalizer実装は列位置ベースの
      汎用キー（`column_N`等）のまま値を保持し意味的フィールド名への
      リネームを行わない仕様（`models/normalization.py`の`NormalizedField`
      docstring参照）であるため、通常は`None`となる。意味的フィールド名を
      パイプライン側で永続化する変更は本Taskの対象外（Pipeline責務は
      変更しない）。
    - `provenance.source_pdf`/`parser_version`: `RepositoryExportService`が
      `GoldRepository`のみに依存する現在の設計では導出できないため`None`
      とする（`models/export.py`の`Provenance`docstring参照）。
      `layout_era_id`は`GoldRecord.fields.raw_record_ref.layout_id`から
      導出する。
    - `confidence`: 常に`score=1.0`・`band=VERIFIED`とする。`gold_records`
      への書き込み経路は`review/`の人手承認（`approve()`が呼ぶ
      `_promote_to_gold()`）に一本化されており（Architecture Contract
      保証8/9）、`GoldRecord`として存在すること自体が、ADR-0016の
      confidence算出ルール（`docs/database/json_schema.md#confidenceの算出ルール`）
      における`verified`の条件（人手レビューにより内容が確定している）を
      常に満たすため。
    """
    normalized_fields = gold_record.fields.normalized_fields
    return PersonnelRecord(
        id=_to_public_id(gold_record.id),
        person=NormalizedValue(value=gold_record.person_key, raw=None),
        rank=_lookup_first(normalized_fields, _RANK_KEYS),
        organization=_lookup_first(normalized_fields, _ORGANIZATION_KEYS),
        position=_lookup_first(normalized_fields, _POSITION_KEYS),
        appointment_type=gold_record.appointment_type,
        effective_date=gold_record.effective_date,
        version=gold_record.version,
        is_current=gold_record.is_current,
        superseded_by=_maybe_to_public_id(gold_record.superseded_by),
        provenance=Provenance(
            source_pdf=None,
            parser_version=None,
            layout_era_id=gold_record.fields.raw_record_ref.layout_id,
        ),
        confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
    )


def _to_public_id(gold_record_id: GoldRecordId) -> str:
    return f"gold-{int(gold_record_id):08d}"


def _maybe_to_public_id(gold_record_id: GoldRecordId | None) -> str | None:
    return None if gold_record_id is None else _to_public_id(gold_record_id)


def _lookup_first(
    normalized_fields: Mapping[str, NormalizedValue], keys: tuple[str, ...]
) -> NormalizedValue | None:
    for key in keys:
        if key in normalized_fields:
            return normalized_fields[key]
    return None


__all__ = ["to_personnel_record"]
