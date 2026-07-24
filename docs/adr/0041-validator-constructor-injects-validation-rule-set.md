# 0041. Validator Constructor-Injects ValidationRuleSet

## ステータス
Accepted

> **注記（Task9.1で追記）**: `RuleEngine`および`ValidationResult`形状に関する副次判断は[ADR-0043](0043-validator-produces-validation-result-with-rule-engine.md)で更新された。単一入力`run()`・コンストラクタ注入という本ADRの核心決定自体は変更されていない（詳細は本ADR末尾の「関連ADR」節を参照）。

## コンテキスト（Context）

[ADR-0040](0040-normalizer-produces-normalization-result.md)は、`Normalizer.run()`の2引数契約（`context, record, knowledge`）が`PipelineStage[TIn, TOut]`の単一入力規約に違反していることを発見し、`KnowledgeSnapshot`をコンストラクタで注入する解決パターンを確立した。同ADRのConsequences節は「将来のValidator実装（`Validator.run(context, record, rules: ValidationRuleSet)`も同型の2引数問題を抱える）は、本ADRの解決パターンをそのまま適用できるが、Validator自体の実装は本ADRの範囲外とし、Validator実装タスク着手前に本ADRを参照して確定する」と明記していた。

Phase2 Task9-0（Architecture Verification）は、この未確定事項をValidator実装（Task9想定）着手前に確定することを要求する。

## 問題（Problem）

現行の[`docs/api/interfaces.md`](../api/interfaces.md)は`Validator.run(context, record: NormalizedRecord, rules: ValidationRuleSet) -> ValidationResult`と定めており、`PipelineStage[TIn, TOut]`（[`docs/api/pipeline.md`](../api/pipeline.md)）が要求する単一入力に違反している。`PipelineRunner.run()`は`stage.run(context, current)`という2引数呼び出ししか行わないため、`rules`を渡す経路がない。

## 決定（Decision）

### 1. `ValidationRuleSet`はコンストラクタで注入し、`run()`は単一入力にする

[ADR-0040](0040-normalizer-produces-normalization-result.md)が確立した解決パターンをそのまま適用する。

```python
class Validator:
    def __init__(self, rules: ValidationRuleSet) -> None: ...
    def run(self, context: PipelineContext, record: NormalizedRecord) -> ValidationResult: ...
```

`Validator`は`PipelineStage[NormalizedRecord, ValidationResult]`を満たす。`ValidationRuleSet`は呼び出し元（`pipeline/`のJobRunner想定）が`Validator`のインスタンス化時に注入する（`Normalizer(knowledge, ...)`・`FieldExtractor(confidence_threshold=...)`と同型のコンストラクタ注入パターン）。

### 2. `RuleEngine`等の追加抽象は導入しない

Task9-0は「`ValidationRuleSet`、`RuleEngine`、`KnowledgeSnapshot`など複数入力はコンストラクタ注入で統一する」ことを要求したが、検証の結果、Validatorがコンストラクタで受け取る値オブジェクトは`ValidationRuleSet`のみで足りることを確認した。

