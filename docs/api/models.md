# Models（ドメインモデル）

> **本ドキュメントに実装はない。** すべて`@dataclass(frozen=True, slots=True)`の**属性宣言のみ**を示す。バリデーションロジックの中身（`__post_init__`等）は将来の実装タスクで書く。ここでは「何を検証すべきか（Validation Rule）」「常に成り立つべき性質（不変条件）」を仕様として固定する。
>
> 各モデルは可能な限り[`docs/database/schema.md`](../database/schema.md)のテーブル定義と対応させるが、DBの永続化表現（`TEXT`によるISO8601日時等）ではなく、Pythonの型（`date`, `datetime`, `Enum`）を用いる。DB表現との変換は`repositories/sqlite/`の実装詳細であり、モデル自体はDB非依存である。

## 対象モデル（13、要求通り）

`Document`, `PersonnelSection`, `RawRecord`, `NormalizedRecord`, `ValidationResult`, `ReviewItem`, `KnowledgeItem`, `LearningRecord`, `ExportRecord`, `Job`, `ParserVersion`, `Layout`, `FeatureVector`

これに加え、上記13モデルの型シグネチャ（[`interfaces.md`](interfaces.md), [`repositories.md`](repositories.md)）を成立させるために必要な**補助的な値オブジェクト**（ID型、集約型）を末尾にまとめる。13モデルの設計を主として読み、補助型は参照用として扱うこと。

---

## `Document`

Document Analyzerの出力。**Version 2.0（[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)）**: Pipelineを流れる「Document Identity」——PDFメタデータ・健全性・基本統計の束であり、ページ単位の抽出済みテキストは保持しない。文字列抽出はDocument Analyzerの責務外であり、後続Stageの設計確定を待つ（[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)のMigration Plan参照）。

> **Version 1設計（Superseded）との違い**: 設計フェーズ当初（Task 8）は`Document`が`pages: tuple[Page, ...]`（`Page.text`にページ単位の抽出済みテキストを保持）を持つ設計だった。Phase2 Task4着手前のArchitecture Synchronization（Task 3.1）で、Document Analyzerの実装指示（PDF解析・文字抽出を行わない）と非互換であることが判明し、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)により現行のVersion 2.0設計に置き換えられた。旧`Page`型・旧`Document`の構造は同ADRの「Superseded Design」節を参照（削除せず参照として保持）。

```python
from enum import StrEnum


class DocumentWarning(StrEnum):
    ENCRYPTED = "encrypted"
    IMAGE_ONLY = "image_only"
    BROKEN_PDF = "broken_pdf"
    UNSUPPORTED_VERSION = "unsupported_version"
    LARGE_PDF = "large_pdf"
    UNKNOWN_ENCODING = "unknown_encoding"


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    filename: str
    sha256: str
    file_size: int
    created_at: datetime | None
    modified_at: datetime | None
    pdf_version: str
    encrypted: bool


@dataclass(frozen=True, slots=True)
class DocumentStatistics:
    page_count: int
    text_length: int | None
    image_count: int
    rotation_count: int
    analysis_time_ms: float


@dataclass(frozen=True, slots=True)
class DocumentAnalysisResult:
    metadata: DocumentMetadata
    statistics: DocumentStatistics
    warnings: tuple[DocumentWarning, ...]
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class Document:
    id: DocumentId
    source_pdf_id: PdfId
    file_path: str
    analysis: DocumentAnalysisResult
    analyzed_at: datetime
    analyzer_version: str
```

