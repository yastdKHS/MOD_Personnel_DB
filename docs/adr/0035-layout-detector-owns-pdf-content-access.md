# 0035. Layout Detector Owns PDF Content Access

## ステータス
Accepted

## コンテキスト（Context）

[ADR-0032](0032-redefine-document-analyzer-responsibility.md)は、Document Analyzer（中核パイプライン段階1）の責務をPDFメタデータ・健全性・統計・警告の取得のみに限定し、`Document`を「Document Identity」（ページ・テキストを保持しない）として再定義した。同ADRは、ページ単位のテキスト抽出責務を「後続Stage」に委ねると述べたが、**どのStageが担うか、どうやってPDF本体にアクセスするかは未確定**のまま残していた（同ADRのMigration Plan Phase 3）。

Phase2 Task5（Layout Detector Implementation）は、この未確定事項を解決する。Layout Detectorを**PDF本文へアクセスできる唯一のPipeline Stage**として設計するという明確な方針が与えられた。

### 発見した実装上の欠落

Task5-0（Architecture Verification）でこの方針を実装可能性の観点から検証したところ、以下の欠落を発見した。

- [ADR-0032](0032-redefine-document-analyzer-responsibility.md)が定めた`Document`（Version 2.0）は`id` / `source_pdf_id` / `analysis` / `analyzed_at` / `analyzer_version`のみを持ち、**元PDFファイルの実際の所在（ファイルパス）を保持しない**。`source_pdf_id`は`PdfId`（不透明な整数ID）に過ぎず、それ自体からファイルパスを導出できない。
- [`docs/api/interfaces.md`](../api/interfaces.md)の`LayoutDetector.run(context, document: Document) -> LayoutDetectionResult`は、入力として`Document`のみを受け取る。`PdfRecord`（ファイルパスを持つ）は受け取らない。
- Layout Detectorが`repositories/`（`PdfRepository`）に依存してファイルパスを解決することは、[`docs/api/package-design.md`](../api/package-design.md)の`layout/`節（依存先: `models/`, `utils/`のみ）およびTask5の禁止事項（Repository参照）に反する。

したがって、現行の設計のままではLayout DetectorはPDF本文に一切アクセスできず、「Layout DetectorがPDF本文へアクセスできる唯一のStageである」という本Taskの要求を実装できない。

## 問題（Problem）

「Layout Detectorのみが PDF本文・文字列・Font・Bounding Box・Drawing・Rotation・画像・Annotationへアクセスできる」という設計方針を成立させるには、Layout Detectorが**Repositoryを経由せずに**元PDFファイルへ到達できる手段が`Document`自身に必要である。

## 決定（Decision）

### 1. `Document`に`file_path`フィールドを追加する

`Document`（Document Identity）に、由来PDFファイルの絶対パスを保持する`file_path: str`フィールドを追加する。

```python
@dataclass(frozen=True, slots=True)
class Document:
    id: DocumentId
    source_pdf_id: PdfId
    file_path: str
    analysis: DocumentAnalysisResult
    analyzed_at: datetime
    analyzer_version: str
```

- `file_path`はDocument Analyzer（`document/analyzer.py`）が、自身が既に検証済みの`PdfRecord.file_path`（`_ensure_exists()`で存在確認済み）をそのまま複写する。新たなファイルI/Oや検証を追加する必要はない。
- これは「Documentを変更しない」というTask5の制約（Layout DetectorがDocumentを書き換えない、様式判定結果を書き戻さない）とは異なる話である。本変更はLayout Detector実装**前**の設計修正であり、Document Analyzerの出力契約を1フィールド拡張するものであって、Layout Detectorがランタイムに`Document`を変更するものではない。

### 2. PDF本文アクセスの独占をLayout Detectorに限定する

以下を**Layout Detectorだけが**扱ってよいものとして明文化する。

- PDF本文（ページ単位の生テキスト）
- 文字列（`extract_text()`等による抽出結果そのもの）
- Font情報（フォント名・サイズ等）
- Bounding Box（テキスト・図形の座標範囲）
- Drawing（ベクター図形・罫線等の描画要素）
- Rotation（ページ回転角度）
- 画像（埋め込み画像オブジェクト）
- Annotation（注釈オブジェクト）

Document Analyzer（段階1）は、[ADR-0032](0032-redefine-document-analyzer-responsibility.md)により、上記のいずれにもアクセスしない（メタデータ・健全性・統計のみ）。中核パイプラインの他の段階（Section Parser以降）も、上記へ直接アクセスしない。**Section Parser以降が判定結果に基づく処理を行うために必要な情報は、Layout Detectorの出力（`LayoutDetectionResult`）を経由してのみ得る。**

