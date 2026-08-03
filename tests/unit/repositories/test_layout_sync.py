"""`layout_sync.sync_layout_definitions()`の単体テスト。

Task26: layoutsテーブルへの自動登録機構（Task25-7で確認したBlocker #1の
恒久対応）が「自動登録される」「重複登録されない」「既存行のmanifest_checksum
は不変」という設計上の要件を満たすことを検証する。
"""

import hashlib
import sqlite3
from pathlib import Path

from mod_personnel_db.models import LayoutDefinition, LayoutRule, LayoutRuleKind
from mod_personnel_db.repositories.sqlite.layout_sync import sync_layout_definitions

_RULES = (LayoutRule(rule_id="header", kind=LayoutRuleKind.HEADER_PATTERN, value="X", weight=1.0),)


def _write_manifest(layouts_root: Path, era_id: str, content: bytes) -> Path:
    manifest_dir = layouts_root / era_id
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.yaml"
    manifest_path.write_bytes(content)
    return manifest_path


def test_sync_layout_definitions_inserts_new_layout(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    manifest_path = _write_manifest(tmp_path, "format_a", b"era_id: format_a\nversion: 1\n")
    definition = LayoutDefinition(era_id="format_a", version=1, rules=_RULES)

    sync_layout_definitions(conn, tmp_path, (definition,))

    row = conn.execute(
        "SELECT * FROM layouts WHERE era_id = ? AND version = ?", ("format_a", 1)
    ).fetchone()
    assert row is not None
    assert row["manifest_path"] == str(manifest_path)
    assert row["manifest_checksum"] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert row["status"] == "active"
    assert row["valid_from"] is not None


def test_sync_layout_definitions_is_idempotent(conn: sqlite3.Connection, tmp_path: Path) -> None:
    _write_manifest(tmp_path, "format_a", b"era_id: format_a\nversion: 1\n")
    definition = LayoutDefinition(era_id="format_a", version=1, rules=_RULES)

    sync_layout_definitions(conn, tmp_path, (definition,))
    sync_layout_definitions(conn, tmp_path, (definition,))

    count = conn.execute(
        "SELECT COUNT(*) c FROM layouts WHERE era_id = ? AND version = ?", ("format_a", 1)
    ).fetchone()["c"]
    assert count == 1


def test_sync_layout_definitions_does_not_update_existing_checksum(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """docs/database/schema.md「既存行のera_id/valid_from/manifest_checksumは不変」。
    manifest.yaml内容がDB登録後に変わっても、既存行のmanifest_checksumは更新しない。"""
    _write_manifest(tmp_path, "format_a", b"era_id: format_a\nversion: 1\n")
    conn.execute(
        """
        INSERT INTO layouts (era_id, version, manifest_path, manifest_checksum, valid_from, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("format_a", 1, "layouts/format_a/manifest.yaml", "stale_checksum", "2020-01-01", "active"),
    )
    conn.commit()
    definition = LayoutDefinition(era_id="format_a", version=1, rules=_RULES)

    sync_layout_definitions(conn, tmp_path, (definition,))

    row = conn.execute(
        "SELECT manifest_checksum FROM layouts WHERE era_id = ? AND version = ?", ("format_a", 1)
    ).fetchone()
    assert row["manifest_checksum"] == "stale_checksum"


def test_sync_layout_definitions_registers_multiple_layouts(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """複数のLayout（例: Layout-Aと2026 Layout）が両方登録される。"""
    _write_manifest(tmp_path, "2015_2017_format_a", b"era_id: 2015_2017_format_a\nversion: 1\n")
    _write_manifest(tmp_path, "2026_format_sample", b"era_id: 2026_format_sample\nversion: 1\n")
    definitions = (
        LayoutDefinition(era_id="2015_2017_format_a", version=1, rules=_RULES),
        LayoutDefinition(era_id="2026_format_sample", version=1, rules=_RULES),
    )

    sync_layout_definitions(conn, tmp_path, definitions)

    era_ids = {row["era_id"] for row in conn.execute("SELECT era_id FROM layouts").fetchall()}
    assert era_ids == {"2015_2017_format_a", "2026_format_sample"}


def test_sync_layout_definitions_empty_input_does_nothing(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    sync_layout_definitions(conn, tmp_path, ())

    count = conn.execute("SELECT COUNT(*) c FROM layouts").fetchone()["c"]
    assert count == 0
