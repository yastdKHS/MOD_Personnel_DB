# Models（ドメインモデル）

> **本ドキュメントに実装はない。** すべて`@dataclass(frozen=True, slots=True)`の**属性宣言のみ**を示す。バリデーションロジックの中身（`__post_init__`等）は将来の実装タスクで書く。ここでは「何を検証すべきか（Validation Rule）」「常に成り立つべき性質（不変条件）」を仕様として固定する。
>
> 各モデルは可能な限り[`docs/database/schema.md`](../database/schema.md)のテーブル定義と対応させるが、DBの永続化表現（`TEXT`によるISO8601日時等）ではなく、Pythonの型（`date`, `datetime`, `Enum`）を用いる。DB表現との変換は`repositories/sqlite/`の実装詳細であり、モデル自体はDB非依存である。

## 対象モデル（13、要求通り）

`Document`, `PersonnelSection`, `RawRecord`, `NormalizedRecord`, `ValidationResult`, `ReviewItem`, `KnowledgeItem`, `LearningRecord`, `ExportRecord`, `Job`, `ParserVersion`, `Layout`, `FeatureVector`

これに加え、上記13モデルの型シグネチャ（[`interfaces.md`](interfaces.md), [`repositories.md`](repositories.md)）を成立させるために必要な**補助的な値オブジェクト**（ID型、集約型）を末尾にまとめる。13モデルの設計を主として読み、補助型は参照用として扱うこと。

---

## `Document`

Document Analyzerの出力。PDFの内部構造表現。

```python
@dataclass(frozen=True, slots=True)
class Page:
    index: int
    text: str
    width: float
    height: float

@dataclass(frozen=True, slots=True)
class Document:
    source_pdf_id: PdfId
    pages: tuple[Page, ...]
    analyzed_at: datetime
```

- **属性**: `source_pdf_id`（由来PDFへの参照、[ADR-0006](../adr/0006-pipeline-provenance.md)の来歴要件）、`pages`（ページ単位のテキスト・寸法）、`analyzed_at`。
- **不変条件**: `pages`は空でない。各`Page.index`は`0`から`len(pages)-1`までの連番で重複がない。`Document`はfrozenであり、生成後に内容を変更しない。
- **Validation Rule**: `Page.text`は空文字列を許容する（白紙ページの可能性）が`None`は許容しない。`width`/`height`は正の値。

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
- **不変条件**: `section_index >= 0`。`page_range`は`(start, end)`で`start <= end`かつ`Document.pages`の範囲内。
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
JobId = NewType("JobId", int)
ParserVersionId = NewType("ParserVersionId", int)
LayoutId = NewType("LayoutId", int)
ExportId = NewType("ExportId", int)
ReviewSessionId = NewType("ReviewSessionId", int)
ReviewItemId = NewType("ReviewItemId", int)
```

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

### `LayoutDetectionResult`

Layout Detectorの戻り値（[`interfaces.md`](interfaces.md)参照）。

```python
@dataclass(frozen=True, slots=True)
class LayoutDetectionResult:
    layout: Layout
    confidence: Confidence
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