Layout Detectorは`document.file_path`を用いてPDFファイルを自ら再読込する（`Document`が保持する`analysis`・メタデータは一切参照しない。二重読み込みになるが、[ADR-0032](0032-redefine-document-analyzer-responsibility.md)が定めた「各段階は独立した純粋な変換」という原則を優先し、Document AnalyzerとLayout Detectorの間で状態を共有しない）。

### 3. `LayoutDetectionResult`をVersion 2.0として再定義する

[ADR-0032](0032-redefine-document-analyzer-responsibility.md)時点の`LayoutDetectionResult`（`layout: Layout`, `confidence: Confidence`の2属性）を、Task5の実装指示に基づき以下のとおり拡張する。

```python
@dataclass(frozen=True, slots=True)
class LayoutDetectionResult:
    layout_id: str | None
    layout_version: int | None
    confidence: LayoutConfidence
    candidate_layouts: tuple[LayoutCandidate, ...]
    evidence: LayoutEvidence
    warnings: tuple[LayoutWarning, ...]
```

`layout_id` / `layout_version`が`None`になるのは、[`docs/review/queue.md`](../review/queue.md)が定める`layout_unknown`（既知の`era_id`に一致しない、またはConfidenceが閾値未満）の場合である。この場合もLayout Detectorは例外を送出せず、正常に`LayoutDetectionResult`を返す（[`docs/review/queue.md`](../review/queue.md#優先度スコアの算出)が`LayoutDetectionResult.confidence`を読み取ってレビューキューの優先度を算出する設計と整合させるため）。`LayoutDetectorError`は、PDFの再読込自体が失敗する等、判定処理そのものを実行できない場合にのみ送出する（[ADR-0032](0032-redefine-document-analyzer-responsibility.md)のDocument Analyzerと同様の例外設計方針）。

**`layout_id`の型についての補足**: 当初案では`Layout`（`layouts`テーブルの行、[`docs/database/schema.md`](../database/schema.md#2-layouts)）のDB主キーである`LayoutId`（不透明な`int`、`models/ids.py`）を型として想定していたが、これはLayout Detectorに実装不可能な要求を課すことが判明した。`LayoutDefinition`（Layout Detectorが判定に用いる唯一の入力データ）は`era_id: str`をキーとし、`LayoutId`を持たない。`era_id`から`LayoutId`（DB主キー）への変換にはLayout行の永続化状態の参照が必要であり、それは`repositories/`（`LayoutRepository`）への依存を意味するため、Task5の禁止事項（Repository参照）および本ADR自身の「Layout Detectorは`repositories/`に依存しない」という前提に反する。したがって`LayoutCandidate.layout_id`・`LayoutDetectionResult.layout_id`はいずれも`str`型とし、`LayoutDefinition.era_id`と同じ値域（`era_id`文字列）を表すものとして定義し直す（[`docs/review/queue.md`](../review/queue.md)が`layout_unknown`の判定条件を「既知の`era_id`に一致しない」と表現していることとも整合する）。`era_id`から`LayoutId`（DB主キー）への解決は、Layout Detectorより後段（永続化を担う層）の責務であり、本ADRの範囲外とする。

新設する型（`LayoutCandidate`, `LayoutConfidence`, `LayoutEvidence`, `LayoutMatch`, `LayoutDefinition`）の詳細は[`docs/api/models.md`](../api/models.md#layoutdetectionresult)を参照。

## 検討した代替案

- **`Document`に`file_path`を追加せず、`LayoutDetector.run()`のシグネチャに`PdfRecord`を追加する**（`run(context, document, source: PdfRecord) -> LayoutDetectionResult`）: [`docs/api/interfaces.md`](../api/interfaces.md)が既に確定している`PipelineStage[TIn, TOut]`という2引数（`context`, 単一の入力）の契約と食い違う。`PipelineStage.run(context, input: TIn) -> TOut`は単一の入力のみを取る設計（[`docs/api/pipeline.md`](../api/pipeline.md#pipelinestage)）であり、複数の入力を受け取るステージはFieldExtractor等一部の例外を除き避ける方針だったため、`Document`自体にファイルパスを持たせる方が既存契約との整合性が高いと判断した。
- **`Document`に`PdfRecord`全体を埋め込む**: `Document`が「Document Identity」（軽量な識別子・メタデータの束）であるという[ADR-0032](0032-redefine-document-analyzer-responsibility.md)の設計意図に反し、`PdfRecord`の他のフィールド（`content_hash`, `source_url`, `status`等）まで不要に伝播させることになるため、必要最小限の`file_path`のみを追加する案を採用した。
- **Layout DetectorがRepository（`PdfRepository`）経由でファイルパスを解決する**: Task5の明示的な禁止事項（Repository参照）およびADR-0032の`document/`・`layout/`双方の依存禁止ルール（`repositories/`への依存禁止）に反するため採用しなかった。

## 結果（トレードオフ, Consequences）

- `Document`の生成元がDocument Analyzerのみである限り、`file_path`は常に検証済みの値になる（Document Analyzerが`_ensure_exists()`で存在確認済みのパスを複写するため）。ただしLayout Detector実行時点でファイルが削除・移動されている可能性は排除できず、その場合はLayout Detector自身の再読込処理が失敗し`LayoutDetectorError`を送出する。
- Document AnalyzerとLayout Detectorが同一PDFファイルをそれぞれ独立に読み込む（二重読み込み）。処理性能上のコストはあるが、各段階が独立した純粋な変換であるという設計原則（ADR-0011, ADR-0032）を優先する。将来性能上の問題が顕在化した場合は、キャッシュ機構等を別ADRとして検討する。
- Section Parser（段階3）の入力契約（`docs/api/interfaces.md`の`SectionParser.run(context, document, layout_match)`）は、依然としてセクション切り出しに必要なテキストをどう得るかが未確定である。本ADRは「Layout DetectorのみがPDF本文にアクセスできる」という制約を明文化したことで、この未確定事項をより明確にした（Section Parserは`document.file_path`を用いた独自の再読込を行わないことが本ADRにより確定したため）。この解決は本ADRの範囲外とし、Task6（Section Parser実装）着手前に新規ADRとして確定する。

## Migration

1. `docs/api/models.md`の`Document`・`LayoutDetectionResult`・補助的な値オブジェクト節を本ADRの内容に同期する（同一PR）。
2. `src/mod_personnel_db/models/document.py`の`Document`（Version 2.0）に`file_path: str`を追加する。既存のVersion 1（`DocumentV1`/`PageV1`）には影響しない。
3. `src/mod_personnel_db/document/analyzer.py`の`Document(...)`生成箇所に`file_path=str(path)`を追加する。
4. 既存テスト（`tests/unit/models/test_document.py`, `tests/unit/document/test_analyzer.py`, `tests/unit/document/test_pipeline_integration.py`）の`Document(...)`呼び出し箇所に`file_path`を追加する。
5. `src/mod_personnel_db/layout/`を新規実装する（Task5-2, 5-3）。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/api/models.md`](../api/models.md) | `Document`に`file_path`追加。`LayoutDetectionResult`をVersion 2.0に再定義。`LayoutCandidate`/`LayoutConfidence`/`LayoutEvidence`/`LayoutMatch`/`LayoutDefinition`/`LayoutWarning`を新設 |
| [`docs/api/interfaces.md`](../api/interfaces.md) | `LayoutDetector`のdocstringに、PDF本文アクセス独占の明記と`document.file_path`利用の注記を追加 |
| [`docs/api/package-design.md`](../api/package-design.md) | `layout/`節の責務説明を更新（PDF再読込・Evidence抽出・Layout判定） |
| [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) | 保証11「Layout DetectorだけがPDF本文にアクセスできる」を新設 |
| [`docs/architecture.md`](../architecture.md) | Layout Detectorの責務説明にPDF再読込の言及を追加 |

## Architecture Contract

以下を[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)の保証11として追加する（詳細は同ファイルを正とする）。

> **保証11: Layout DetectorだけがPDF本文にアクセスできる。**
> `document/`パッケージ（Document Analyzer）は、メタデータ・健全性・統計取得のためにPDFファイルを開くが、本文テキスト・Font・Bounding Box・Drawing・Rotation・画像・Annotationのいずれも`Document`の出力に含めない（[ADR-0032](0032-redefine-document-analyzer-responsibility.md)）。`layout/`パッケージ（Layout Detector）のみが、`document.file_path`を用いてPDFファイルを再読込し、上記の情報を（`layout/`パッケージ内部の処理としてのみ）扱う。`layout/`より後続の段階（`sections/`以降）は、PDFファイルを直接読み込まず、`LayoutDetectionResult`（および将来のSection Parser設計で確定する追加の出力）のみを入力として受け取る。

## 関連ADR
- [ADR-0006](0006-pipeline-provenance.md) — パイプライン段階分割と来歴管理。
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0032](0032-redefine-document-analyzer-responsibility.md) — Document Analyzer責務再定義。本ADRが解決する未確定事項（Migration Plan Phase 3）の起点。
- [ADR-0033](0033-document-analyzer-output-field-composition.md) — Document Analyzer出力型のフィールド構成確定。同種のフィールド配置調整の先例。

（`LayoutDefinition`の実装ライブラリ選定は[ADR-0036](0036-pyyaml-for-layout-definition.md)を参照。同ADRは本ADRを前提とする側であり、本ADRからは参照しない——[ADR-0034](0034-pypdf-for-document-analyzer.md)が[ADR-0032](0032-redefine-document-analyzer-responsibility.md)を参照する向きと同型の関係）
