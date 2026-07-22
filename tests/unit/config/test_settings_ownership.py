"""`AppSettings`（`CompositionSettings`）の生成箇所が`cli/bootstrap.py`に
限定されていることの検証（ADR-0028、Phase6 Task14-5、レビュー項目6）。

`cli/app.py`・`cli/commands.py`のソースをASTで走査し、`AppSettings(...)`/
`CompositionSettings(...)`という直接のコンストラクタ呼び出しが存在しない
ことを確認する（`build_settings(...)`経由の呼び出しのみを許可する）。
"""

import ast
import inspect
from types import ModuleType

from mod_personnel_db.cli import app as app_module
from mod_personnel_db.cli import bootstrap as bootstrap_module
from mod_personnel_db.cli import commands as commands_module


def _called_names(module: ModuleType) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def test_app_module_does_not_construct_settings_directly() -> None:
    called = _called_names(app_module)
    assert "AppSettings" not in called
    assert "CompositionSettings" not in called


def test_commands_module_does_not_construct_settings_directly() -> None:
    called = _called_names(commands_module)
    assert "AppSettings" not in called
    assert "CompositionSettings" not in called


def test_bootstrap_module_is_the_sole_settings_constructor_site() -> None:
    called = _called_names(bootstrap_module)
    assert "AppSettings" in called
