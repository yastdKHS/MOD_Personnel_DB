from datetime import UTC, date, datetime

import pytest

from mod_personnel_db.models import (
    JobId,
    KnowledgeItem,
    KnowledgeItemId,
    KnowledgeSnapshot,
    NormalizedRecord,
    NormalizedValue,
    ParserVersionId,
    RawRecord,
    ValidationRuleSet,
)
from mod_personnel_db.pipeline.context import PipelineContext

_STARTED_AT = datetime(2020, 1, 1, tzinfo=UTC)
DEFAULT_AS_OF = date(2026, 1, 1)


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(1),
        correlation_id="corr-validators-0001",
        started_at=_STARTED_AT,
    )


def make_item(
    item_id: int,
    category: str,
    item_key: str,
    canonical_value: str,
    *,
    effective: tuple[date | None, date | None] = (None, None),
) -> KnowledgeItem:
    effective_from, effective_to = effective
    return KnowledgeItem(
        id=KnowledgeItemId(item_id),
        category=category,  # type: ignore[arg-type]
        source_file=f"knowledge/{category}/test.yaml",
        item_key=item_key,
        canonical_value=canonical_value,
        effective_from=effective_from,
        effective_to=effective_to,
        provenance_source="test",
        version=1,
    )


def make_knowledge(
    items: tuple[KnowledgeItem, ...] = (), *, as_of: date = DEFAULT_AS_OF
) -> KnowledgeSnapshot:
    return KnowledgeSnapshot(items=items, snapshot_checksum="chk-1", as_of=as_of)


def make_rule_set(
    rules: tuple[KnowledgeItem, ...] = (), *, as_of: date = DEFAULT_AS_OF
) -> ValidationRuleSet:
    return ValidationRuleSet(rules=rules, as_of=as_of)


def make_record(
    normalized_fields: dict[str, str], *, layout_id: str = "format_a", record_index: int = 0
) -> NormalizedRecord:
    raw = RawRecord(
        section_ref=None,
        layout_id=layout_id,
        record_index=record_index,
        raw_fields=dict(normalized_fields),
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={
            k: NormalizedValue(value=v, raw=v) for k, v in normalized_fields.items()
        },
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
