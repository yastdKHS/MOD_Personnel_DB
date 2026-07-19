# 0038. Field Extractor Produces FieldExtractionResult

## ステータス
Accepted

## コンテキスト（Context）

Phase2 Task7-0（Architecture Verification）は、`docs/api/models.md`の`RawRecord`のValidation Ruleが「`raw_fields`のキー集合は、対応する様式が定義するフィールド集合の部分集合でなければならない」と定めている一方、この「様式が定義するフィールド集合」をField Extractorがどう取得するかが未確定であることを発見した。`LayoutDefinition`（[ADR-0035](0035-layout-detector-owns-pdf-content-access.md), [ADR-0036](0036-pyyaml-for-layout-definition.md)）の判定ルール語彙（`LayoutRuleKind`）にはフィールド抽出定義が含まれず、Field Extractor（`extractors/`）の依存先（`models/`, `utils/`のみ）は`layouts/`ディレクトリへのアクセスを許可しない。

Phase2 Task7（Field Extractor Implementation）は、この未確定事項を実装可能な形で解決することを要求する。同時に、Task7の指示は`FieldExtractor`を`PipelineStage[PersonnelSection, FieldExtractionResult]`として実装することを明示しており、これは現行の`docs/api/interfaces.md`が定める`FieldExtractor.run() -> tuple[RawRecord, ...]`という戻り値の型と食い違う。

## 問題（Problem）

1. `FieldExtractor.run()`の戻り値型が、現行設計（`tuple[RawRecord, ...]`）とTask7の要求（`FieldExtractionResult`）で食い違っている。
2. `RawRecord.raw_fields`のキー（フィールド名）をField Extractorがどう決定するかが未確定である。意味的なフィールド名（`name`/`rank`/`organization`等）を決定するには、様式ごとのフィールド定義（列位置とフィールド名の対応）が必要だが、そのようなスキーマは現時点で存在しない。

## 決定（Decision）

### 1. `FieldExtractor.run()`の戻り値を`FieldExtractionResult`とする

[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)の`LayoutArtifact`、[ADR-0037](0037-layout-detector-produces-layout-artifact.md)の`SectionParseResult`と同型のパターンを踏襲する。

```python
@dataclass(frozen=True, slots=True)
class RawField:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class ExtractionEvidence:
    line: str
    column_count: int


@dataclass(frozen=True, slots=True)
class ExtractionCandidate:
    record_index: int
    score: float
    fields: tuple[RawField, ...]
    evidence: ExtractionEvidence


@dataclass(frozen=True, slots=True)
class FieldExtractionResult:
    records: tuple[RawRecord, ...]
    candidates: tuple[ExtractionCandidate, ...]
    confidence: Confidence
```

`records`は確定した`RawRecord`（`candidates`のうちConfidence閾値以上のもの）。`candidates`は評価した全行（閾値未満を含む）。`RawRecord`自体の形状（`section_ref`, `record_index`, `raw_fields`, `extracted_at`）は無変更。`Normalizer.run(context, record: RawRecord, knowledge)`の入力契約も無変更（呼び出し元`pipeline/`のJobRunnerが`FieldExtractionResult.records`を1件ずつNormalizerへ渡す、[ADR-0037](0037-layout-detector-produces-layout-artifact.md)がSection Parser→Field Extractorで確立した「集約結果→個別処理」の受け渡しパターンと同型）。

### 2. フィールド名は列位置ベースの汎用名とする（Version 2.0の暫定解）

Field Extractorは`PersonnelSection.section_text`の各行を1レコード候補とみなし、行内の値を構造的な区切り（連続する空白等）で列に分割する。各列に対応する`RawField.name`は、意味的なフィールド名（`name`/`rank`等）ではなく、**列位置に基づく汎用名**（`column_1`, `column_2`, ...）とする。

これにより、Field Extractorは`layouts/`・`LayoutDefinition`・`knowledge/`のいずれにも依存せず、`PersonnelSection`（Section Parserの出力）のみを入力として動作できる。列位置から意味的なフィールド名への対応付け（例: 様式Aでは`column_1`が氏名、様式Bでは`column_2`が氏名）は、本ADRの範囲外とし、将来必要になった時点で新規ADR（`LayoutDefinition`へのフィールド抽出定義追加、または別の解決策）として検討する。

