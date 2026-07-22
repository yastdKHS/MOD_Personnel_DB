"""`fetch/`パッケージの依存境界の検証（Phase7 Task16-3、レビュー項目2-6）。

本Task16-3は`fetch/`のうちHTTP経由の取得機構（転送層）のみを実装する。
docs/api/package-design.md のfetch/節が定める`repositories/`（抽象、
`PDFRepository`）・`ftp/`への依存は、本Task16-3のScopeには含まれない
（将来タスクに委ねる）ため、本テストでは`utils/`以外の
`mod_personnel_db`配下パッケージへの依存が一切ないことを確認する。
"""

import ast
from pathlib import Path

import mod_personnel_db.fetch as fetch_package

_FORBIDDEN_TOP_LEVEL_PACKAGES = {
    "repositories",
    "pipeline",
    "review",
    "learning",
    "export",
    "ftp",
    "features",
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
    "services",
}

_ALLOWED_TOP_LEVEL_PACKAGES = {"utils", "fetch"}


def _imported_top_level_packages(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("mod_personnel_db.")
        ):
            imported.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("mod_personnel_db."):
                    imported.add(alias.name.split(".")[1])
    return imported


def test_fetch_package_does_not_import_forbidden_packages() -> None:
    package_dir = Path(fetch_package.__file__).parent

    for source_path in sorted(package_dir.glob("*.py")):
        imported = _imported_top_level_packages(source_path)
        violations = imported & _FORBIDDEN_TOP_LEVEL_PACKAGES
        assert not violations, f"{source_path.name} imports forbidden packages: {violations}"


def test_fetch_package_only_depends_on_utils_within_the_project() -> None:
    package_dir = Path(fetch_package.__file__).parent

    for source_path in sorted(package_dir.glob("*.py")):
        imported = _imported_top_level_packages(source_path)
        assert imported <= _ALLOWED_TOP_LEVEL_PACKAGES, (
            f"{source_path.name} imports unexpected packages: {imported}"
        )
