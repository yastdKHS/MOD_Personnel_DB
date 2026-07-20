# 0043. Validator Produces ValidationResult with RuleEngine

## ステータス
Accepted

## コンテキスト（Context）

[ADR-0041](0041-validator-constructor-injects-validation-rule-set.md)（Phase2 Task9-0）は、Validatorの単一入力化（`ValidationRuleSet`のコンストラクタ注入）を確定する一方、以下2点を「不要」と判断していた。

1. `ValidationResult`/`ValidationViolation`の形状変更 — 既存形状（`subject_ref`/`status`/`violations`/`confidence`/`validated_at`）のままで、Task9-0が示す保持してよい情報を満たすと判断した。
2. `RuleEngine`の新設 — ルール評価アルゴリズムを差し替え可能にする具体的要求がなく、過剰設計（YAGNI）にあたると判断した。同様に`KnowledgeSnapshot`のValidatorへの追加注入も不要と判断した（`ValidationRuleSet`単体で足りるため）。

Phase2 Task9（Validator Implementation）は、実装対象として明示的に`ValidationError`, `ValidationWarning`, `ValidationEvidence`, `ValidationCandidate`, `ValidationResult`を列挙し、`ValidationRuleSet`・`KnowledgeSnapshot`・`RuleEngine`をコンストラクタ注入することを要求した。これはADR-0041の上記2点の判断と直接矛盾する。

実装に着手して判断したところ、この矛盾は単なる名称の揺れではなく、実装上も正当な理由があることが判明した。

