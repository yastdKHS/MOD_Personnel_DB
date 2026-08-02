"""Task25-3で追加した`layouts/2015_2017_format_a/manifest.yaml`の構造検証。

実データPDFに対する実際のLayoutDetector判定挙動の確認は、Task25-3の
検証手順（`runtime/staged_pdfs/`配下の実データ・診断スクリプト）で
別途行っており、ここでは`load_layout_definitions()`がマニフェストを
仕様どおりに読み込めることのみを検証する（既存の`_pdf_fixtures.py`は
ASCII文字のみを想定した合成PDF生成ヘルパーであり、本Layoutが用いる
日本語文字列ルールを実際のPDFテキスト抽出で再現するには対応していない
ため、実データでの検証で代替する）。
"""

from pathlib import Path

from mod_personnel_db.layout.definitions import load_layout_definitions
from mod_personnel_db.models import LayoutRuleKind

_LAYOUTS_ROOT = Path(__file__).resolve().parents[3] / "layouts"


def test_layout_2015_2017_format_a_manifest_loads_with_expected_rules() -> None:
    definitions = load_layout_definitions(_LAYOUTS_ROOT)
    matches = [d for d in definitions if d.era_id == "2015_2017_format_a"]

    assert len(matches) == 1
    definition = matches[0]
    assert definition.version == 1
    assert len(definition.rules) == 8
    assert sum(rule.weight for rule in definition.rules) == 1.0

    header_rules = [r for r in definition.rules if r.kind == LayoutRuleKind.HEADER_PATTERN]
    footer_rules = [r for r in definition.rules if r.kind == LayoutRuleKind.FOOTER_PATTERN]
    min_page_rules = [r for r in definition.rules if r.kind == LayoutRuleKind.MIN_PAGE_COUNT]
    font_rules = [r for r in definition.rules if r.kind == LayoutRuleKind.FONT_NAME_CONTAINS]

    assert {r.value for r in header_rules} == {"防", "衛", "省", "発", "令"}
    assert {r.value for r in footer_rules} == {"以上"}
    assert {r.value for r in min_page_rules} == {"1"}
    assert {r.value for r in font_rules} == {"Century"}


def test_layout_2015_2017_format_a_does_not_remove_existing_layout() -> None:
    definitions = load_layout_definitions(_LAYOUTS_ROOT)
    era_ids = {d.era_id for d in definitions}

    assert "2026_format_sample" in era_ids
    assert "2015_2017_format_a" in era_ids
    assert len(definitions) == 2