- `ValidationRuleSet.rules: tuple[KnowledgeItem, ...]`は、`knowledge/validation/`（[`docs/knowledge/schema.md`](../knowledge/schema.md#validation)）の`category="validation"`エントリのみを既に集約した値オブジェクトであり、Validatorが必要とするドメイン知識（許容値集合・制約ルール）はこれ単体で完結する。`KnowledgeSnapshot`（8カテゴリ全体、Normalizer向け）を別途Validatorに注入する必要はない。
- ルール評価ロジック（`rule_type`ごとの分岐、[`docs/knowledge/schema.md`](../knowledge/schema.md#validation)の`allowed_value_set`/`cross_field_constraint`/`date_range_constraint`）は`Validator`内部の関数として実装し、「`RuleEngine`」という独立した注入可能コンポーネントとしては切り出さない。現時点でルール評価アルゴリズムを差し替え可能にする要求はなく、抽象を増やすことは[`docs/implementation.md`](../implementation.md)・[ADR-0014](0014-development-discipline.md)が戒める過剰設計（YAGNI）にあたる。将来、ルール評価方式の複数化が必要になった場合は、そのときに新規ADRで導入を検討する。

### 3. `ValidationResult`の形状は変更しない

Task9-0が示す保持してよい情報（ValidationError/ValidationWarning/Confidence/RuleResult/ValidatedAt）・保持してはいけない情報（NormalizedRecordのコピー/Review情報/Correction情報）を、既存の[`docs/api/models.md`](../api/models.md)の`ValidationResult`定義と照合した結果、**変更なしで両方を満たす**ことを確認した。

```python
@dataclass(frozen=True, slots=True)
class ValidationViolation:
    rule_id: str
    severity: Literal["error", "warning"]
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    subject_ref: NormalizedRecord
    status: Literal["passed", "failed"]
    violations: tuple[ValidationViolation, ...]
    confidence: Confidence
    validated_at: datetime
```

- **ValidationError/ValidationWarning → `ValidationViolation`**: `severity: Literal["error", "warning"]`により1つの型で両方を表現する（`error`側がValidationError、`warning`側がValidationWarningに相当）。個別の型に分離する要求ではなく、区分そのものが表現できていることを確認した。
- **RuleResult → `ValidationViolation`**: `rule_id`（どのルールか）・`severity`・`message`を保持しており、ルール評価結果としての情報は既に揃っている。全ルール（合格したものも含む）を網羅的に記録する設計（`FieldExtractionResult.candidates`等が採用する「集約結果が全評価対象を内包する」パターン）は、Field Extractor/Normalizerが「複数候補から採用するものを選ぶ」ために候補全件を必要とするのに対し、Validatorは単一の`NormalizedRecord`に対する合否判定であり同じ必要性がないため、採用しない（下記「検討した代替案」参照）。
- **ValidatedAt → `validated_at`**: 既存フィールドがそのまま対応する。
- **Confidence → `confidence`**: 既存フィールドがそのまま対応する。
- **`subject_ref: NormalizedRecord`は保持してはいけない情報（NormalizedRecordのコピー）に該当しない**: [`architecture-contract.md`](../architecture/architecture-contract.md)保証6が既に確定しているとおり、`subject_ref`は検証**対象への参照**であり、値のコピーや改変版ではない。[ADR-0006](0006-pipeline-provenance.md)の来歴管理原則（各段階の出力は入力元への参照を保持する）を満たすために必要であり、除外すると`ValidationResult`単体からどの`NormalizedRecord`を検証した結果かが分からなくなる。Task9-0の禁止事項が指すのは「修正後の値を新たに保持すること」（保証6の趣旨）であり、既存の参照保持は対象外と判断した。
- **Review情報・Correction情報を保持しないこと**: 現行`ValidationResult`にはそのようなフィールドは存在せず、既に満たされている。

## 検討した代替案

- **`ValidationResult`に全ルール（合格含む）の評価結果を保持する`results: tuple[RuleResult, ...]`を新設する**: `FieldExtractionResult`/`NormalizationResult`が確立した「集約結果が全評価対象を内包する」パターンとの一貫性は魅力的だが、Validatorのユースケース（単一`NormalizedRecord`の合否判定、複数候補からの選択を伴わない）ではこの情報の消費者が存在しない。`violations`のみで`status`（合否）を導出可能という既存の不変条件と非破壊的に両立する追加ではあるものの、要求されない情報を持たせる設計は[ADR-0014](0014-development-discipline.md)の開発規律に反するため、現時点では採用しない。将来「どのルールが合格したか」を監査する具体的な要求が生じた場合は、新規ADRで追加を検討する。
- **`RuleEngine`を独立した注入可能コンポーネントとして新設する**: 「検討した代替案」ではなく採用しなかった理由を上記2節に記載。

## 結果（トレードオフ, Consequences）

- `docs/api/interfaces.md`の`Validator.run()`のシグネチャが`(context, record, rules) -> ValidationResult`から`(context, record) -> ValidationResult`（`rules`はコンストラクタ引数）に変わる、破壊的変更である。呼び出し元は未実装（`pipeline/`のJobRunner本実装は将来Task）のため、影響は本ADR時点でのドキュメント同期のみ。
- `ValidationResult`・`ValidationViolation`は無変更のため、既存の`repositories/sqlite/candidate.py`（`update_validation`）・既存テストへの影響はない。
- `validators/`の依存先は`models/`, `utils/`のみのまま変更なし（`ValidationRuleSet`は`models/`に属する値オブジェクト）。

## Migration

1. `docs/api/interfaces.md`・`docs/api/package-design.md`・`docs/api/dependency-rule.md`を本ADRの内容に同期する（同一PR）。
2. 実装（Validator実装タスク、Task9想定）で`src/mod_personnel_db/validators/`を新規実装する際、`Validator.__init__(self, rules: ValidationRuleSet) -> None`・`run(self, context: PipelineContext, record: NormalizedRecord) -> ValidationResult`のシグネチャに従う。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/api/interfaces.md`](../api/interfaces.md) | `Validator`をコンストラクタ注入＋単一入力`run()`に変更（TODO注記を解消） |
| [`docs/api/package-design.md`](../api/package-design.md) | `validators/`節の責務説明を更新（`ValidationRuleSet`はコンストラクタ注入） |
| [`docs/api/dependency-rule.md`](../api/dependency-rule.md) | エッジ表に`validators/` → `knowledge/`禁止・`ValidationRuleSet`注入経路の行を追加（Normalizerの行6と対称） |

## 関連ADR
- [ADR-0005](0005-knowledge-base-normalization.md) — Knowledge Base正規化の全体方針。`ValidationRuleSet`が`knowledge/validation/`由来であることの前提。
- [ADR-0006](0006-pipeline-provenance.md) — パイプライン来歴管理。`ValidationResult.subject_ref`を維持する理由の根拠。
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0014](0014-development-discipline.md) — 開発規律。`RuleEngine`等の過剰な抽象を導入しない判断根拠。
- [ADR-0037](0037-layout-detector-produces-layout-artifact.md) — 単一入力`run()`への修正パターンの最初の先例。
- [ADR-0040](0040-normalizer-produces-normalization-result.md) — 本ADRが直接適用する、コンストラクタ注入による単一入力化の確立元。
- [ADR-0043](0043-validator-produces-validation-result-with-rule-engine.md) — 本ADRの副次判断（「`ValidationResult`は変更不要」「`RuleEngine`は不要」）を、Phase2 Task9の実装要求に基づき改めた後継ADR。単一入力`run()`・コンストラクタ注入という本ADRの核心決定はADR-0043でも変更されていない。

（本ADRはADR-0005/0006/0011/0014/0037/0040のいずれの核心決定も変更しないため、Supersededにはしない。ADR-0043は本ADRの核心決定を維持したまま副次判断のみを改めるものであり、本ADR自体もSupersededにはしない。）
