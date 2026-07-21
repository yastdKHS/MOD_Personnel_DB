from datetime import date
from pathlib import Path

import pytest

from mod_personnel_db.knowledge import FileKnowledgeService, KnowledgeService
from mod_personnel_db.utils.exceptions import KnowledgeLoadError

_LAYOUT_YAML = """
items:
  - item_key: "format_a.col_0"
    canonical_value: "rank"
    provenance_source: "layouts/reiwa/manifest.yaml"
    version: 1
"""

_VALIDATION_YAML = """
items:
  - item_key: "rank"
    canonical_value: "大将"
    provenance_source: "test"
    version: 1
  - item_key: "rank"
    canonical_value: "中将"
    provenance_source: "test"
    version: 1
"""


def _write(root: Path, category_dir: str, filename: str, text: str) -> None:
    directory = root / category_dir
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(text, encoding="utf-8")


def test_load_snapshot_reads_yaml_items(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "format_a.yaml", _LAYOUT_YAML)
    service = FileKnowledgeService(tmp_path)

    snapshot = service.load_snapshot(as_of=date(2026, 1, 1))

    assert len(snapshot.items) == 1
    item = snapshot.items[0]
    assert item.category == "layout"
    assert item.item_key == "format_a.col_0"
    assert item.canonical_value == "rank"
    assert item.source_file == "layout_notes/format_a.yaml"
    assert snapshot.snapshot_checksum != ""
    assert snapshot.as_of == date(2026, 1, 1)


def test_load_snapshot_defaults_as_of_to_today(tmp_path: Path) -> None:
    service = FileKnowledgeService(tmp_path)

    snapshot = service.load_snapshot()

    assert snapshot.as_of == date.today()


def test_load_validation_rules_filters_to_validation_category(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "format_a.yaml", _LAYOUT_YAML)
    _write(tmp_path, "validation", "rank.yaml", _VALIDATION_YAML)
    service = FileKnowledgeService(tmp_path)

    rules = service.load_validation_rules(as_of=date(2026, 1, 1))

    assert len(rules.rules) == 2
    assert {rule.canonical_value for rule in rules.rules} == {"大将", "中将"}
    assert all(rule.category == "validation" for rule in rules.rules)


def test_effective_from_and_effective_to_filter_by_as_of(tmp_path: Path) -> None:
    yaml_text = """
items:
  - item_key: "rank"
    canonical_value: "新階級名"
    provenance_source: "test"
    version: 1
    effective_from: "2026-06-01"
    effective_to: "2026-12-31"
"""
    _write(tmp_path, "validation", "rank.yaml", yaml_text)
    service = FileKnowledgeService(tmp_path)

    assert service.load_snapshot(as_of=date(2026, 1, 1)).items == ()
    assert len(service.load_snapshot(as_of=date(2026, 7, 1)).items) == 1
    assert service.load_snapshot(as_of=date(2026, 12, 31)).items == ()


def test_get_item_returns_matching_item(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "format_a.yaml", _LAYOUT_YAML)
    service = FileKnowledgeService(tmp_path)

    found = service.get_item("layout", "format_a.col_0")
    missing = service.get_item("layout", "unknown")

    assert found is not None
    assert found.canonical_value == "rank"
    assert missing is None


def test_cache_avoids_rereading_file_until_reload(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "format_a.yaml", _LAYOUT_YAML)
    service = FileKnowledgeService(tmp_path)
    first = service.load_snapshot(as_of=date(2026, 1, 1))

    (tmp_path / "layout_notes" / "format_a.yaml").unlink()

    cached = service.load_snapshot(as_of=date(2026, 1, 1))
    assert cached.items == first.items

    reloaded = service.reload()
    assert reloaded.items == ()


def test_missing_knowledge_root_raises_knowledge_load_error(tmp_path: Path) -> None:
    service = FileKnowledgeService(tmp_path / "does-not-exist")

    with pytest.raises(KnowledgeLoadError):
        service.load_snapshot()


def test_malformed_yaml_raises_knowledge_load_error(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "broken.yaml", "items: [unterminated")
    service = FileKnowledgeService(tmp_path)

    with pytest.raises(KnowledgeLoadError):
        service.load_snapshot()


def test_missing_required_field_raises_knowledge_load_error(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "layout_notes",
        "format_a.yaml",
        "items:\n  - canonical_value: 'rank'\n    provenance_source: 'test'\n",
    )
    service = FileKnowledgeService(tmp_path)

    with pytest.raises(KnowledgeLoadError):
        service.load_snapshot()


def test_non_mapping_yaml_raises_knowledge_load_error(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "format_a.yaml", "- just\n- a\n- list\n")
    service = FileKnowledgeService(tmp_path)

    with pytest.raises(KnowledgeLoadError):
        service.load_snapshot()


def test_items_not_a_list_raises_knowledge_load_error(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "format_a.yaml", "items: 'not-a-list'\n")
    service = FileKnowledgeService(tmp_path)

    with pytest.raises(KnowledgeLoadError):
        service.load_snapshot()


def test_entry_not_a_mapping_raises_knowledge_load_error(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "format_a.yaml", "items:\n  - 'not-a-mapping'\n")
    service = FileKnowledgeService(tmp_path)

    with pytest.raises(KnowledgeLoadError):
        service.load_snapshot()


def test_unreadable_yaml_path_raises_knowledge_load_error(tmp_path: Path) -> None:
    directory_as_yaml = tmp_path / "layout_notes" / "not-a-file.yaml"
    directory_as_yaml.mkdir(parents=True)
    service = FileKnowledgeService(tmp_path)

    with pytest.raises(KnowledgeLoadError):
        service.load_snapshot()


def test_unquoted_yaml_date_literal_is_accepted(tmp_path: Path) -> None:
    yaml_text = (
        "items:\n"
        "  - item_key: 'rank'\n"
        "    canonical_value: '新階級名'\n"
        "    provenance_source: 'test'\n"
        "    version: 1\n"
        "    effective_from: 2026-06-01\n"
        "    effective_to: 2026-12-31\n"
    )
    _write(tmp_path, "validation", "rank.yaml", yaml_text)
    service = FileKnowledgeService(tmp_path)

    snapshot = service.load_snapshot(as_of=date(2026, 7, 1))

    assert len(snapshot.items) == 1
    assert snapshot.items[0].effective_from == date(2026, 6, 1)
    assert snapshot.items[0].effective_to == date(2026, 12, 31)


def test_empty_knowledge_root_returns_empty_snapshot(tmp_path: Path) -> None:
    service = FileKnowledgeService(tmp_path)

    snapshot = service.load_snapshot()

    assert snapshot.items == ()
    assert snapshot.snapshot_checksum != ""


def test_file_knowledge_service_satisfies_knowledge_service_protocol(tmp_path: Path) -> None:
    _write(tmp_path, "layout_notes", "format_a.yaml", _LAYOUT_YAML)
    service: KnowledgeService = FileKnowledgeService(tmp_path)

    snapshot = service.load_snapshot()
    rules = service.load_validation_rules()
    item = service.get_item("layout", "format_a.col_0")
    reloaded = service.reload()

    assert snapshot.items[0].item_key == "format_a.col_0"
    assert rules.rules == ()
    assert item is not None
    assert reloaded.items == snapshot.items
