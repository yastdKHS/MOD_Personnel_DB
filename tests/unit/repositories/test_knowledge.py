import sqlite3
from datetime import date

from mod_personnel_db.models import KnowledgeItem, KnowledgeItemId, LayoutId
from mod_personnel_db.repositories.sqlite.knowledge import SqliteKnowledgeRepository


def _make_item(item_key: str = "陸将", canonical_value: str = "陸将") -> KnowledgeItem:
    return KnowledgeItem(
        id=KnowledgeItemId(0),
        category="rank",
        source_file="knowledge/ranks/gsdf.yaml",
        item_key=item_key,
        canonical_value=canonical_value,
        effective_from=date(2020, 1, 1),
        effective_to=None,
        provenance_source="陸上自衛隊階級呼称一覧",
        version=1,
    )


def test_upsert_and_get_item(conn: sqlite3.Connection) -> None:
    repo = SqliteKnowledgeRepository(conn)
    repo.upsert_item(_make_item())

    found = repo.get_item("rank", "陸将")
    missing = repo.get_item("rank", "存在しない階級")

    assert found is not None
    assert found.canonical_value == "陸将"
    assert missing is None


def test_upsert_unchanged_item_is_idempotent(conn: sqlite3.Connection) -> None:
    repo = SqliteKnowledgeRepository(conn)
    repo.upsert_item(_make_item())
    repo.upsert_item(_make_item())

    items = repo.list_items("rank")

    assert len(items) == 1


def test_upsert_changed_item_closes_old_and_adds_new(conn: sqlite3.Connection) -> None:
    repo = SqliteKnowledgeRepository(conn)
    repo.upsert_item(_make_item(canonical_value="陸将（旧）"))

    updated = KnowledgeItem(
        id=KnowledgeItemId(0),
        category="rank",
        source_file="knowledge/ranks/gsdf.yaml",
        item_key="陸将",
        canonical_value="陸将（新）",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        provenance_source="陸上自衛隊階級呼称一覧 改訂版",
        version=2,
    )
    repo.upsert_item(updated)

    items = repo.list_items("rank")
    current = repo.get_item("rank", "陸将")

    assert len(items) == 2
    assert current is not None
    assert current.canonical_value == "陸将（新）"
    old = next(i for i in items if i.canonical_value == "陸将（旧）")
    assert old.effective_to == date(2026, 1, 1)


def test_get_item_as_of_returns_historical_value(conn: sqlite3.Connection) -> None:
    repo = SqliteKnowledgeRepository(conn)
    repo.upsert_item(_make_item(canonical_value="陸将（旧）"))
    repo.upsert_item(
        KnowledgeItem(
            id=KnowledgeItemId(0),
            category="rank",
            source_file="knowledge/ranks/gsdf.yaml",
            item_key="陸将",
            canonical_value="陸将（新）",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            provenance_source="改訂版",
            version=2,
        )
    )

    historical = repo.get_item("rank", "陸将", as_of=date(2021, 1, 1))
    current = repo.get_item("rank", "陸将", as_of=date(2026, 6, 1))

    assert historical is not None
    assert historical.canonical_value == "陸将（旧）"
    assert current is not None
    assert current.canonical_value == "陸将（新）"


def test_get_layout_by_era_and_version(conn: sqlite3.Connection, layout_id: LayoutId) -> None:
    repo = SqliteKnowledgeRepository(conn)

    by_latest = repo.get_layout("reiwa")
    by_version = repo.get_layout("reiwa", version=1)
    missing = repo.get_layout("unknown-era")

    assert by_latest is not None
    assert by_latest.id == layout_id
    assert by_version is not None
    assert by_version.id == layout_id
    assert missing is None


def test_list_active_layouts(conn: sqlite3.Connection, layout_id: LayoutId) -> None:
    repo = SqliteKnowledgeRepository(conn)

    active = repo.list_active_layouts()
    as_of_active = repo.list_active_layouts(as_of=date(2026, 1, 1))
    as_of_before = repo.list_active_layouts(as_of=date(2000, 1, 1))

    assert [layout.id for layout in active] == [layout_id]
    assert [layout.id for layout in as_of_active] == [layout_id]
    assert as_of_before == ()
