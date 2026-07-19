# 0040. Normalizer Produces NormalizationResult via Constructor-Injected KnowledgeSnapshot

## ステータス
Accepted

## コンテキスト（Context）

Phase2 Task8（Normalizer Implementation）は、`normalizers/`を新規実装するにあたり以下を明示的に要求した。

- `Normalizer.run()`は`PipelineStage[RawRecord, NormalizationResult]`を実装する。
- 実装対象の型として`Normalizer`, `NormalizerError`, `NormalizedRecord`, `NormalizedField`, `NormalizationEvidence`, `NormalizationCandidate`, `NormalizationResult`を列挙。
- Knowledgeは`KnowledgeSnapshot`のみを受け取る。
- `NormalizedRecord`は「raw値・normalized値・normalization_method・knowledge_versionのみ保持する」。
- 実装してよい処理に「意味的フィールド名対応」を含む。

実装に着手したところ、以下3件の構造的な矛盾・未確定事項が判明した。

### 1. `Normalizer.run()`の2引数契約が`PipelineStage[TIn, TOut]`の単一入力規約に違反する

現行の[`docs/api/interfaces.md`](../api/interfaces.md)は`Normalizer.run(context, record: RawRecord, knowledge: KnowledgeSnapshot) -> NormalizedRecord`と定めている。これは`PipelineStage[TIn, TOut]`（[`docs/api/pipeline.md`](../api/pipeline.md)）が要求する単一入力（`run(context, input: TIn) -> TOut`）に違反しており、[`src/mod_personnel_db/pipeline/runner.py`](../../src/mod_personnel_db/pipeline/runner.py)の`PipelineRunner.run()`は`stage.run(context, current)`という2引数呼び出ししか行わない（`knowledge`を渡す経路がない）。これは[ADR-0037](0037-layout-detector-produces-layout-artifact.md)が`SectionParser.run()`について発見・解決したのと同種の問題である。

### 2. `NormalizedRecord`を要求どおりの4属性に再定義すると、`normalizers/`の外側に破壊的影響が及ぶ

既存の`NormalizedRecord`（Phase1/Task2設計、`models/candidate.py`）は`raw_record_ref: RawRecord`, `normalized_fields: Mapping[str, NormalizedValue]`, `normalization_applied: tuple[KnowledgeItemId, ...]`, `normalized_at: datetime`という形状であり、`GoldRepository`（`repositories/sqlite/gold.py`）・`CandidateRepository`（`repositories/sqlite/candidate.py`）・公開JSON輸出フォーマット（[`docs/database/json_schema.md`](../database/json_schema.md)の`NormalizedValue`、[ADR-0016](0016-public-json-format.md)）・既存テスト（`test_candidate.py`, `test_gold.py`, `test_validation.py`）に既に深く依存されている。Task8自身がNormalizerに対しRepository・JSON生成・Exportへの依存を禁止している以上、`NormalizedRecord`を要求どおりの4属性（`raw`/`normalized`/`normalization_method`/`knowledge_version`）に破壊的変更すると、この禁止と矛盾する範囲外コード（Gold/Export/Repository/既存テスト）の追随修正が必要になる。ユーザーに確認したところ、**既存`NormalizedRecord`は変更せず維持し、要求された4属性は新設の`NormalizedField`等で表現する**方針が選択された。

### 3. `column_N`→意味的フィールド名マッピング・ドメイン知識検索の具体的な参照規約が未確定

[ADR-0039](0039-normalizer-field-mapping-via-extended-layout-knowledge.md)は`knowledge/layout`カテゴリのスコープ拡張と`RawRecord.layout_id`追加を方針として決定したが、マッピングエントリの具体的なJSON Schema形状・`KnowledgeItem`の`item_key`/`canonical_value`の解釈規約は「Normalizer実装タスクで確定する」として本ADRに委譲していた。

## 問題（Problem）

