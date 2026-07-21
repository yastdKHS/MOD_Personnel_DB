"""`knowledge/`配下のフラットYAMLエントリを`KnowledgeItem`へ変換する。

`docs/knowledge/schema.md`が定めるカテゴリ別のリッチなJSON Schemaは、
Normalizer/Validatorが実際に消費する`item_key`/`canonical_value`という
平坦なモデル（ADR-0039〜ADR-0043）へまだ橋渡しされていない。本モジュールは
その橋渡しの最小実装として、カテゴリ別スキーマではなく共通の平坦な
エントリ形式（`item_key`/`canonical_value`/`provenance_source`等）のみを
読み込む。`docs/knowledge/schema.md`のカテゴリ別`constraint`展開等は対象外。

読み込みスタイルは`layout/definitions.py`（`LayoutDefinition`のYAMLロード）に
倣う: `yaml.safe_load()` → 構造変換、失敗はいずれも`KnowledgeLoadError`へ集約する。
"""

from datetime import date
from pathlib import Path
from typing import Any, get_args

import yaml

from mod_personnel_db.models import KnowledgeItem, KnowledgeItemId
from mod_personnel_db.models.knowledge import KnowledgeCategory
from mod_personnel_db.utils.exceptions import KnowledgeLoadError

# `docs/knowledge/schema.md`「カテゴリと物理ディレクトリの対応」に対応する。
CATEGORY_DIRECTORIES: dict[KnowledgeCategory, str] = {
    "organization": "organizations",
    "position": "positions",
    "rank": "ranks",
    "alias": "aliases",
    "historical": "historical",
    "typography": "typography",
    "layout": "layout_notes",
    "validation": "validation",
}

if set(CATEGORY_DIRECTORIES) != set(get_args(KnowledgeCategory)):
    raise AssertionError("CATEGORY_DIRECTORIES must cover every KnowledgeCategory value")


def load_knowledge_items(knowledge_root: Path) -> tuple[KnowledgeItem, ...]:
    """`knowledge_root`配下の全カテゴリディレクトリからKnowledgeItem群を読み込む。

    カテゴリディレクトリ自体が存在しない場合はそのカテゴリを0件として扱う
    （`README.md`のみが置かれた未整備カテゴリを許容するため）。
    """
    if not knowledge_root.is_dir():
        raise KnowledgeLoadError(f"knowledge root does not exist: {knowledge_root}")

    items: list[KnowledgeItem] = []
    next_id = 1
    for category, dirname in CATEGORY_DIRECTORIES.items():
        category_dir = knowledge_root / dirname
        if not category_dir.is_dir():
            continue
        for yaml_path in sorted(category_dir.rglob("*.yaml")):
            for entry in _load_entries(yaml_path):
                try:
                    item = _to_knowledge_item(next_id, category, knowledge_root, yaml_path, entry)
                except (KeyError, TypeError, ValueError) as exc:
                    raise KnowledgeLoadError(f"invalid knowledge item entry: {yaml_path}") from exc
                items.append(item)
                next_id += 1
    return tuple(items)


def _load_entries(yaml_path: Path) -> list[dict[str, Any]]:
    try:
        raw_text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise KnowledgeLoadError(f"failed to read knowledge YAML: {yaml_path}") from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise KnowledgeLoadError(f"failed to parse knowledge YAML: {yaml_path}") from exc

    try:
        return _to_entry_list(data)
    except TypeError as exc:
        raise KnowledgeLoadError(f"invalid knowledge YAML structure: {yaml_path}") from exc


def _to_entry_list(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise TypeError("knowledge YAML top-level must be a mapping")
    entries = data.get("items", [])
    if not isinstance(entries, list):
        raise TypeError("knowledge YAML 'items' must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise TypeError("each knowledge item entry must be a mapping")
    return entries


def _to_knowledge_item(
    item_id: int,
    category: KnowledgeCategory,
    knowledge_root: Path,
    yaml_path: Path,
    entry: dict[str, Any],
) -> KnowledgeItem:
    return KnowledgeItem(
        id=KnowledgeItemId(item_id),
        category=category,
        source_file=yaml_path.relative_to(knowledge_root).as_posix(),
        item_key=str(entry["item_key"]),
        canonical_value=str(entry["canonical_value"]),
        effective_from=_to_date(entry.get("effective_from")),
        effective_to=_to_date(entry.get("effective_to")),
        provenance_source=str(entry["provenance_source"]),
        version=int(entry.get("version", 1)),
    )


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
