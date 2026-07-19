# 0033. Document Analyzer出力型のフィールド構成を確定する

## ステータス
Accepted

## コンテキスト

[ADR-0032](0032-redefine-document-analyzer-responsibility.md)は、Document AnalyzerがVersion 2.0で返す`DocumentMetadata` / `DocumentStatistics` / `DocumentAnalysisResult`のフィールド構成を以下のとおり定義した。

```python
class DocumentMetadata:
    sha256: str
    filename: str
    created_at: datetime | None
    modified_at: datetime | None
    pdf_version: str
    encrypted: bool

class DocumentStatistics:
    page_count: int
    file_size: int
    text_length: int | None
    image_count: int
    rotation_count: int

class DocumentAnalysisResult:
    metadata: DocumentMetadata
    statistics: DocumentStatistics
    warnings: tuple[DocumentWarning, ...]
    analysis_time_ms: float
    confidence: Confidence
```

Phase2 Task4（Document Analyzer Implementation）の実装指示は、同じ3型について以下のフィールド構成を明示的に指定しており、ADR-0032と2点で異なる。

1. `file_size`が`DocumentStatistics`ではなく`DocumentMetadata`の保持対象として指定されている。
2. `analysis_time_ms`が`DocumentAnalysisResult`直下ではなく`DocumentStatistics`の保持対象として指定されている（`DocumentAnalysisResult`は`metadata` / `statistics` / `warnings` / `confidence`の4属性のみ）。

Task4-0（Design Verification）は「実装前に同期済みであることを確認し、差異があれば実装を開始しない」ことを求めており、上記2点の差異はこの基準に該当する。[ADR-0031](0031-pipeline-metrics-field-finalization.md)（`PipelineMetrics`のフィールド構成確定）と同種の、設計ドラフトと実装指示の間のフィールド配置レベルの調整である。

## 決定

- `DocumentMetadata` / `DocumentStatistics` / `DocumentAnalysisResult`のフィールド構成を、**Phase2 Task4の実装指示に合わせて確定**する。

```python
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
```

- `file_size`は「PDFファイルというモノに関する静的な事実」であり、`created_at`/`modified_at`/`pdf_version`と同じ性質（ファイルそのものの属性）を持つため`DocumentMetadata`に属する、と整理する。
- `analysis_time_ms`は「今回の解析実行1回分の計測値」であり、`page_count`/`text_length`等の統計値と同じ性質（解析結果の集計値）を持つため`DocumentStatistics`に属する、と整理する。
- `DocumentWarning`（`ENCRYPTED` / `BROKEN_PDF` / `IMAGE_ONLY` / `LARGE_PDF` / `UNKNOWN_ENCODING` / `UNSUPPORTED_VERSION`）・`Document`（Document Identity: `id` / `source_pdf_id` / `analysis` / `analyzed_at` / `analyzer_version`）の構成はADR-0032のまま変更しない。
- 本ADRは[ADR-0032](0032-redefine-document-analyzer-responsibility.md)の核心的決定（Document Analyzerの責務範囲、`Document`のDocument Identity化、文字列非生成）を一切変更しない。フィールドの所属先という実装詳細レベルの確定のみを行う。ADR-0032はSupersededにしない（決定内容は変わっていないため）。

## 検討した代替案

- **ADR-0032をSupersedeし、新ADRとして全体を書き直す**: 変更範囲がフィールド2個の所属先のみであり、ADR-0032の実質的な決定（責務範囲・Document Identity化）を何も変えていないため、Supersede（決定の置き換え）は過剰と判断した。[ADR-0031](0031-pipeline-metrics-field-finalization.md)が同種の状況で新規ADR（Supersedeなし）を選んだ前例に倣った。
- **ADR-0032を直接編集してフィールド構成を修正する**: [`docs/adr/README.md`](README.md#更新ルール)の更新ルールが禁じる「決定内容の実質的な書き換え」に該当するため採用しなかった。

## 結果（トレードオフ）

- `docs/api/models.md`の`Document`セクションのコード例を本ADRの構成に合わせて修正する（同一PR）。
- 既存コード（`src/mod_personnel_db/`）に本ADRが影響する実装は存在しない（Phase2 Task4のDocument Analyzer実装がこれから本ADRの構成に従って行われる）。
- 今後`DocumentMetadata`等のフィールドを追加・移動する場合も、本ADR・ADR-0032と同様に新規ADRを起票し、決定の変遷を追跡可能にする。

## 関連ADR
- [ADR-0032](0032-redefine-document-analyzer-responsibility.md) — Document Analyzer責務再定義。本ADRが対象とする3型の初出・核心決定。
- [ADR-0031](0031-pipeline-metrics-field-finalization.md) — PipelineMetricsのフィールド構成を確定する。同種の「設計ドラフトと実装指示の間のフィールド配置調整」を扱った先例。
