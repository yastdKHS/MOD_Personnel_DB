"""テスト用の`LayoutDefinition`ビルダー。"""

from mod_personnel_db.models import LayoutDefinition, LayoutRule, LayoutRuleKind


def format_a_definition(*, era_id: str = "format_a", version: int = 1) -> LayoutDefinition:
    return LayoutDefinition(
        era_id=era_id,
        version=version,
        rules=(
            LayoutRule(
                rule_id="header",
                kind=LayoutRuleKind.HEADER_PATTERN,
                value="MOD PERSONNEL ORDER FORMAT A",
                weight=0.7,
            ),
            LayoutRule(
                rule_id="min_pages",
                kind=LayoutRuleKind.MIN_PAGE_COUNT,
                value="1",
                weight=0.3,
            ),
        ),
    )


def format_b_definition(*, era_id: str = "format_b", version: int = 1) -> LayoutDefinition:
    return LayoutDefinition(
        era_id=era_id,
        version=version,
        rules=(
            LayoutRule(
                rule_id="header",
                kind=LayoutRuleKind.HEADER_PATTERN,
                value="FORMAT B HEADER THAT WILL NOT MATCH",
                weight=1.0,
            ),
        ),
    )