- **属性**: `id`（本解析実行を識別する[`DocumentId`](#id型)、同一`PdfRecord`への再解析を区別するための識別子。[ADR-0023](../adr/0023-parser-versioning-policy.md)）、`source_pdf_id`（由来`PdfRecord`への参照、[ADR-0006](../adr/0006-pipeline-provenance.md)の来歴要件）、`file_path`（由来PDFファイルの絶対パス。Document Analyzerが検証済みの`PdfRecord.file_path`を複写する。Layout DetectorがRepositoryを経由せずにPDF本文へアクセスするための参照、[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md)で追加）、`analysis`（[`DocumentAnalysisResult`](#documentanalysisresultversion-20adr-0032)）、`analyzed_at`、`analyzer_version`（解析を行ったDocument Analyzer実装のバージョン、来歴追跡用）。
- **不変条件**: `Document`はfrozenであり、生成後に内容を変更しない。`DocumentMetadata.sha256`は64桁の16進文字列。`DocumentMetadata.file_size >= 0`。`DocumentStatistics.page_count >= 0`、`image_count >= 0`、`rotation_count >= 0`、`analysis_time_ms >= 0`。`DocumentAnalysisResult.confidence.score`は`[0.0, 1.0]`（[`Confidence`](#confidence)と共通）。
- **Validation Rule**: `DocumentMetadata.encrypted == True`の場合、`DocumentAnalysisResult.warnings`に`DocumentWarning.ENCRYPTED`を含む。
- **`DocumentStatistics.text_length`に関する注記**: Document Analyzerは文字列（抽出結果）を生成・保持・返却しない（[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)）。`text_length`は、`DocumentWarning.IMAGE_ONLY`等の警告判定に必要な**軽量プローブによる文字数の計測値**（スカラー）のみを表し、抽出したテキスト本文そのものを保持しない。プローブが実行できない場合（例: 暗号化PDFで内容確認不可）は`None`。
- **フィールド配置（[ADR-0033](../adr/0033-document-analyzer-output-field-composition.md)）**: `file_size`はファイルそのものの静的属性として`DocumentMetadata`に、`analysis_time_ms`は解析実行1回分の計測値として`DocumentStatistics`に、それぞれ配置する。

### `DocumentAnalysisResult`（Version 2.0、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)・[ADR-0033](../adr/0033-document-analyzer-output-field-composition.md)）

`Document.analysis`として保持される。上記コードブロックを参照。`metadata` / `statistics` / `warnings` / `confidence`の4属性のみを持ち、PDFの内容（文字列）は一切含まない。

### `Page`・旧`Document`構造（Superseded）

Version 1で定義されていた`Page`（`index` / `text` / `width` / `height`）は廃止された。文字列保持責務の移管先（`ExtractedDocument` / `ExtractedPage`、仮称）は本ドキュメント時点では未確定である。詳細・経緯は[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md#pageの扱い)を参照。

## `PersonnelSection`

Section Parserの出力。`candidate_records`table:`personnel_sections`に対応。

```python
@dataclass(frozen=True, slots=True)
class PersonnelSection:
    document_ref: PdfId
    layout_id: str
    section_index: int
    section_label: str | None
    page_range: tuple[int, int]
    section_text: str
```

- **属性**: [`docs/database/schema.md`](../database/schema.md#3-personnel_sections)の`personnel_sections`列に対応（`parser_version_id`は永続化時に`CandidateRepository.add_section`の呼び出し文脈から付与されるため、モデル自体には持たせない——[`pipeline.md`](pipeline.md)の`PipelineContext`が保持する）。`layout_id`は`Layout`（`layouts`テーブル）のDB主キー`LayoutId`ではなく、`LayoutDetectionResult.layout_id`と同じ値域の`era_id`（`str`）である（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）。Section ParserはRepositoryにアクセスしないため、DB主キーへの解決は永続化時に`SqliteCandidateRepository.add_section`が担う。
- **不変条件**: `section_index >= 0`。`page_range`は`(start, end)`で`start <= end`。
- **`page_range`の妥当性検証対象（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)で確定）**: `page_range`が参照するページ範囲は、Section Parserの入力`LayoutArtifact.pages`（[`#layoutartifact`](#layoutartifact)）のページ番号体系に対応する。Version 1設計時点の「`Document.pages`の範囲内」という検証対象は、Version 2.0で`Document`がページ情報を保持しなくなったことに伴い[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)時点では未確定だったが、`LayoutArtifact`の新設（ADR-0037）により確定した。
- **Validation Rule**: `section_text`は空文字列を許容しない（空セクションはSection Parserが生成すべきでない、上位の契約違反として扱う）。

### `SectionParseResult`（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）

`SectionParser.run()`の戻り値。

```python
@dataclass(frozen=True, slots=True)
class SectionEvidence:
    header_line: str | None
    footer_line: str | None
    body_line_count: int
    page_range: tuple[int, int]


@dataclass(frozen=True, slots=True)
class SectionCandidate:
    section_index: int
    score: float
    evidence: SectionEvidence


@dataclass(frozen=True, slots=True)
class SectionParseResult:
    sections: tuple[PersonnelSection, ...]
    candidates: tuple[SectionCandidate, ...]
    confidence: Confidence
```

- **属性**: `sections`は確定した`PersonnelSection`（`candidates`のうちConfidence閾値以上、かつ`LayoutArtifact.detection.layout_id`が既知の場合のみ生成される）。`candidates`は評価した全Section候補（`LayoutArtifact.pages`の各ページに対応、Confidence閾値未満のものを含む）。`confidence`は`candidates`のスコア平均（候補が0件の場合は`score=0.0`）。
- **不変条件**: `SectionCandidate.score`は`[0.0, 1.0]`。`SectionEvidence.body_line_count >= 0`。`SectionEvidence.page_range`は`(start, end)`で`start <= end`。
- **未一致・低Confidenceの扱い**: `LayoutArtifact.detection.layout_id`が`None`（未知様式）の場合、`SectionParser.run()`は例外を送出せず、`sections=()`（空）・`candidates`（評価は実施）・低い`confidence`を返す（[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md)以来の「内容品質の問題は例外ではなくデータとして表現する」方針を踏襲、`SectionParserError`との使い分けは[`interfaces.md`](interfaces.md#sectionparser)参照）。
- **Section境界判定の粒度（Task6時点の実装判断）**: Section境界はページ境界を単位とする（1ページ=1Section候補）。複数ページにまたがるSectionの結合判定は、様式ごとの構造情報を要する可能性が高く、`LayoutArtifact`が持つ情報のみでは信頼できる判定ができないため、将来の拡張点として保留する。

## `RawRecord`

Field Extractorの出力。正規化前のフィールド。

```python
@dataclass(frozen=True, slots=True)
class RawRecord:
    section_ref: PersonnelSectionId | None
    layout_id: str  # era_id（ADR-0039）
    record_index: int
    raw_fields: Mapping[str, str]
    extracted_at: datetime
```

- **属性**: `section_ref`はパイプライン実行中（未永続化）は`None`、永続化後は`PersonnelSectionId`を持つ（[`pipeline.md`](pipeline.md)のステージ間受け渡しでは`None`のまま扱われ、`CandidateRepository.add_raw`呼び出し時に紐付けが確定する)。`layout_id`はField Extractorが入力`PersonnelSection.layout_id`をそのままコピーする`era_id`（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)の`PersonnelSection.layout_id: str`と同じ意味論、[ADR-0039](../adr/0039-normalizer-field-mapping-via-extended-layout-knowledge.md)）。`raw_fields`は列位置ベースの汎用フィールド名（`column_1`, `column_2`, ...、[ADR-0038](../adr/0038-field-extractor-produces-field-extraction-result.md)）から生テキストへの写像。
- **不変条件**: `raw_fields`は空でない。`record_index >= 0`。`layout_id`は空文字列を許容しない。
- **Validation Rule（[ADR-0038](../adr/0038-field-extractor-produces-field-extraction-result.md)で確定）**: `raw_fields`のキー集合は、Field Extractorが`PersonnelSection.section_text`の該当行から構造的に認識した列の集合と一致する（`column_1`, `column_2`, ...の汎用名。検証自体はField Extractorの責務、[`architecture-contract.md`](../architecture/architecture-contract.md)）。
- **列位置→意味的フィールド名マッピング（[ADR-0039](../adr/0039-normalizer-field-mapping-via-extended-layout-knowledge.md)/[ADR-0040](../adr/0040-normalizer-produces-normalization-result.md)で確定）**: `column_N`から意味的フィールド名（`name`/`rank`/`organization`等）への対応付けは、Normalizerが`layout_id`をキーに`knowledge/layout`カテゴリ（[`docs/knowledge/schema.md`](../knowledge/schema.md#layout)）のマッピングエントリを`KnowledgeSnapshot`経由で参照して行う。`KnowledgeItem`の`category="layout"`, `item_key=f"{layout_id}.{raw_field_name}"`（例: `"format_a.column_1"`）, `canonical_value`が意味的フィールド名という規約を用いる（ADR-0040）。`RawRecord`自体は対応付け結果を持たない（正規化前の生値のみを保持するという既存方針を維持）。

### `FieldExtractionResult`（[ADR-0038](../adr/0038-field-extractor-produces-field-extraction-result.md)）

`FieldExtractor.run()`の戻り値。

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

- **属性**: `records`は確定した`RawRecord`（`candidates`のうちConfidence閾値以上、かつ`fields`が空でないもの）。`candidates`は評価した全行（`PersonnelSection.section_text`の各行に対応、閾値未満のものを含む）。`confidence`は`candidates`のスコア平均（候補が0件の場合は`score=0.0`）。`RawField`は1つの列から抽出された生の値（`name`は列位置ベースの汎用名`column_N`、`value`はPDFに書かれていた値そのまま）。
- **不変条件**: `ExtractionCandidate.score`は`[0.0, 1.0]`。`ExtractionEvidence.column_count >= 0`。`RawField.name`は空文字列を許容しない。
- **Section Parserとの構造対応**: `LayoutArtifact`→`LayoutDetectionResult`（ADR-0037）、`SectionParseResult`→`PersonnelSection`（ADR-0037）と同型の「集約結果が個別要素を内包し、後続段階へは個別要素が渡される」パターンに従う。`Normalizer.run(context, record: RawRecord)`（`KnowledgeSnapshot`はコンストラクタ注入、ADR-0040）は`FieldExtractionResult.records`の要素を1件ずつ受け取る（呼び出し元`pipeline/`のJobRunnerが担う）。

## `NormalizedRecord`

Normalizerの出力。**Phase1設計以来無変更**（[ADR-0040](../adr/0040-normalizer-produces-normalization-result.md)がTask8での再定義要求を検討し、`GoldRepository`・公開JSON輸出フォーマット（[ADR-0016](../adr/0016-public-json-format.md)）・既存Repositoryへの影響を避けるため維持を決定）。

```python
@dataclass(frozen=True, slots=True)
class NormalizedValue:
    value: str
    raw: str | None

@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    raw_record_ref: RawRecord
    normalized_fields: Mapping[str, NormalizedValue]
    normalization_applied: tuple[KnowledgeItemId, ...]
    normalized_at: datetime
```

- **属性**: `normalization_applied`は正規化に使った`KnowledgeItem`のID列（監査用、[ADR-0005](../adr/0005-knowledge-base-normalization.md)）。`NormalizedValue`は[`docs/database/json_schema.md`](../database/json_schema.md#normalizedvalue)の`value`/`raw`構造と対応する。
- **不変条件**: `normalized_fields`のキー集合は`raw_record_ref.raw_fields`のキー集合と一致する（Normalizerはフィールドを追加・削除しない、値のみを変換する）。`normalized_at >= raw_record_ref.extracted_at`。`normalized_fields`のキーは`raw_record_ref.raw_fields`と同じ列位置ベースの汎用名（`column_N`）であり、意味的フィールド名へのリネームは行わない（ADR-0040。意味的フィールド名対応の内部的な適用結果は`NormalizationCandidate.fields`の`NormalizedField.name`ではなく、どの`KnowledgeItem`カテゴリを検索するかの判定にのみ使う）。
- **Validation Rule**: `NormalizedValue.value`は空文字列を許容しない（正規化の結果、値が失われてはならない。正規化できなかった場合は`NormalizedRecord`を生成せず、上位でLearning Dataset記録に倒す、[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md)）。

### `NormalizationResult`（[ADR-0040](../adr/0040-normalizer-produces-normalization-result.md)）

`Normalizer.run()`の戻り値。`FieldExtractionResult`（ADR-0038）と同型の集約結果パターン。

```python
@dataclass(frozen=True, slots=True)
class NormalizedField:
    name: str               # RawField.nameと同じキー（column_N等）
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
    records: tuple[NormalizedRecord, ...]
    candidates: tuple[NormalizationCandidate, ...]
    confidence: Confidence
```

- **属性**: `records`はConfidence閾値以上の候補から構築された`NormalizedRecord`（0件または1件。`Normalizer.run()`は`RawRecord`を1件ずつ受け取るため、`candidates`も常に1件）。`NormalizedField.name`は`RawField.name`と同じキーを維持し、意味的フィールド名へのリネームは行わない（`NormalizedRecord.normalized_fields`の不変条件を破壊しないため）。`normalization_method`は`"typography"`（`knowledge/typography`のみ適用）・`"alias"`/`"organization"`/`"position"`/`"rank"`（対応するカテゴリのKnowledge Lookupが一致）・`"identity"`（いずれも一致せず未加工）のいずれか。
- **不変条件**: `NormalizationCandidate.score`は`[0.0, 1.0]`。`NormalizedField.name`/`value`/`normalization_method`は空文字列を許容しない。`NormalizationEvidence.layout_id`/`knowledge_version`は空文字列を許容しない。
- **Knowledge検索規約（ADR-0040）**: `KnowledgeItem`の既存の汎用形状（`item_key`/`canonical_value`）をそのまま用いる。`category="layout"`・`item_key=f"{layout_id}.{raw_field_name}"`で意味的フィールド名を解決し、対応する`category`（`alias`/`organization`/`position`/`rank`）・`item_key=`typography正規化後の値で正規化後の値を検索する。`effective_from`/`effective_to`は`KnowledgeSnapshot.as_of`を基準に絞り込む。

## `ValidationResult`（[ADR-0043](../adr/0043-validator-produces-validation-result-with-rule-engine.md)）

Validatorの出力。**レコードの値は含まない**（Validatorは修正しないため、[`architecture-contract.md`](../architecture/architecture-contract.md)）。`FieldExtractionResult`（ADR-0038）・`NormalizationResult`（ADR-0040）と同型の集約結果パターン。

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

- **属性**: `Validator.run()`は`NormalizedRecord`を1件ずつ受け取るため、`candidates`は常に1件（Validatorは常に検証結果を返し、Field Extractor/Normalizerのような「Confidence閾値未満のため出力しない」という状態はない）。`status`は`candidates[0].errors`が空かどうかから導出する。`ValidationEvidence`の`record_index`/`layout_id`は`NormalizedRecord.raw_record_ref`から取得できる値であり、`subject_ref`（旧設計、[ADR-0041](../adr/0041-validator-constructor-injects-validation-rule-set.md)時点では維持していた）は保持しない（呼び出し元が検証対象の`NormalizedRecord`を別途保持しているため冗長、[ADR-0043](../adr/0043-validator-produces-validation-result-with-rule-engine.md)）。
- **不変条件**: `status == "failed"` である場合、かつその場合に限り、`candidates[0].errors`が1件以上存在する。`ValidationCandidate.score`は`[0.0, 1.0]`。`ValidationEvidence.record_index >= 0`、`rules_evaluated >= 0`。
- **Validation Rule**: `confidence.score`は`0.0`〜`1.0`（[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)のバンド定義と整合）。
- **Knowledge検索規約（`category="validation"`、ADR-0043）**: `KnowledgeItem`の既存の汎用形状をそのまま用いる。`item_key`が対象フィールド名（意味的フィールド名）、`canonical_value`が許容される値の1つを表す。同一`item_key`を持つ複数の`KnowledgeItem`が1フィールドの許容値集合を構成する。該当`item_key`のエントリが存在しないフィールドは「制約なし」として扱う。

### `RuleEngine`（[ADR-0043](../adr/0043-validator-produces-validation-result-with-rule-engine.md)）

Validatorがコンストラクタで生成・保持する、フィールド単位のルール評価を担う具象クラス（差し替え可能、デフォルト実装を内蔵）。

```python
class RuleEngine:
    def evaluate_field(
        self, field_name: str, value: str, rules: ValidationRuleSet
    ) -> ValidationError | None: ...
```

`Validator`は`record.raw_record_ref.layout_id`と`KnowledgeSnapshot`の`category="layout"`エントリから各フィールドの意味的名称を解決し（Normalizerと同じ規約だが、`validators/`は`normalizers/`に依存しないため解決ロジックは独立実装する）、解決できたフィールドについて`RuleEngine.evaluate_field()`を呼び出す。解決できなかったフィールドは`ValidationWarning`（`rule_id="layout.unmapped_field"`）とする。

## `ReviewItem`

`review_changes`に対応。

```python
@dataclass(frozen=True, slots=True)
class ReviewItem:
    session_id: ReviewSessionId
    target_table: Literal["candidate_records", "gold_records"]
    target_id: CandidateId | GoldRecordId
    field_name: str
    old_value: str | None
    new_value: str
    change_reason: str | None
    reviewer: str
    created_at: datetime
```

- **属性**: [`docs/database/schema.md`](../database/schema.md#7-review_changes)の`review_changes`列に対応。
- **不変条件**: `new_value != old_value`（無意味な変更を記録しない）。`reviewer`は空文字列を許容しない。
- **Validation Rule**: `target_table`が`"candidate_records"`のとき`target_id`は`CandidateId`、`"gold_records"`のとき`GoldRecordId`でなければならない（多態的参照の整合性、[`docs/database/schema.md`](../database/schema.md#7-review_changes)の設計メモ参照）。

## `KnowledgeItem`

`knowledge_items`／`knowledge/`配下YAMLエントリに対応。

```python
@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    id: KnowledgeItemId
    category: Literal[
        "organization", "position", "rank", "alias",
        "historical", "typography", "layout", "validation",
    ]
    source_file: str
    item_key: str
    canonical_value: str
    effective_from: date | None
    effective_to: date | None
    provenance_source: str
    version: int
```

- **属性**: [`docs/knowledge/schema.md`](../knowledge/schema.md)の8カテゴリ共通部分（`Provenance`/`VersionInfo`）を平坦化したもの。カテゴリ固有の詳細フィールド（`rank_order`等）は、`canonical_value`に構造化データ（JSON文字列相当）を持たせず、`source_file`を参照して元のYAMLから取得する設計とする（`docs/database/schema.md`の`knowledge_items`テーブルの設計メモ「`item_key`/`canonical_value`の解釈はカテゴリごとに異なる」と整合）。
- **不変条件**: `category`は8値のいずれか。`effective_to`が設定されている場合、`effective_to > effective_from`。
- **Validation Rule**: `source_file`は`knowledge/`配下の相対パスであること。

## `LearningRecord`

`learning_dataset`（[`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md)）に対応。

```python
@dataclass(frozen=True, slots=True)
class LearningRecord:
    id: LearningRecordId | None
    source_candidate_id: CandidateId | None
    source_review_item_id: ReviewItemId | None
    pipeline_stage: PipelineStageName
    error_category: ErrorCategory
    field_name: str | None
    wrong_value: str
    correct_value: str | None
    correction_summary: str | None
    reviewer_comment: str | None
    parser_version_id: ParserVersionId | None
    layout_id: LayoutId | None
    confidence: Confidence | None
    status: LearningStatus
    reflected_in_knowledge_item_id: KnowledgeItemId | None
    reflected_in_layout_id: LayoutId | None
    git_commit_hash: str | None
    pull_request_url: str | None
    regression_status: Literal["not_run", "passed", "failed"]
    regression_run_at: datetime | None
    regression_details: str | None
    improvement_candidate: str | None
    created_at: datetime
    resolved_at: datetime | None
```

- **属性**: [`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md#保持するフィールド)の全項目に対応。
- **不変条件**: `status`は`open → in_review → reflected → verified`または`wontfix`の遷移のみ許容する（逆行・スキップ禁止、[`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md#ライフサイクル)）。`status != "open"`のとき`correct_value`は`None`不可。`status == "verified"`のとき`regression_status == "passed"`。
- **Validation Rule**: `layout_id`（発生コンテキスト）と`reflected_in_layout_id`（反映結果）はそれぞれ独立に検証し、値が一致していなくてもエラーとしない（[`docs/database/schema.md`](../database/schema.md#9-learning_dataset)の設計メモ）。

## `ExportRecord`

`exports`に対応。

```python
@dataclass(frozen=True, slots=True)
class ExportRecord:
    id: ExportId | None
    format: Literal["csv", "parquet", "json"]
    destination: str
    as_of: datetime
    record_count: int
    checksum: str
    status: Literal["completed", "failed"]
    created_at: datetime
```

- **属性**: [`docs/database/schema.md`](../database/schema.md#11-exports)に対応。
- **不変条件**: `record_count >= 0`。`status == "completed"`のとき`checksum`は空文字列不可。
- **Validation Rule**: `format == "json"`のときは[`docs/database/json_schema.md`](../database/json_schema.md)のスキーマに、生成物が事前に検証されていることを前提とする（本モデル自体はJSON本文を保持しない、`destination`のみを持つ軽量なメタデータ）。

## `Job`

`jobs`（`parser_versions`は下記`ParserVersion`参照）に対応。

```python
@dataclass(frozen=True, slots=True)
class Job:
    id: JobId | None
    job_type: Literal["fetch", "core_pipeline", "export", "backfill", "knowledge_reload"]
    pdf_id: PdfId | None
    parser_version_id: ParserVersionId | None
    status: Literal["running", "succeeded", "failed"]
    started_at: datetime
    finished_at: datetime | None
    processed_count: int
    failed_count: int
    error_summary: str | None
```

- **属性**: [`docs/database/schema.md`](../database/schema.md#12-jobs)に対応。
- **不変条件**: `status == "running"`のとき`finished_at`は`None`。`finished_at`が設定されている場合`finished_at >= started_at`。`processed_count >= 0`, `failed_count >= 0`。
- **Validation Rule**: `job_type == "backfill"`のとき`error_summary`に対象範囲（期間・様式等）の記述を含むことを推奨する（[ADR-0024](../adr/0024-knowledge-versioning-and-backfill.md)）——強制はしないが、運用上の慣例として`Job`生成側（`services/`）が満たすべき指針。

## `ParserVersion`

`parser_versions`に対応。

```python
@dataclass(frozen=True, slots=True)
class ParserVersion:
    id: ParserVersionId | None
    code_version: str
    knowledge_snapshot_checksum: str
    released_at: datetime
    notes: str | None
```

- **属性**: [`docs/database/schema.md`](../database/schema.md#10-parser_versions)に対応。
- **不変条件**: 生成後は不変（[ADR-0023](../adr/0023-parser-versioning-policy.md)、リリースタグは削除・付け替え禁止）。
- **Validation Rule**: `code_version`はSemVerのGitタグ形式（例: `v1.3.0`）に一致すること（[ADR-0023](../adr/0023-parser-versioning-policy.md)のパターン `^v\d+\.\d+\.\d+$`）。

## `Layout`

`layouts`に対応。

```python
@dataclass(frozen=True, slots=True)
class Layout:
    id: LayoutId | None
    era_id: str
    version: int
    manifest_path: str
    manifest_checksum: str
    valid_from: date
    valid_to: date | None
    status: Literal["active", "deprecated"]
```

- **属性**: [`docs/database/schema.md`](../database/schema.md#2-layouts)に対応。
- **不変条件**: `valid_to`が設定されている場合`valid_to > valid_from`。`(era_id, version)`の組は一意。
- **Validation Rule**: `manifest_path`は`layouts/<era_id>/manifest.yaml`の形式であること。

## `FeatureVector`

FeatureStoreの出力。**V2.0時点では永続化しない**（[`package-design.md`](package-design.md)の`features/`節参照）ため、対応するDBテーブルは持たない。

```python
@dataclass(frozen=True, slots=True)
class FeatureVector:
    subject_ref: CandidateId
    features: Mapping[str, float | str | bool]
    feature_set_version: str
    computed_at: datetime
```

- **属性**: `features`は特徴量名から値への写像（例: `"ocr_confidence": 0.87`, `"layout_match_score": 0.95`, `"org_error_rate_90d": 0.02`）。`feature_set_version`は特徴量の計算ロジック自体のバージョン（`ParserVersion`とは独立、計算式が変われば値が変わるため）。
- **不変条件**: `features`は空でない。`feature_set_version`は空文字列不可。
- **Validation Rule**: `features`の値のうち`float`型のものは、特徴量ごとに定義された値域（例: `*_confidence`系は`0.0`〜`1.0`）を満たす——具体的な値域定義は実装時に`features/`パッケージ内で個別に管理する。

---

## 補助的な値オブジェクト

13モデルの型シグネチャを成立させるために必要だが、Task 4が明示的に列挙した13には含まれない型。それぞれ、どのモデル・インターフェースがこれを必要とするかを併記する。

### ID型

すべて`typing.NewType`による不透明なラッパー（[`repositories.md`](repositories.md#sqlite非依存を実現する設計原則)の原則1）。

```python
from typing import NewType

CandidateId = NewType("CandidateId", int)
PersonnelSectionId = NewType("PersonnelSectionId", int)
GoldRecordId = NewType("GoldRecordId", int)
KnowledgeItemId = NewType("KnowledgeItemId", int)
LearningRecordId = NewType("LearningRecordId", int)
PdfId = NewType("PdfId", int)
DocumentId = NewType("DocumentId", int)
JobId = NewType("JobId", int)
ParserVersionId = NewType("ParserVersionId", int)
LayoutId = NewType("LayoutId", int)
ExportId = NewType("ExportId", int)
ReviewSessionId = NewType("ReviewSessionId", int)
ReviewItemId = NewType("ReviewItemId", int)
```

- `DocumentId`は[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)で`Document`（Document Analyzerの出力）向けに追加された。同一`PdfRecord`（`PdfId`）に対する複数回の解析実行（再解析）を区別する。

### `Confidence`

`ValidationResult`と`LearningRecord`が共有する信頼度の値オブジェクト（[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)と同一定義）。

```python
@dataclass(frozen=True, slots=True)
class Confidence:
    score: float
    band: ConfidenceBand
```

不変条件: `0.0 <= score <= 1.0`。`band`の定義は[`ConfidenceBand`](#confidenceband)を参照。

### `PdfRecord`

`PDFRepository`が扱う`pdfs`テーブル行。**`Document`（解析済み内部表現）とは別物**であることに注意（[`package-design.md`](package-design.md#命名衝突に関する注意)と同種の区別）。Task 4が要求する13モデルには含まれないが、`PDFRepository`（Task 3）の契約を成立させるために必須のため追加した。

```python
@dataclass(frozen=True, slots=True)
class PdfRecord:
    id: PdfId | None
    content_hash: str
    source_url: str
    published_date: date
    fetched_at: datetime
    file_path: str
    file_size_bytes: int
    status: Literal["fetched", "analyzed", "parsed", "validated", "failed"]
```

### `KnowledgeSnapshot`

Normalizerに注入される、ある時点の知識ベース全体のスナップショット（[`interfaces.md`](interfaces.md)のNormalizer参照）。

```python
@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    items: tuple[KnowledgeItem, ...]
    snapshot_checksum: str
    as_of: date
```

### `ValidationRuleSet`

Validatorに注入される、`category="validation"`の`KnowledgeItem`群の集合（[`interfaces.md`](interfaces.md)のValidator参照）。

```python
@dataclass(frozen=True, slots=True)
class ValidationRuleSet:
    rules: tuple[KnowledgeItem, ...]
    as_of: date
```

### `LayoutDetectionResult`（Version 2.0、[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md)）

様式判定結果（[`interfaces.md`](interfaces.md)参照）。設計フェーズ当初（`layout: Layout` / `confidence: Confidence`の2属性、Superseded）から、Task5の実装指示に基づき拡張された。**Layout Detectorの戻り値そのものではない**——ADR-0037により、`LayoutDetector.run()`は本型を`.detection`として内包する`LayoutArtifact`（[`#layoutartifact`](#layoutartifact)）を返す。

```python
from enum import StrEnum


class LayoutWarning(StrEnum):
    NO_MATCH = "no_match"
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_CANDIDATES = "ambiguous_candidates"


@dataclass(frozen=True, slots=True)
class LayoutMatch:
    """1つの判定ルールをEvidenceに対して評価した結果。"""

    rule_id: str
    matched: bool
    detail: str | None


@dataclass(frozen=True, slots=True)
class LayoutCandidate:
    """1つの`era_id`（LayoutDefinition）に対する評価結果。"""

    layout_id: str
    score: float
    matched_rules: tuple[LayoutMatch, ...]
    failed_rules: tuple[LayoutMatch, ...]


@dataclass(frozen=True, slots=True)
class LayoutConfidence:
    score: float
    band: ConfidenceBand


@dataclass(frozen=True, slots=True)
class PageStatistics:
    page_count: int
    average_char_count: float


@dataclass(frozen=True, slots=True)
class BoundingBoxStatistics:
    average_width: float
    average_height: float


@dataclass(frozen=True, slots=True)
class RotationStatistics:
    rotated_page_count: int
    dominant_rotation: int


@dataclass(frozen=True, slots=True)
class LayoutEvidence:
    """Layout Detectorが再読込したPDFから抽出した特徴量。"""

    font_statistics: tuple[str, ...]
    page_statistics: PageStatistics
    bbox_statistics: BoundingBoxStatistics
    rotation_statistics: RotationStatistics
    header_signature: str | None
    footer_signature: str | None
    line_statistics: float
    block_statistics: float


@dataclass(frozen=True, slots=True)
class LayoutDetectionResult:
    layout_id: str | None
    layout_version: int | None
    confidence: LayoutConfidence
    candidate_layouts: tuple[LayoutCandidate, ...]
    evidence: LayoutEvidence
    warnings: tuple[LayoutWarning, ...]
```

- **属性**: `layout_id` / `layout_version`は、最有力候補のConfidenceが閾値以上の場合にのみ値を持つ。閾値未満、または既知の`era_id`に一致しない場合は`None`（[`docs/review/queue.md`](../review/queue.md)の`layout_unknown`判定に対応）。`confidence`は最有力候補の`LayoutConfidence`（候補が0件の場合は`score=0.0`）。`candidate_layouts`は評価した全候補（スコア降順）。`evidence`は再読込したPDFから抽出した特徴量。`warnings`は`LayoutWarning`の集合。
- **`layout_id`の型**: `LayoutCandidate.layout_id`・`LayoutDetectionResult.layout_id`はいずれも`str`型で、`LayoutDefinition.era_id`と同じ値（`era_id`文字列）を表す。`Layout`（`layouts`テーブル）のDB主キーである`LayoutId`（`models/ids.py`の不透明な`int`）とは異なる。Layout Detectorは`LayoutDefinition`（`era_id`キー）のみを入力とし、`repositories/`に依存しない（[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md)）ため、`era_id`から`LayoutId`（DB主キー）への解決はLayout Detectorより後段の責務とする。
- **不変条件**: `layout_id is not None`のとき`layout_version is not None`（およびその逆）。`layout_id is None`の場合`warnings`に`LayoutWarning.NO_MATCH`または`LayoutWarning.LOW_CONFIDENCE`のいずれかを含む。`LayoutCandidate.score`・`LayoutConfidence.score`は`[0.0, 1.0]`。
- **`LayoutEvidence`の各フィールドの粒度**: `font_statistics`（検出された代表フォント名の集合）・`line_statistics`/`block_statistics`（1ページあたり平均行数/ブロック数）は、Task5の実装時点でLayout Detectorの判定精度に必要十分な粒度として選定した実装判断であり、将来Layout判定ルールの拡充に応じて型を精緻化してよい。

### `LayoutArtifact`（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）

`LayoutDetector.run()`の戻り値。Section ParserがPDF本文（テキスト）を得る唯一の経路であり（[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md)が確立した「Layout DetectorのみがPDF本文にアクセスできる」という保証の直接の帰結）、それより後段（Section Parser自身を含む）はPDFファイルを一切読み込まない。

```python
@dataclass(frozen=True, slots=True)
class LayoutArtifactPage:
    index: int
    text: str


@dataclass(frozen=True, slots=True)
class LayoutArtifact:
    source_pdf_id: PdfId
    detection: LayoutDetectionResult
    pages: tuple[LayoutArtifactPage, ...]
```

- **属性**: `detection`は[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md)が確定した`LayoutDetectionResult`（形状は無変更）をそのまま保持する。`docs/review/queue.md`の`layout_unknown`判定が参照する`confidence`は、アクセス経路が本型の`.detection.confidence`に変わる（値の意味・算出方法は無変更）。`pages`はLayout Detectorが再読込した各ページの生テキストを、ページ順（0始まりの連番）で保持する。
- **不変条件**: `pages`の`index`は`0`始まりの連続した整数列でなければならない（`LayoutArtifactPage.index`は`0`以上）。
- **Section Parserとの関係**: `PersonnelSection.page_range`が参照するページ範囲は、本型の`pages`のページ番号体系に対応する（[`#personnelsection`](#personnelsection)）。

### `LayoutDefinition`（[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md), [ADR-0036](../adr/0036-pyyaml-for-layout-definition.md)）

Layout判定ルールのみを保持する。[`docs/knowledge/schema.md`](../knowledge/schema.md)が定める`knowledge/`の8カテゴリには属さない（Knowledgeではない、[ADR-0003](../adr/0003-layout-definition-strategy.md)の`layouts/`外部データ定義に対応）。`layouts/<era_id>/manifest.yaml`（[`layouts/README.md`](../../layouts/README.md)）からYAMLとしてロード可能な構造とする。

```python
class LayoutRuleKind(StrEnum):
    HEADER_PATTERN = "header_pattern"
    FOOTER_PATTERN = "footer_pattern"
    MIN_PAGE_COUNT = "min_page_count"
    FONT_NAME_CONTAINS = "font_name_contains"


@dataclass(frozen=True, slots=True)
class LayoutRule:
    rule_id: str
    kind: LayoutRuleKind
    value: str
    weight: float


@dataclass(frozen=True, slots=True)
class LayoutDefinition:
    era_id: str
    version: int
    rules: tuple[LayoutRule, ...]
```

- **属性**: `era_id` / `version`は`Layout`（`layouts`テーブル、[`docs/database/schema.md`](../database/schema.md#2-layouts)）の`(era_id, version)`と対応する。`rules`は判定ルールの集合で、各ルールは`kind`（判定方法の種別）・`value`（パターン等のルール固有データ）・`weight`（スコアへの寄与度）を持つ。
- **不変条件**: `rules`は空でない。各`LayoutRule.weight`は`0.0`より大きい。`rule_id`は`LayoutDefinition`内で一意。
- **YAML表現例**（`layouts/<era_id>/manifest.yaml`、Task5時点の最小実装。フィールド抽出定義等の拡張は将来のスキーマ拡張として別途検討）:
  ```yaml
  era_id: "2019_format_a"
  version: 1
  rules:
    - rule_id: "header_a"
      kind: "header_pattern"
      value: "海上自衛隊人事発令"
      weight: 0.6
    - rule_id: "min_pages"
      kind: "min_page_count"
      value: "1"
      weight: 0.1
  ```

### `CandidateRecord`

`CandidateRepository.get`等が返す、永続化された候補レコードの読み取りビュー（`RawRecord`＋任意の`NormalizedRecord`＋検証状態の集約）。

```python
@dataclass(frozen=True, slots=True)
class CandidateRecord:
    id: CandidateId
    section_id: PersonnelSectionId
    raw: RawRecord
    normalized: NormalizedRecord | None
    validation_status: Literal["pending", "passed", "failed"]
```

### `GoldRecord`

`GoldRepository`が返す`gold_records`の読み取りビュー。

```python
@dataclass(frozen=True, slots=True)
class GoldRecord:
    id: GoldRecordId
    candidate_id: CandidateId
    person_key: str
    effective_date: date
    appointment_type: str
    fields: NormalizedRecord
    version: int
    is_current: bool
    superseded_by: GoldRecordId | None
```

### `LearningStatus`

```python
from enum import StrEnum


class LearningStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    REFLECTED = "reflected"
    VERIFIED = "verified"
    WONTFIX = "wontfix"
```

`Enum`利用方針の詳細（`enum.StrEnum`採用の経緯は[ADR-0030](../adr/0030-strenum-adoption.md)）は[`python-contract.md`](python-contract.md#enum利用方針)を参照。

### `PipelineStageName`

Learning Datasetの`pipeline_stage`列挙値。`docs/api/pipeline.md`が定義する`PipelineStage`（Stage実装が満たすProtocol）とは別の概念であるため、命名を分離している（Phase2 Task3で発見・是正）。

```python
class PipelineStageName(StrEnum):
    LAYOUT_DETECTOR = "layout_detector"
    SECTION_PARSER = "section_parser"
    FIELD_EXTRACTOR = "field_extractor"
    NORMALIZER = "normalizer"
    VALIDATOR = "validator"
```

### `ErrorCategory`

Learning Datasetの`error_category`列挙値。[ADR-0012](../adr/0012-error-handling-priority-order.md)の優先順位分類に対応する。

```python
class ErrorCategory(StrEnum):
    UNKNOWN_ALIAS = "unknown_alias"
    UNKNOWN_LAYOUT = "unknown_layout"
    KNOWLEDGE_GAP = "knowledge_gap"
    LAYOUT_GAP = "layout_gap"
    TRUE_EXCEPTION = "true_exception"
```

### `RegressionStatus`

Learning Datasetの`regression_status`列挙値。

```python
class RegressionStatus(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
```

### `ConfidenceBand`

`Confidence.band`の列挙値（[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)のバンド定義と対応）。

```python
class ConfidenceBand(StrEnum):
    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```
