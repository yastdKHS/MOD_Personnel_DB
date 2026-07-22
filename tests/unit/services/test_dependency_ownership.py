"""`services/`パッケージの依存境界の検証（Phase7 Task16-4、レビュー項目8-9）。

docs/api/package-design.md のservices/節（Phase7 Task16-0で設計確定）は
「`services/`は`pipeline/`・`review/`・`export/`・`fetch/`・`ftp/`の
具象実装を自ら生成しない」（architecture-contract.md 保証15）と定める。
本テストは`src/mod_personnel_db/services/`配下の全モジュールをASTで走査し、
具象実装クラス（`HTTPFetchClient`・`StandardFTPClient`・`JobRunner`・
`RepositoryReviewService`・`RepositoryExportService`・`repositories.sqlite`
配下の各具象クラス等）を直接インスタンス化する式が存在しないこと、および
コンストラクタが依存をすべて注入で受け取っていることを確認する。
"""

import ast
from pathlib import Path

import mod_personnel_db.services as services_package
import mod_personnel_db.services.orchestrator as orchestrator_module

_FORBIDDEN_CONSTRUCTOR_CALLS = {
    "HTTPFetchClient",
    "StandardFTPClient",
    "JobRunner",
    "RepositoryReviewService",
    "RepositoryExportService",
    "SqlitePdfRepository",
    "SqliteCandidateRepository",
    "SqliteJobRepository",
    "SqliteGoldRepository",
    "SqliteLearningRepository",
    "SqliteKnowledgeRepository",
    "SqliteExportRepository",
    "SqliteReviewRepository",
    "FileKnowledgeService",
    "RepositoryLearningService",
}


def _called_names(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def test_services_package_does_not_construct_concrete_implementations() -> None:
    package_dir = Path(services_package.__file__).parent

    for source_path in sorted(package_dir.glob("*.py")):
        called = _called_names(source_path)
        violations = called & _FORBIDDEN_CONSTRUCTOR_CALLS
        assert not violations, f"{source_path.name} constructs concrete types: {violations}"


def test_default_job_orchestrator_constructor_only_assigns_injected_dependencies() -> None:
    """`__init__`が受け取った`dependencies`の属性代入のみを行い、新規オブジェクトを
    生成しない（Constructor Injectionのみで依存を解決する、レビュー項目9）ことを
    ASTで確認する。
    """
    source_path = Path(orchestrator_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    class_node = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "DefaultJobOrchestrator"
    )
    init_node = next(
        node
        for node in ast.walk(class_node)
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    calls_in_init = [n for n in ast.walk(init_node) if isinstance(n, ast.Call)]
    assert calls_in_init == []
