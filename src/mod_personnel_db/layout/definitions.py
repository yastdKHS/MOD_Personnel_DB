"""`LayoutDefinition`のYAMLロード。docs/api/models.md#layoutdefinition, ADR-0035/0036に対応する。

`layouts/<era_id>/manifest.yaml`（[`layouts/README.md`](../../../layouts/README.md)）を
`LayoutDefinition`に変換する。Knowledge Base（`knowledge/`）とは異なる読み込み経路であり、
本モジュールは`layouts/`配下のみを対象とする。
"""

from pathlib import Path
from typing import Any

import yaml

from mod_personnel_db.layout.exceptions import LayoutDetectorError
from mod_personnel_db.models import LayoutDefinition, LayoutRule, LayoutRuleKind

_MANIFEST_FILENAME = "manifest.yaml"


def load_layout_definition(manifest_path: Path) -> LayoutDefinition:
    """1つの`manifest.yaml`を`LayoutDefinition`に変換する。"""
    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LayoutDetectorError(f"failed to read layout manifest: {manifest_path}") from exc

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise LayoutDetectorError(f"failed to parse layout manifest YAML: {manifest_path}") from exc

    try:
        return _to_layout_definition(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise LayoutDetectorError(f"invalid layout manifest structure: {manifest_path}") from exc


def load_layout_definitions(layouts_root: Path) -> tuple[LayoutDefinition, ...]:
    """`layouts_root`直下の各`<era_id>/manifest.yaml`を`LayoutDefinition`群に変換する。"""
    manifest_paths = sorted(layouts_root.glob(f"*/{_MANIFEST_FILENAME}"))
    return tuple(load_layout_definition(path) for path in manifest_paths)


def _to_layout_definition(data: Any) -> LayoutDefinition:
    if not isinstance(data, dict):
        raise TypeError("layout manifest must be a mapping")
    rules = tuple(_to_layout_rule(rule) for rule in data["rules"])
    return LayoutDefinition(era_id=str(data["era_id"]), version=int(data["version"]), rules=rules)


def _to_layout_rule(data: Any) -> LayoutRule:
    if not isinstance(data, dict):
        raise TypeError("layout rule must be a mapping")
    return LayoutRule(
        rule_id=str(data["rule_id"]),
        kind=LayoutRuleKind(data["kind"]),
        value=str(data["value"]),
        weight=float(data["weight"]),
    )
