"""`ftp/`パッケージの依存境界の検証（Phase7 Task16-1、レビュー項目2-4）。

docs/api/package-design.md のftp/節（Phase7 Task16-0で設計確定）は
「依存先: `utils/`のみ」「依存禁止: `repositories/`, `models/`のドメイン
モデル、`config/`」と定める。本テストは`src/mod_personnel_db/ftp/`配下の
全モジュールをASTで走査し、禁止された`mod_personnel_db`配下パッケージへの
importが存在しないことを機械的に確認する。
"""

import ast
from pathlib import Path

import mod_personnel_db.ftp as ftp_package

_FORBIDDEN_TOP_LEVEL_PACKAGES = {
    "repositories",
    "pipeline",
    "review",
    "learning",
    "export",
    "cli",
    "models",
    "config",
    "document",
    "layout",
    "sections",
    "extractors",
    "normalizers",
    "validators",
    "knowledge",
    "fetch",
    "services",
}


def _imported_top_level_packages(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("mod_personnel_db.")
        ):
            parts = node.module.split(".")
            imported.add(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("mod_personnel_db."):
                    parts = alias.name.split(".")
                    imported.add(parts[1])
    return imported


def test_ftp_package_does_not_import_forbidden_packages() -> None:
    package_dir = Path(ftp_package.__file__).parent

    for source_path in sorted(package_dir.glob("*.py")):
        imported = _imported_top_level_packages(source_path)
        violations = imported & _FORBIDDEN_TOP_LEVEL_PACKAGES
        assert not violations, f"{source_path.name} imports forbidden packages: {violations}"


def test_ftp_package_only_depends_on_utils_within_the_project() -> None:
    """パッケージ内サブモジュール間のimport（自己参照）は依存先の対象外とする。"""
    package_dir = Path(ftp_package.__file__).parent
    allowed = {"utils", "ftp"}

    for source_path in sorted(package_dir.glob("*.py")):
        imported = _imported_top_level_packages(source_path)
        assert imported <= allowed, f"{source_path.name} imports unexpected packages: {imported}"
