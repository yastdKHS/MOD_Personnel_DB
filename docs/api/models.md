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
    layout_id: LayoutId
    section_index: int
    section_label: str | None
    page_range: tuple[int, int]
    section_text: str
```

- **属性**: [`docs/database/schema.md`](../database/schema.md#3-personnel_sections)の`personnel_sections`列に対応（`parser_version_id`は永続化時に`CandidateRepository.add_section`の呼び出し文脈から付与されるため、モデル自体には持たせない——[`pipeline.md`](pipeline.md)の`PipelineContext`が保持する）。
- **不変条件**: `section_index >= 0`。`page_range`は`(start, end)`で`start <= end`。
- **未確定事項（[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)）**: `page_range`が参照するページ範囲の妥当性検証（旧設計では「`Document.pages`の範囲内」）は、Version 2.0で`Document`がページ情報を保持しなくなったことに伴い**未確定**である。Section Parser設計時に、`page_range`の妥当性を検証する対象（`ExtractedDocument`等、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md#pageの扱い)参照）を別ADRで確定する。Section Parser実装着手前に解決必須。
- **Validation Rule**: `section_text`は空文字列を許容しない（空セクションはSection Parserが生成すべきでない、上位の契約違反として扱う）。

## `RawRecord`

Field Extractorの出力。正規化前のフィールド。

```python
@dataclass(frozen=True, slots=True)
class RawRecord:
    section_ref: PersonnelSectionId | None
    record_index: int
    raw_fields: Mapping[str, str]
    extracted_at: datetime
```

- **属性**: `section_ref`はパイプライン実行中（未永続化）は`None`、永続化後は`PersonnelSectionId`を持つ（[`pipeline.md`](pipeline.md)のステージ間受け渡しでは`None`のまま扱われ、`CandidateRepository.add_raw`呼び出し時に紐付けが確定する)。`raw_fields`はフィールド名（`name`/`rank`/`organization`/`position`/`effective_date`等）から生テキストへの写像。
- **不変条件**: `raw_fields`は空でない。`record_index >= 0`。
- **Validation Rule**: `raw_fields`のキー集合は、対応する`Layout`の`manifest.yaml`が定義するフィールド集合の部分集合でなければならない（未知フィールドの混入を防ぐ。検証自体はField Extractorの責務、[`architecture-contract.md`](../architecture/architecture-contract.md)）。

## `NormalizedRecord`

Normalizerの出力。

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
- **不変条件**: `normalized_fields`のキー集合は`raw_record_ref.raw_fields`のキー集合と一致する（Normalizerはフィールドを追加・削除しない、値のみを変換する）。`normalized_at >= raw_record_ref.extracted_at`。
- **Validation Rule**: `NormalizedValue.value`は空文字列を許容しない（正規化の結果、値が失われてはならない。正規化できなかった場合は`NormalizedRecord`を生成せず、上位でLearning Dataset記録に倒す、[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md)）。

## `ValidationResult`

Validatorの出力。**レコードの値は含まない**（Validatorは修正しないため、[`architecture-contract.md`](../architecture/architecture-contract.md)）。

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

- **属性**: `violations`は`knowledge/validation/`（[`docs/knowledge/schema.md`](../knowledge/schema.md#validation)）の`ValidationEntry`群との照合結果。
- **不変条件**: `status == "failed"` である場合、かつその場合に限り、`violations`に`severity == "error"`のものが1件以上存在する（`status`は`violations`から導出可能な冗長情報だが、明示的に持たせることでクエリ・シリアライズを簡潔にする）。
- **Validation Rule**: `confidence.score`は`0.0`〜`1.0`（[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)のバンド定義と整合）。

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

Layout Detectorの戻り値（[`interfaces.md`](interfaces.md)参照）。設計フェーズ当初（`layout: Layout` / `confidence: Confidence`の2属性、Superseded）から、Task5の実装指示に基づき拡張された。

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
