"""`layouts/<era_id>/manifest.yaml`から`layouts`テーブルへの自動登録。

`layouts`テーブルは`layout/definitions.py::load_layout_definitions()`が読む
YAMLファイル（source of truth、ADR-0003）をDB上でクエリ可能にしたインデックス
であり（docs/database/schema.md#2-layouts）、`SqliteCandidateRepository.
_resolve_layout_id()`が`personnel_sections.layout_id`（FK）を解決する際に
参照する。これまでこのテーブルへ書き込むコードが存在せず、`layouts/`へ新規
Layout定義を追加しても本テーブルは空のままだったため（Task25-7調査）、Pipeline
実行時に`RepositoryError`が発生していた。本モジュールはその恒久対応であり、
Composition Root（`cli/bootstrap.py`）が`LayoutDefinition`をロードするたびに
呼び出すことで、YAMLファイルの内容を常に本テーブルへ反映する。

`CandidateRepository` Protocol（`repositories/__init__.py`）へは書き込み用の
メソッドを追加しない。既存Protocolの責務（`personnel_sections`/
`candidate_records`）とは異なる関心事であり、テストフィクスチャ
（`tests/unit/repositories/conftest.py::layout_id`）も同様に、Protocolを
介さず直接SQLを実行して`layouts`行を用意している（既知のギャップとして
コメントで明記済み）。
"""

import hashlib
import sqlite3
from pathlib import Path

from mod_personnel_db.models import LayoutDefinition

_MANIFEST_FILENAME = "manifest.yaml"


def sync_layout_definitions(
    conn: sqlite3.Connection,
    layouts_root: Path,
    layout_definitions: tuple[LayoutDefinition, ...],
) -> None:
    """`layout_definitions`（`layouts_root`から既にロード済み）の各`(era_id, version)`を
    `layouts`テーブルへ登録する。

    docs/database/schema.mdが定める更新方針（「既存行の`era_id`/`valid_from`/
    `manifest_checksum`は不変。新しい様式・manifest改訂ごとに新規行をINSERT」）
    に従い、`(era_id, version)`が既に登録済みの行は一切更新しない（`manifest_checksum`
    も含め不変）。未登録の`(era_id, version)`のみ新規`INSERT`する。これにより、
    同一マニフェストへの複数回の呼び出しでも重複登録は発生しない（冪等）。
    """
    for definition in layout_definitions:
        manifest_path = layouts_root / definition.era_id / _MANIFEST_FILENAME
        if _is_already_registered(conn, definition.era_id, definition.version):
            continue
        checksum = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        conn.execute(
            """
            INSERT INTO layouts
                (era_id, version, manifest_path, manifest_checksum, valid_from, status)
            VALUES (?, ?, ?, ?, STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now'), 'active')
            """,
            (definition.era_id, definition.version, str(manifest_path), checksum),
        )
    conn.commit()


def _is_already_registered(conn: sqlite3.Connection, era_id: str, version: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM layouts WHERE era_id = ? AND version = ?", (era_id, version)
    ).fetchone()
    return row is not None


__all__ = ["sync_layout_definitions"]