これに伴い、`docs/api/models.md`の`RawRecord`のValidation Ruleを「`raw_fields`のキー集合は、Field Extractorが構造的に認識した列の集合と一致する（`column_1`, `column_2`, ...の汎用名）」に修正する。Task7-0が発見した「未確定事項」の記述は、本ADRにより「Version 2.0時点での意図的な最小実装」という確定した記述に置き換える。

## 検討した代替案

- **`LayoutDefinition`にフィールド抽出定義（列位置→フィールド名のマッピング）を追加し、Field Extractorがこれを読み込む**: `LayoutDefinition`のYAMLロードは`layout/`パッケージの責務であり（[ADR-0036](0036-pyyaml-for-layout-definition.md)）、Field Extractorがこれを直接読み込むには新たな依存（`layouts/`ファイルI/O、または`layout/`パッケージへの依存）を追加する必要がある。これは`extractors/`の依存先を`models/`, `utils/`のみに限定する既存の設計判断（`docs/api/package-design.md`）およびTask7の禁止事項（新規責務の追加を伴う設計変更は本Taskの範囲外）に反するため採用しなかった。実データでの列位置とフィールド名の対応関係が明確になった段階で、改めて検討する。
- **Section ParserがField抽出に必要な情報を`PersonnelSection`に追加する**: `PersonnelSection`は永続化対象のモデルであり（`personnel_sections`テーブル、[`database/schema.md`](../database/schema.md#3-personnel_sections)）、フィールド定義情報を持たせることは責務の逸脱（Section Parserの責務は「セクションの切り出し」のみ、[ADR-0011](0011-fixed-core-pipeline.md)）にあたるため採用しなかった。

## 結果（トレードオフ, Consequences）

- 列位置ベースの汎用フィールド名（`column_1`等）は、そのままでは意味的な解釈ができない。Normalizer（段階5）が実際に「氏名」「階級」等の意味的な正規化を行うには、`column_N`から意味的フィールド名への対応付けが別途必要になる。この対応付けの方法（`LayoutDefinition`の拡張、`knowledge/`側での対応、Normalizer入力契約の拡張等）は本ADRの範囲外とし、Normalizer実装（Task8想定）着手前に新規ADRで確定する。
- `FieldExtractor.run()`の戻り値型が`tuple[RawRecord, ...]`から`FieldExtractionResult`に変わる、`docs/api/interfaces.md`に対する破壊的変更である。呼び出し元は本PRで追随修正する。

## Migration

1. `docs/api/interfaces.md`・`docs/api/models.md`・`docs/api/package-design.md`・`docs/architecture/architecture-contract.md`（保証10の表）を本ADRの内容に同期する（同一PR）。
2. `src/mod_personnel_db/models/extraction.py`に`RawField`, `ExtractionEvidence`, `ExtractionCandidate`, `FieldExtractionResult`を新設する。
3. `src/mod_personnel_db/extractors/`を新規実装する（Task7-1, 7-2, 7-3）。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/api/models.md`](../api/models.md) | `FieldExtractionResult`・`RawField`・`ExtractionEvidence`・`ExtractionCandidate`を新設。`RawRecord`のValidation Ruleを列位置ベースの汎用名に確定 |
| [`docs/api/interfaces.md`](../api/interfaces.md) | `FieldExtractor.run()`の戻り値を`FieldExtractionResult`に変更 |
| [`docs/api/package-design.md`](../api/package-design.md) | `extractors/`節の責務説明を更新（列認識・汎用フィールド名） |
| [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) | 保証10の表（Field Extractor行）を`FieldExtractionResult`に更新 |

## 関連ADR
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0035](0035-layout-detector-owns-pdf-content-access.md) — Layout Detector Owns PDF Content Access。`extractors/`が`layouts/`に依存しないという制約の先例。
- [ADR-0037](0037-layout-detector-produces-layout-artifact.md) — Layout Detector Produces Layout Artifact。「集約結果を返し、個別要素は呼び出し元が後続Stageへ渡す」という受け渡しパターンの先例（`SectionParseResult.sections` → `SectionParser`と同型）。

（本ADRはADR-0032/ADR-0035/ADR-0037のいずれの核心決定も変更しないため、Supersededにはしない。）