1. `Normalizer.run()`の2引数契約が`PipelineStage[TIn, TOut]`の単一入力規約に違反している。
2. `NormalizedRecord`をTask8の要求どおり再定義すると、`normalizers/`の外側（Gold/Export/Repository/既存テスト）に、Task8自身が禁止する範囲の変更が波及する。
3. `column_N`→意味的フィールド名マッピング、および`alias`/`organization`/`position`/`rank`/`typography`各カテゴリの`KnowledgeItem`検索規約が未確定である。

## 決定（Decision）

### 1. `KnowledgeSnapshot`はコンストラクタで注入し、`run()`は単一入力にする

[ADR-0037](0037-layout-detector-produces-layout-artifact.md)が`SectionParser.run()`について確立した解決パターンと同型で解決する。

```python
class Normalizer:
    def __init__(self, knowledge: KnowledgeSnapshot, *, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None: ...
    def run(self, context: PipelineContext, record: RawRecord) -> NormalizationResult: ...
```

`Normalizer`は`PipelineStage[RawRecord, NormalizationResult]`を満たす。`KnowledgeSnapshot`は呼び出し元（`pipeline/`のJobRunner想定）が`Normalizer`のインスタンス化時に注入する（`FieldExtractor.__init__(confidence_threshold=...)`と同型のコンストラクタ注入パターン）。これにより「Knowledgeは`KnowledgeSnapshot`のみ受け取る」という要求を満たしつつ、`PipelineRunner.run()`の`stage.run(context, current)`という単一入力呼び出しにそのまま適合する。

この設計上、`docs/api/interfaces.md`が定める`Normalizer.run(context, record, knowledge) -> NormalizedRecord`という現行契約は**本ADRにより置き換えられる**。将来のValidator実装（`Validator.run(context, record, rules: ValidationRuleSet)`も同型の2引数問題を抱える）は、本ADRの解決パターンをそのまま適用できるが、Validator自体の実装は本ADRの範囲外とし、Validator実装タスク着手前に本ADRを参照して確定する。

### 2. `NormalizationResult`はFieldExtractor（ADR-0038）と同型の集約結果パターンとし、既存`NormalizedRecord`をそのまま内包する

```python
@dataclass(frozen=True, slots=True)
class NormalizedField:
    name: str              # RawField.nameと同じキー（column_N、意味的フィールド名へのリネームは行わない）
    raw: str
    value: str
    normalization_method: str  # "typography" | "alias" | "organization" | "position" | "rank" | "identity"


@dataclass(frozen=True, slots=True)
class NormalizationEvidence:
    layout_id: str
    knowledge_version: str     # KnowledgeSnapshot.snapshot_checksum
    matched_item_ids: tuple[KnowledgeItemId, ...]


@dataclass(frozen=True, slots=True)
class NormalizationCandidate:
    record_index: int
    score: float
    fields: tuple[NormalizedField, ...]
    evidence: NormalizationEvidence


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    records: tuple[NormalizedRecord, ...]   # 既存NormalizedRecord。無変更
    candidates: tuple[NormalizationCandidate, ...]
    confidence: Confidence
```

`NormalizedField.name`は`RawField.name`と同じキー（`column_N`等）を維持する。これは既存`NormalizedRecord.__post_init__`の不変条件「`normalized_fields`のキー集合は`raw_record_ref.raw_fields`のキー集合と一致する」を変更せずに満たすためであり、意味的フィールド名（`name`/`rank`等）への対応付けは、どの`KnowledgeItem`カテゴリを検索するかを選ぶ**内部的な判定**としてのみ用いる（対応付け結果を出力のキーとして露出しない）。

`NormalizationCandidate.score`が閾値以上の場合、`candidate.fields`から既存形状の`NormalizedRecord`（`raw_record_ref`, `normalized_fields={f.name: NormalizedValue(value=f.value, raw=f.raw) for f in fields}`, `normalization_applied=evidence.matched_item_ids`, `normalized_at`）を構築し`NormalizationResult.records`に含める。Task8が要求した「`NormalizedRecord`には raw値・normalized値・normalization_method・knowledge_versionのみ保持する」という意図は、`NormalizedField`（`raw`/`value`/`normalization_method`）と`NormalizationEvidence.knowledge_version`によってフィールド単位・候補単位で表現される。