- `NormalizedRecord.normalized_fields`のキーは列位置ベースの汎用名（`column_1`等、[ADR-0038](0038-field-extractor-produces-field-extraction-result.md)/[ADR-0040](0040-normalizer-produces-normalization-result.md)）のままである（Normalizerは`normalized_fields`のキーをリネームしない、ADR-0040）。したがってValidatorが「`rank`フィールドの値が許容階級か」のような意味的な検証を行うには、Normalizerが内部的に行っているのと同じ`column_N`→意味的フィールド名の対応付け（`knowledge/layout`カテゴリ、[ADR-0039](0039-normalizer-field-mapping-via-extended-layout-knowledge.md)）を、Validator自身も参照できる必要がある。これには`ValidationRuleSet`（`category="validation"`のみ）では不足し、`KnowledgeSnapshot`（`category="layout"`を含む全カテゴリ）が必要になる。
3. ルール種別（`allowed_value_set`等、[`docs/knowledge/schema.md`](../knowledge/schema.md#validation)）ごとの評価ロジックを独立した`RuleEngine`に切り出すことで、Validator本体（オーケストレーション・フィールド反復・Evidence構築）とルール評価そのもの（`KnowledgeItem`との照合）を分離でき、テスト容易性が向上する。

`ValidationResult`の再定義については、影響範囲を確認したところ、既存の`ValidationResult`/`ValidationViolation`は`repositories/sqlite/candidate.py`の`update_validation()`（`result.status`のみ参照）と、`tests/unit/repositories/test_candidate.py`の2箇所でのみ使用されており、[ADR-0040](0040-normalizer-produces-normalization-result.md)のコンテキストで確認した`NormalizedRecord`（`GoldRepository`・公開JSON輸出フォーマットに深く依存）ほどの影響範囲を持たない。したがって再定義に伴う「範囲外コードの追随修正」は`update_validation()`の型シグネチャと2件の既存テストに限定され、Gold/Export領域には及ばない。

## 問題（Problem）

1. `ValidationResult`/`ValidationViolation`の形状がTask9の実装対象一覧（`ValidationError`/`ValidationWarning`/`ValidationEvidence`/`ValidationCandidate`/`ValidationResult`）と一致しない。
2. Validatorが意味的なValidation Ruleを適用するには`KnowledgeSnapshot`（`category="layout"`によるフィールド名解決）が必要であり、`ValidationRuleSet`単体では不足する。
3. ルール種別ごとの評価ロジックを独立させる`RuleEngine`が存在しない。

## 決定（Decision）

### 1. `ValidationResult`を`FieldExtractionResult`/`NormalizationResult`と同型の集約結果パターンに再定義する

```python
@dataclass(frozen=True, slots=True)
class ValidationError:
    rule_id: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationWarning:
    rule_id: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationEvidence:
    record_index: int
    layout_id: str
    rules_evaluated: int


@dataclass(frozen=True, slots=True)
class ValidationCandidate:
    record_index: int
    score: float
    errors: tuple[ValidationError, ...]
    warnings: tuple[ValidationWarning, ...]
    evidence: ValidationEvidence


@dataclass(frozen=True, slots=True)
class ValidationResult:
    status: Literal["passed", "failed"]
    candidates: tuple[ValidationCandidate, ...]
    confidence: Confidence
    validated_at: datetime
```

`Validator.run()`は`NormalizedRecord`を1件ずつ受け取るため、`candidates`は常に1件（`FieldExtractionResult.records`が閾値未満を除外して0件になり得るのとは異なり、Validatorは常に検証結果を返す。「検証を実施しない」という状態はない）。`status`は`candidates[0].errors`が空かどうかから導出する（既存の不変条件「`status == "failed"`であるとき、かつその場合に限り、`errors`が1件以上存在する」を維持）。

`subject_ref: NormalizedRecord`は保持しない。ADR-0006の来歴管理原則は、`ValidationEvidence.record_index`・`layout_id`（`NormalizedRecord.raw_record_ref`から取得可能な値）によって引き続き満たされる。呼び出し元（`pipeline/`のJobRunner想定）は、Validatorに渡した`NormalizedRecord`をそれ自身が保持しているため、`ValidationResult`から逆参照する必要がない（`repositories/sqlite/candidate.py`の`update_validation(candidate_id, result)`が`candidate_id`を別引数で受け取るのと同じ理由、[ADR-0039](0039-normalizer-field-mapping-via-extended-layout-knowledge.md)のコンテキストで確認済みの設計）。

### 2. Validatorは`ValidationRuleSet`・`KnowledgeSnapshot`・`RuleEngine`をコンストラクタ注入で受け取る

```python
class Validator:
    def __init__(
        self,
        rules: ValidationRuleSet,
        knowledge: KnowledgeSnapshot,
        engine: RuleEngine | None = None,
    ) -> None: ...

    def run(self, context: PipelineContext, record: NormalizedRecord) -> ValidationResult: ...
```

`KnowledgeSnapshot`は、Normalizerが`column_N`→意味的フィールド名の対応付けに使うのと同じ`category="layout"`エントリ（[ADR-0039](0039-normalizer-field-mapping-via-extended-layout-knowledge.md)）をValidatorも参照するために必要となる。`RuleEngine`はデフォルト値`None`（内部で標準実装を構築）を持ち、コンストラクタで差し替え可能とする。

### 3. `RuleEngine`はフィールド単位のルール評価のみを担う

```python
class RuleEngine:
    def evaluate_field(
        self, field_name: str, value: str, rules: ValidationRuleSet
    ) -> ValidationError | None: ...
```

`category="validation"`の`KnowledgeItem`は、既存の`item_key`/`canonical_value`規約（[ADR-0040](0040-normalizer-produces-normalization-result.md)が確立した規約の延長）をそのまま用いる。`item_key`が対象フィールド名（意味的フィールド名、例: `"rank"`）、`canonical_value`が許容される値の1つを表す。同一`item_key`を持つ複数の`KnowledgeItem`が、1フィールドの許容値集合（`allowed_value_set`）を構成する。該当`item_key`のエントリが1件も存在しないフィールドは「制約なし」として扱い、エラーを生成しない（許容値集合が未定義のフィールドを一律エラーにはしない、寛容側に倒す）。

Validator本体は、`record.raw_record_ref.layout_id`と`KnowledgeSnapshot`の`category="layout"`エントリから各フィールドの意味的名称を解決し（Normalizerと同じ規約、ただし`validators/`は`normalizers/`に依存しないため解決ロジックは`validators/`内に独立して実装する、[`dependency-rule.md`](../api/dependency-rule.md)の「他段階間の直接依存を持たない」制約）、意味的名称が解決できたフィールドについて`RuleEngine.evaluate_field()`を呼び出す。意味的名称が解決できなかったフィールド（`knowledge/layout`にマッピングが存在しない列）は`ValidationWarning`（`rule_id="layout.unmapped_field"`）とする（構造的な不確実性を警告として表現し、失敗扱いにはしない）。

## 検討した代替案

- **`subject_ref`相当の参照を`ValidationEvidence`に`NormalizedRecord`丸ごと持たせる**: [ADR-0040](0040-normalizer-produces-normalization-result.md)が確立した「参照ではあっても新たな深い埋め込みは増やさない」方針、および呼び出し元が既に`NormalizedRecord`を保持しているという実態から、冗長と判断し不採用。`record_index`/`layout_id`という軽量な識別情報で足りる。
- **`RuleEngine`をProtocolとして定義し、複数実装を許容する**: 現時点で複数実装（例: 外部ルールエンジンとの統合）の具体的要求がないため、単純な具象クラスとして実装し、将来Protocol化が必要になった場合に新規ADRで検討する（過剰設計を避ける、[ADR-0014](0014-development-discipline.md)）。

## 結果（トレードオフ, Consequences）

- `ValidationResult`/`ValidationViolation`の再定義は、[ADR-0041](0041-validator-constructor-injects-validation-rule-set.md)が「変更しない」とした判断を覆す。ただし影響範囲は`repositories/sqlite/candidate.py`（`update_validation`の型シグネチャ）と既存テスト2件に限定され、`GoldRepository`・公開JSON輸出フォーマットには影響しない（確認済み）。
- `validators/`の依存先に`models/`, `utils/`のみという制約は維持される（`KnowledgeSnapshot`・`RuleEngine`はいずれも`models/`側の値オブジェクト・具象クラスであり、`knowledge/`サービスパッケージへの依存は発生しない）。
- Validatorの意味的フィールド名解決ロジックは、Normalizerの同等ロジックと重複する（`validators/`が`normalizers/`に依存できないため）。この重複は、中核パイプライン6段階が相互に依存しないという既存の設計制約（[`dependency-rule.md`](../api/dependency-rule.md)）の直接の帰結であり、意図的に許容する。

## Migration

1. `docs/api/models.md`・`docs/api/interfaces.md`・`docs/api/package-design.md`を本ADRの内容に同期する（同一PR）。
2. `src/mod_personnel_db/models/candidate.py`から`ValidationViolation`・旧`ValidationResult`を削除し、`src/mod_personnel_db/models/validation.py`を新設して`ValidationError`, `ValidationWarning`, `ValidationEvidence`, `ValidationCandidate`, `ValidationResult`を定義する。
3. `src/mod_personnel_db/repositories/sqlite/candidate.py`の`update_validation()`・`src/mod_personnel_db/repositories/__init__.py`のProtocolを追随修正する。
4. `tests/unit/repositories/test_candidate.py`の`ValidationResult`/`ValidationViolation`構築箇所を追随修正する。
5. `src/mod_personnel_db/validators/`を新規実装する（Task9）。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/api/models.md`](../api/models.md) | `ValidationResult`を再定義。`ValidationError`・`ValidationWarning`・`ValidationEvidence`・`ValidationCandidate`・`RuleEngine`を新設 |
| [`docs/api/interfaces.md`](../api/interfaces.md) | `Validator`のコンストラクタに`knowledge: KnowledgeSnapshot`・`engine: RuleEngine`を追加 |
| [`docs/api/package-design.md`](../api/package-design.md) | `validators/`節を更新（`KnowledgeSnapshot`参照理由・`RuleEngine`導入） |
| [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) | 保証6の`ValidationResult`構成記述・`subject_ref`廃止を反映 |

## Future Improvements

本節は、Phase2 Task9.1（Documentation Update、Task9 Reviewの推奨事項反映）で記録する**将来の実装拡張候補**である。現時点では実装変更を行わない（後述「実装範囲（Version 2.0時点）」参照）。

**実装範囲（Version 2.0時点）**: `RuleEngine`は`category="validation"`の`KnowledgeItem`について、`item_key`（対象フィールド名）に対する`canonical_value`（許容値）の集合照合——[`docs/knowledge/schema.md`](../knowledge/schema.md#validation)が定める`rule_type`のうち`allowed_value_set`相当——のみを実装対象とした。これは現行のTask9実装要件を満たすために必要十分な範囲であり、意図的な最小実装である（[ADR-0014](0014-development-discipline.md)の開発規律、過剰設計を避ける方針に基づく）。

**未実装として意図的に対象外とした項目**:

- **`cross_field_constraint`**: `docs/knowledge/schema.md`が定める、あるフィールドの値に応じて別フィールドの許容値を制約するルール種別。`KnowledgeItem`（実装済みモデル）は`item_key`/`canonical_value`の平坦な形状のみを持ち、`if_field`/`if_value`/`then_field`/`then_allowed`という多項の構造を表現できない。
- **`date_range_constraint`**: 発令日等の日付範囲制約。同様に`KnowledgeItem`の現行形状では表現できない。
- **`severity`別評価（error/warning）**: `docs/knowledge/schema.md`は`category="validation"`エントリに`severity: error | warning`を持たせ、`error`は`status=failed`、`warning`は`learning_dataset`記録のみとする設計を示すが、`KnowledgeItem`は`severity`フィールドを持たず、`RuleEngine`は`ValidationError`のみを生成する（`ValidationWarning`は`knowledge/layout`未解決時にのみ用いる別概念）。
- **`effective_from`/`effective_to`による期間評価**: Validatorが`knowledge/layout`エントリの解決（`_resolve_semantic_field_name`）では`KnowledgeSnapshot.as_of`による期間絞り込みを行っているのに対し、`RuleEngine.evaluate_field()`は`ValidationRuleSet`の`category="validation"`エントリに対して同様の期間絞り込みを行わない（`ValidationRuleSet.as_of`は現状未使用）。

**現時点での判断**: 上記はいずれも**設計変更しない**。`RuleEngine`はVersion 2.0の実装要件（`allowed_value_set`相当のチェック）を満たしており、現行のValidator/Normalizer責務境界・依存制約とも整合する。拡張候補は、実際の`knowledge/validation/`データで複数`rule_type`・`severity`分岐・期間付きルールが必要になった時点で、新規ADRの起票を通じて再評価する（[`docs/roadmap.md`](../roadmap.md)参照）。

## 関連ADR
- [ADR-0006](0006-pipeline-provenance.md) — パイプライン来歴管理。`subject_ref`除去後も`record_index`/`layout_id`で満たされることの根拠。
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0014](0014-development-discipline.md) — 開発規律。`RuleEngine`をProtocol化しない判断根拠。
- [ADR-0038](0038-field-extractor-produces-field-extraction-result.md) — 集約結果パターンの先例。
- [ADR-0039](0039-normalizer-field-mapping-via-extended-layout-knowledge.md) — `knowledge/layout`によるフィールド名解決規約の起点。Validatorが同じ規約を再利用する。
- [ADR-0040](0040-normalizer-produces-normalization-result.md) — `item_key`/`canonical_value`によるKnowledge検索規約の起点。`validation`カテゴリにも同じ規約を適用する。
- [ADR-0041](0041-validator-constructor-injects-validation-rule-set.md) — 単一入力`run()`・コンストラクタ注入という核心決定の起点（本ADRでも変更しない）。「`ValidationResult`は変更不要」「`RuleEngine`は不要」という同ADRの2つの副次判断のみを、Task9の実装要求に基づき本ADRで改める。

（本ADRはADR-0006/0011/0014/0038/0039/0040のいずれの核心決定も変更しない。ADR-0041の核心決定（単一入力化・コンストラクタ注入パターン）も変更しないため、いずれもSupersededにはしない。ADR-0041自体は「関連ADR」として本ADRへの参照を追記するに留める。）
