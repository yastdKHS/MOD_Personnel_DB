from pathlib import Path

import pytest

from mod_personnel_db.layout import (
    LayoutDetectorError,
    load_layout_definition,
    load_layout_definitions,
)
from mod_personnel_db.models import LayoutRuleKind

_VALID_MANIFEST = """
era_id: "2019_format_a"
version: 1
rules:
  - rule_id: "header_a"
    kind: "header_pattern"
    value: "MOD PERSONNEL ORDER FORMAT A"
    weight: 0.6
  - rule_id: "min_pages"
    kind: "min_page_count"
    value: "1"
    weight: 0.1
"""


def test_load_layout_definition_parses_valid_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(_VALID_MANIFEST, encoding="utf-8")

    definition = load_layout_definition(manifest)

    assert definition.era_id == "2019_format_a"
    assert definition.version == 1
    assert len(definition.rules) == 2
    assert definition.rules[0].kind == LayoutRuleKind.HEADER_PATTERN


def test_load_layout_definition_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yaml"

    with pytest.raises(LayoutDetectorError):
        load_layout_definition(missing)


def test_load_layout_definition_invalid_yaml_raises(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("era_id: [unterminated", encoding="utf-8")

    with pytest.raises(LayoutDetectorError):
        load_layout_definition(manifest)


def test_load_layout_definition_missing_required_key_raises(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("era_id: '2019_format_a'\nversion: 1\n", encoding="utf-8")

    with pytest.raises(LayoutDetectorError):
        load_layout_definition(manifest)


def test_load_layout_definition_non_mapping_raises(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(LayoutDetectorError):
        load_layout_definition(manifest)


def test_load_layout_definitions_scans_era_subdirectories(tmp_path: Path) -> None:
    era_dir = tmp_path / "2019_format_a"
    era_dir.mkdir()
    (era_dir / "manifest.yaml").write_text(_VALID_MANIFEST, encoding="utf-8")

    definitions = load_layout_definitions(tmp_path)

    assert len(definitions) == 1
    assert definitions[0].era_id == "2019_format_a"


def test_load_layout_definitions_empty_root_returns_empty_tuple(tmp_path: Path) -> None:
    definitions = load_layout_definitions(tmp_path)

    assert definitions == ()