### 3. `RawRecord.layout_id: str`を確定し、意味的フィールド名マッピング・Knowledge検索規約を確定する

[ADR-0039](0039-normalizer-field-mapping-via-extended-layout-knowledge.md)が決定した`RawRecord.layout_id: str`（era_id）追加を本ADRで実装確定する。Field Extractorは`section.layout_id`を`RawRecord.layout_id`にコピーする（モデル変更の直接的な帰結として、`extractors/extractor.py`・`repositories/sqlite/candidate.py`を本PRで追随修正する。[ADR-0037](0037-layout-detector-produces-layout-artifact.md)が`PersonnelSection.layout_id`型変更時にRepositoryを同一PRで修正した前例と同型）。

Knowledge検索規約（`KnowledgeItem`の既存の汎用形状`id`/`category`/`source_file`/`item_key`/`canonical_value`/`effective_from`/`effective_to`/`provenance_source`/`version`をそのまま用いる。新規モデル拡張は行わない）:

- **意味的フィールド名マッピング**: `category="layout"`、`item_key=f"{layout_id}.{raw_field_name}"`（例: `"format_a.column_1"`）、`canonical_value`が意味的フィールド名（例: `"name"`）。一致するエントリがない場合、その列は意味的フィールドに対応付けず、typography正規化のみ適用する。
- **`alias`/`organization`/`position`/`rank`**: `category`が対応するカテゴリ名、`item_key`が認識対象の表記（typography正規化後の値）、`canonical_value`が正規化後の値。一致するエントリがない場合、typography正規化後の値をそのまま採用する（`normalization_method="typography"`）。
- **`typography`**: `category="typography"`、`item_key`が置換対象の文字列（リテラル部分文字列）、`canonical_value`が置換後の文字列。全件を順に`str.replace`で適用する（正規表現のハードコードを避け、[`architecture-contract.md`](../architecture/architecture-contract.md)保証5の「ドメイン固有regexを持たない」に従う）。加えてUnicode NFKC正規化を機械的に適用する（`knowledge/`データに依存しない汎用的な文字正規化であり、ドメイン知識ではないため`normalizers/`のコードに直接実装してよい）。
- **`effective_from`/`effective_to`による絞り込み**: `KnowledgeSnapshot.as_of`を基準日とし、これを含む有効期間のエントリのみを候補とする（`effective_from`/`effective_to`が`None`の場合は無期限とみなす）。

## 検討した代替案

- **`Normalizer.run()`を2引数のまま維持し、`PipelineRunner`側を拡張してStageごとの追加引数を許容する**: `PipelineStage[TIn, TOut]`という確立済みの単一入力契約（[`docs/api/pipeline.md`](../api/pipeline.md)、Phase2 Task3）を崩すことになり、Validator（同様に`rules: ValidationRuleSet`を追加引数として持つ）にも波及する大掛かりな変更になるため採用しなかった。
- **`NormalizedRecord`を要求どおり再定義し、Gold/Export/Repository/既存テストを本PRで追随修正する**: ユーザーへの確認により不採用（「既存NormalizedRecordは維持、新型で表現」を選択）。
- **`column_N`→意味的フィールド名マッピングを`knowledge/layout`ではなく`NormalizedField.name`自体に反映する（キーをリネームする）**: 既存`NormalizedRecord.__post_init__`の不変条件（`normalized_fields`キー集合が`raw_record_ref.raw_fields`キー集合と一致）を破壊するため、既存`NormalizedRecord`を維持するという上記決定と矛盾し、採用しなかった。

## 結果（トレードオフ, Consequences）

