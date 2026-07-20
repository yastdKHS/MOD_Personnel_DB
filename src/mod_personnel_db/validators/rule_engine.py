"""フィールド単位のValidation Rule評価。docs/api/models.md#ruleengine, ADR-0043に対応する。"""

from mod_personnel_db.models import ValidationError, ValidationRuleSet


class RuleEngine:
    """`category="validation"`の`KnowledgeItem`に基づき、フィールド単位でルールを評価する。

    `item_key`が対象フィールド名（意味的フィールド名）、`canonical_value`が
    許容される値の1つを表す規約を用いる（`ADR-0040`が確立した規約の延長、
    `ADR-0043`）。同一`item_key`を持つ複数の`KnowledgeItem`が1フィールドの
    許容値集合（`allowed_value_set`）を構成する。該当エントリが存在しない
    フィールドは制約なしとして扱う。
    """

    def evaluate_field(
        self, field_name: str, value: str, rules: ValidationRuleSet
    ) -> ValidationError | None:
        allowed = {
            item.canonical_value
            for item in rules.rules
            if item.category == "validation" and item.item_key == field_name
        }
        if not allowed or value in allowed:
            return None
        return ValidationError(
            rule_id=f"validation.{field_name}.allowed_value_set",
            message=f"value {value!r} is not in the allowed set for field {field_name!r}",
        )
