from datetime import date

from mod_personnel_db.knowledge import KnowledgeService
from mod_personnel_db.models import (
    KnowledgeItem,
    KnowledgeItemId,
    KnowledgeSnapshot,
    ValidationRuleSet,
)

from ._stubs import StubKnowledgeService

_AS_OF = date(2026, 1, 1)


def _make_item(category: str, item_key: str, canonical_value: str) -> KnowledgeItem:
    return KnowledgeItem(
        id=KnowledgeItemId(1),
        category=category,  # type: ignore[arg-type]
        source_file=f"knowledge/{category}/test.yaml",
        item_key=item_key,
        canonical_value=canonical_value,
        effective_from=None,
        effective_to=None,
        provenance_source="test",
        version=1,
    )


def test_stub_satisfies_knowledge_service_protocol() -> None:
    layout_item = _make_item("layout", "format_a.col_0", "rank")
    validation_item = _make_item("validation", "rank", "大将")
    snapshot = KnowledgeSnapshot(items=(layout_item,), snapshot_checksum="chk-1", as_of=_AS_OF)
    rules = ValidationRuleSet(rules=(validation_item,), as_of=_AS_OF)

    service: KnowledgeService = StubKnowledgeService(snapshot, rules)

    assert service.load_snapshot() is snapshot
    assert service.load_validation_rules() is rules
    assert service.get_item("layout", "format_a.col_0") is layout_item
    assert service.get_item("layout", "unknown") is None
    assert service.reload() is snapshot


def test_knowledge_service_public_api_is_documented_methods() -> None:
    public_names = {name for name in dir(KnowledgeService) if not name.startswith("_")}

    assert public_names == {"load_snapshot", "load_validation_rules", "get_item", "reload"}