- `docs/api/interfaces.md`の`Normalizer.run()`のシグネチャが`(context, record, knowledge) -> NormalizedRecord`から`(context, record) -> NormalizationResult`（`knowledge`はコンストラクタ引数）に変わる、破壊的変更である。呼び出し元は未実装（`pipeline/`のJobRunner本実装は将来Task）のため、影響は本ADR時点でのドキュメント同期のみ。
- `RawRecord.layout_id: str`追加は、既に実装済みの`RawRecord`に対する破壊的変更である。`src/mod_personnel_db/models/candidate.py`・`src/mod_personnel_db/extractors/extractor.py`・`src/mod_personnel_db/repositories/sqlite/candidate.py`・関連テストを本PRで追随修正する。
- `NormalizedRecord`自体は無変更のため、Gold/Export/既存テストへの影響はない。
- Validator実装タスクは、本ADRが確立した「コンストラクタ注入＋単一入力`run()`」パターンを`ValidationRuleSet`にも適用する必要がある（TODO、Validator実装タスク着手前に本ADRを参照）。
- Knowledge検索規約（`item_key`/`canonical_value`の解釈）は、8カテゴリ全体で汎用的な「認識表記→正規化後の値」の対応として統一され、[`docs/knowledge/schema.md`](../knowledge/schema.md)のスキーマ自体（`LayoutEntry`等の詳細フィールド）は変更しない。`KnowledgeItem`（`models/knowledge.py`）は`docs/knowledge/schema.md`が定める詳細スキーマを実装時点でフラット化した形（`item_key`/`canonical_value`）であるため、本ADRの規約はこの既存の設計方針の範囲内である。

## Migration

1. `docs/api/interfaces.md`・`docs/api/models.md`・`docs/api/package-design.md`を本ADRの内容に同期する（同一PR）。
2. `src/mod_personnel_db/models/candidate.py`の`RawRecord`に`layout_id: str`を追加する。
3. `src/mod_personnel_db/models/normalization.py`を新設し、`NormalizedField`, `NormalizationEvidence`, `NormalizationCandidate`, `NormalizationResult`を定義する。
4. `src/mod_personnel_db/extractors/extractor.py`で`section.layout_id`を`RawRecord.layout_id`にコピーする。
5. `src/mod_personnel_db/repositories/sqlite/candidate.py`の`RawRecord`読み取りロジックを、`personnel_sections`とのJOINで`era_id`を取得するよう修正する。
6. `src/mod_personnel_db/normalizers/`を新規実装する（Task8）。
7. 既存テスト（`tests/unit/models/test_extraction.py`, `tests/unit/models/test_validation.py`, `tests/unit/repositories/test_candidate.py`, `tests/unit/repositories/test_gold.py`, `tests/unit/extractors/conftest.py`）の`RawRecord`構築箇所に`layout_id`を追加する。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/api/interfaces.md`](../api/interfaces.md) | `Normalizer`をコンストラクタ注入＋単一入力`run()`に変更 |
| [`docs/api/models.md`](../api/models.md) | `RawRecord.layout_id`追加を確定。`NormalizationResult`・`NormalizedField`・`NormalizationEvidence`・`NormalizationCandidate`を新設 |
| [`docs/api/package-design.md`](../api/package-design.md) | `normalizers/`節の責務説明を更新（`KnowledgeSnapshot`はコンストラクタ注入） |
| [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) | 保証5「実現方法」の`Normalizer.run()`シグネチャ記述を更新 |
| [`docs/api/dependency-rule.md`](../api/dependency-rule.md) | エッジ表6行目の`KnowledgeSnapshot`注入経路の記述を更新（引数→コンストラクタ） |

## 関連ADR
- [ADR-0005](0005-knowledge-base-normalization.md) — Knowledge Base正規化の全体方針。
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0037](0037-layout-detector-produces-layout-artifact.md) — 単一入力`run()`への修正パターン、およびモデル変更に伴うRepository追随修正の前例。
- [ADR-0038](0038-field-extractor-produces-field-extraction-result.md) — 集約結果パターン（`records`/`candidates`/`confidence`）の先例。
- [ADR-0039](0039-normalizer-field-mapping-via-extended-layout-knowledge.md) — `knowledge/layout`スコープ拡張・`RawRecord.layout_id`追加の方針決定。本ADRはその実装確定。

（本ADRはADR-0005/0011/0037/0038/0039のいずれの核心決定も変更しないため、Supersededにはしない。ADR-0039が委譲した「マッピングデータの具体的内容」を確定するものであり、ADR-0039の方針自体は変更しない。）
