"""`features/`パッケージの依存境界の検証（Phase7 Task16-2、レビュー項目2-5）。

docs/api/package-design.md のfeatures/節（Phase7 Task16-0で設計確定）は
「依存先: `models/`, `learning/`, `utils/`」「依存禁止: `document/`〜
`validators/`（中核パイプライン）, `repositories/`」と定める。本テストは
`src/mod_personnel_db/features/`配下の全モジュールをASTで走査し、
`pipeline/`・`repositories/`・`ftp/`・`cli/`（本タスクのレビュー項目が
明示する禁止対象）を含む禁止パッケージへのimportが存在しないことを
機械的に確認する。
"""

import ast
from pathlib import Path

import mod_personnel_db.features as features_package

_FORBIDDEN_TOP_LEVEL_PACKAGES = {
    "repositories",
    "pipeline",
    "review",
    "export",
    "ftp",
    "cli",
    "document",
    "layout",
    "sections",
    "extractors",
    "normalizers",
    "validators",
    "knowledge",
    "fetch",
    "services",
    "config",
}

_ALLOWED_TOP_LEVEL_PACKAGES = {"models", "learning", "utils", "features"}


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


def test_features_package_does_not_import_forbidden_packages() -> None:
    package_dir = Path(features_package.__file__).parent

    for source_path in sorted(package_dir.glob("*.py")):
        imported = _imported_top_level_packages(source_path)
        violations = imported & _FORBIDDEN_TOP_LEVEL_PACKAGES
        assert not violations, f"{source_path.name} imports forbidden packages: {violations}"


def test_features_package_only_depends_on_models_learning_and_utils() -> None:
    package_dir = Path(features_package.__file__).parent

    for source_path in sorted(package_dir.glob("*.py")):
        imported = _imported_top_level_packages(source_path)
        assert imported <= _ALLOWED_TOP_LEVEL_PACKAGES, (
            f"{source_path.name} imports unexpected packages: {imported}"
        )
