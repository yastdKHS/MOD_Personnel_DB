# 0037. Layout Detector Produces Layout Artifact

## ステータス
Accepted

## コンテキスト（Context）

[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)は、Layout Detector（中核パイプライン段階2）を**PDF本文（文字列・Font・Bounding Box・Drawing・Rotation・画像・Annotation）へアクセスできる唯一のPipeline Stage**と定めた。同ADRのConsequences節は、この決定の直接の帰結として「Section Parser（段階3）がセクション切り出しに必要なテキストをどう得るか」が**未確定のまま残る**ことを明記し、Task6着手前に新規ADRで確定するとしていた。

Phase2 Task6（Section Parser Implementation）は、この未確定事項を解決する。Task6の指示は以下を明確に定める。

- Section ParserはPDF本文へのアクセスを禁止される（PDF再読込・文字列抽出のいずれも禁止事項に含まれる）。
- Section Parserは**Layout Artifactのみ**を入力とする。
- 新ADR「Layout Detector Produces Layout Artifact」を追加し、「Layout Detectorだけが`LayoutArtifact`を生成する」「Section Parserは`LayoutArtifact`以外からPDF本文を取得してはならない」ことを決定する。

### Task6-0（Architecture Verification）で発見した追加の欠落

上記方針を実装可能性の観点から検証したところ、以下2件の欠落・不整合を追加で発見した。

1. **`docs/api/interfaces.md`の`SectionParser.run()`が2入力**: 現行シグネチャは`run(self, context, document: Document, layout_match: LayoutDetectionResult) -> tuple[PersonnelSection, ...]`であり、`PipelineStage[TIn, TOut]`が単一の入力のみを取るという確立済みの契約（[`docs/api/pipeline.md`](../api/pipeline.md#pipelinestage)、[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)の「検討した代替案」で同種の問題を指摘済み）と食い違う。
2. **`PersonnelSection.layout_id`の型不整合**: 既存モデル（Phase1設計、`models/candidate.py`）の`PersonnelSection.layout_id`は`LayoutId`（`layouts`テーブルのDB主キー`int`）型であり、`repositories/sqlite/candidate.py`が既にこの型でSQLの読み書き（`INSERT`・`SELECT`）を行っている。しかしSection ParserはRepositoryアクセスを禁止されるため、[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)が確定した`LayoutDetectionResult.layout_id: str`（`era_id`）以外の値を持ち得ず、DB主キーへ自ら解決することができない。これは[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)で発見・解決した`LayoutCandidate.layout_id`の型問題と同根の問題が、Phase1設計の`PersonnelSection`にも波及したものである。

## 問題（Problem）

1. Layout Detectorの現行出力（`LayoutDetectionResult`、[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)）は判定結果（`layout_id`/`confidence`/`evidence`統計等）のみを保持し、Section Parserがセクション切り出しに必要な**PDFページ本文のテキストそのもの**を保持しない。Layout Detectorは既にPDFを再読込してページテキストを抽出しているが（`layout/detector.py`の`_page_features`）、Evidence算出後にそのテキストを破棄している。
2. `SectionParser.run()`の入力契約が`PipelineStage[TIn, TOut]`の単一入力規約に違反している。
3. `PersonnelSection.layout_id`の型が、Repositoryアクセスを持たないSection Parserには構築不可能な値（DB主キー`LayoutId`）を要求している。

## 決定（Decision）

### 1. `LayoutArtifact`を新設し、Layout Detectorの戻り値とする

Layout Detectorが既に抽出しているページテキストを破棄せず、新設する`LayoutArtifact`（`models/layout_detection.py`）として保持する。

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

- `LayoutDetector.run(context, document: Document) -> LayoutArtifact`（**戻り値の型を`LayoutDetectionResult`から`LayoutArtifact`に変更**）。
- `detection`フィールドに[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)が確定した`LayoutDetectionResult`（形状は無変更）をそのまま格納する。[`docs/review/queue.md`](../review/queue.md)の`layout_unknown`判定が参照する`confidence`は、アクセス経路が`LayoutDetector.run()`の戻り値`.detection.confidence`に変わるのみで、値の意味・算出方法は無変更である。
- `pages`は、Layout Detectorが様式判定のために再読込した各ページの生テキストを、ページ順（0始まりの連番、`Document`のページ番号体系と対応）で保持する。これが**Section Parserに渡される、PDF本文の唯一の経路**となる。
- Layout Detectorが再読込したPDFファイル自体・`pypdf`のReader/Pageオブジェクトは`LayoutArtifact`に含めない（[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)の「PDF本文アクセスの独占」を`layout/`パッケージ内部に留める）。

これにより、`docs/api/models.md`が[ADR-0032](0032-redefine-document-analyzer-responsibility.md)以来「未確定」としていた「`PersonnelSection.page_range`が参照するページ範囲の妥当性検証対象」（Version 1の`Document.pages`に代わる存在）が、`LayoutArtifact.pages`として確定する。

### 2. Section ParserはLayoutArtifactのみを入力とする

```python
def run(self, context: PipelineContext, artifact: LayoutArtifact) -> SectionParseResult: ...
```

単一入力に修正し、`PipelineStage[LayoutArtifact, SectionParseResult]`として`PipelineStage[TIn, TOut]`契約に適合させる。Section Parserは`LayoutArtifact.pages`以外からPDF本文（テキスト）を取得してはならない。PDFファイルの再読込・`pypdf`等のPDF解析ライブラリへの依存は`sections/`パッケージに一切持たせない。

### 3. `PersonnelSection.layout_id`の型を`LayoutId`から`str`に変更する

[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)が`LayoutCandidate.layout_id`/`LayoutDetectionResult.layout_id`に適用したのと同じ理由・同じ解決策を`PersonnelSection.layout_id`にも適用する。Section Parserは`LayoutArtifact.detection.layout_id`（`str`、`era_id`）のみを持ち、DB主キー`LayoutId`へ解決する手段（Repositoryアクセス）を持たないため、`PersonnelSection.layout_id`の型を`str`（`era_id`）に変更する。

```python
@dataclass(frozen=True, slots=True)
class PersonnelSection:
    document_ref: PdfId
    layout_id: str  # era_id（変更前: LayoutId）
    section_index: int
    section_label: str | None
    page_range: tuple[int, int]
    section_text: str
```

**影響範囲**: `repositories/sqlite/candidate.py`が`PersonnelSection.layout_id`をDB主キー`LayoutId`として直接読み書きしている（`add_section`のINSERT・`_row_to_section`のSELECT）。本ADRにより、この読み書きを`era_id ⇔ layouts.id`の解決を伴う形に修正する（本PRで実施、Migration参照）。`personnel_sections`テーブルのDDL自体（`layout_id INTEGER`列、[`docs/database/schema.md`](../database/schema.md#3-personnel_sections)）は変更しない。`era_id`から`layouts.id`への解決はRepository層（`SqliteCandidateRepository.add_section`）が担う——これはRepositoryが唯一SQLiteへアクセスしてよい層であるという既存方針（[`docs/implementation.md`](../implementation.md#no-sqlite-dependency-outside-infrastructure)）と整合する。

なお、`era_id`は`(era_id, version)`の組でのみ`layouts`テーブルの行を一意に特定できるが、`PersonnelSection`は`layout_version`を保持しない。本ADRでは実装を簡潔に保つため、`era_id`の`status='active'`かつ最新`version`の行を解決対象とする（複数バージョンが同時に有効な運用は現時点で想定しない）。より厳密な版指定が必要になった場合は将来のADRで拡張する（TODO、本ADRのConsequences参照）。

## 検討した代替案

- **`Document`にページテキストを保持させる（Version 1設計への回帰）**: [ADR-0032](0032-redefine-document-analyzer-responsibility.md)が確定した「`Document`はページ単位の抽出済みテキストを保持しないDocument Identityである」という中核決定を覆すことになり、Document Analyzerの責務（メタデータ・健全性・統計のみ）にも矛盾するため採用しなかった。
- **`SectionParser.run()`が`Document`と`LayoutDetectionResult`の2引数を取り続け、Section Parser自身がPDFを再読込する**: Task6の禁止事項（PDF再読込・文字列抽出）および[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)の「Layout Detectorのみが PDF本文にアクセスできる」という保証に正面から反するため採用しなかった。
- **`PersonnelSection.layout_id`を`LayoutId | None`のまま維持し、Section Parserは`None`を設定する**: 永続化前提のモデルに構造的に無効な値（`None`が来ることを前提にした特別扱い）を持たせることになり、[`docs/database/schema.md`](../database/schema.md#3-personnel_sections)の`layout_id INTEGER NOT NULL`相当の制約とも整合しない。`str`型への変更の方が実態（Section Parserが実際に保持する値）を正直に表現する。

## 結果（トレードオフ, Consequences）

- Task5で確定した`LayoutDetector.run()`の戻り値型が`LayoutDetectionResult`から`LayoutArtifact`に変わる**破壊的変更**である。呼び出し元（`tests/unit/layout/`の該当テスト、[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)自体の記述内容）は本PRで追随修正する。[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)の核心決定（PDF本文アクセスの独占）自体は変更しないため、Supersededにはしない。
- `repositories/sqlite/candidate.py`への修正を伴う（Migration参照）。Section Parser自体はRepositoryへ一切依存しない（Task6の禁止事項を遵守）が、既存の`PersonnelSection`モデルの型変更に追随する必要のあるRepository実装コードの修正は、モデル変更の直接的な帰結として本PRに含める（[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)が`Document.file_path`追加時に呼び出し元テストを同一PRで修正したのと同じ扱い）。
- `era_id`の版指定（`layout_version`）を`PersonnelSection`が保持しないため、Repository層での`era_id → layouts.id`解決は「最新のactiveバージョン」に簡略化される。複数バージョンが同時運用される将来のシナリオでは別途ADRでの拡張が必要（TODO）。
- Field Extractor（段階4）以降は、引き続き`PersonnelSection`のみを入力とする（[`docs/api/interfaces.md`](../api/interfaces.md)の`FieldExtractor.run(context, section: PersonnelSection)`は無変更）。`LayoutArtifact`はSection Parserの入力としてのみ用いられ、それより後段には伝播しない。

## Migration

1. `docs/api/models.md`・`docs/api/interfaces.md`・`docs/api/package-design.md`・`docs/architecture.md`・`docs/architecture/architecture-contract.md`（保証12を新設）・[`docs/review/queue.md`](../review/queue.md)（`confidence`アクセス経路の記述）を本ADRの内容に同期する（同一PR）。
2. `src/mod_personnel_db/models/layout_detection.py`に`LayoutArtifactPage`・`LayoutArtifact`を追加する。
3. `src/mod_personnel_db/models/candidate.py`の`PersonnelSection.layout_id`の型を`LayoutId`から`str`に変更する。
4. `src/mod_personnel_db/layout/detector.py`の`LayoutDetector.run()`の戻り値を`LayoutArtifact`に変更する（`LayoutDetectionResult`の構築ロジック自体は無変更、`.detection`に格納する）。
5. `src/mod_personnel_db/repositories/sqlite/candidate.py`の`add_section`（`era_id → layouts.id`解決を追加）・`_row_to_section`（`layouts`とのJOINで`era_id`を取得）を修正する。
6. `src/mod_personnel_db/sections/`を新規実装する（Task6-1, 6-2, 6-3）。
7. 既存テスト（`tests/unit/layout/`, `tests/unit/models/test_document.py`は対象外、`tests/unit/models/test_layout_detection.py`, `tests/unit/repositories/test_candidate.py`, `tests/unit/repositories/test_gold.py`）の該当箇所を追随修正する。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/api/models.md`](../api/models.md) | `LayoutArtifact`・`LayoutArtifactPage`を新設。`PersonnelSection.layout_id`の型を`str`に変更（「未確定事項」の解消）。`SectionParseResult`・`SectionCandidate`・`SectionEvidence`を新設 |
| [`docs/api/interfaces.md`](../api/interfaces.md) | `LayoutDetector.run()`の戻り値を`LayoutArtifact`に変更。`SectionParser.run()`を単一入力に変更 |
| [`docs/api/package-design.md`](../api/package-design.md) | `sections/`節の責務説明を確定（PDF非アクセス・LayoutArtifact入力） |
| [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) | 保証12「Section ParserはLayoutArtifact経由でのみPDFのテキストを得られる」を新設 |
| [`docs/architecture.md`](../architecture.md) | Section Parserの責務説明にLayoutArtifact入力の言及を追加 |
| [`docs/review/queue.md`](../review/queue.md) | `layout_unknown`判定の参照経路を`LayoutDetector.run()`の戻り値`.detection.confidence`に更新 |

## Architecture Contract

以下を[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)の保証12として追加する（詳細は同ファイルを正とする）。

> **保証12: Section ParserはLayoutArtifact経由でのみPDFのテキストを得られる。**
> `sections/`パッケージは、PDFファイルを直接読み込まず、`pypdf`等のPDF解析ライブラリにも依存しない。Section Parserが利用できるPDF由来のテキストは、Layout Detector（`layout/`パッケージ）が生成した`LayoutArtifact.pages`のみである（[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)が確立した「Layout DetectorのみがPDF本文にアクセスできる」という保証の直接の帰結）。

## 関連ADR
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0032](0032-redefine-document-analyzer-responsibility.md) — Document Identityの再定義。`Document`がページテキストを保持しないという決定の起点。
- [ADR-0035](0035-layout-detector-owns-pdf-content-access.md) — Layout DetectorのPDF本文アクセス独占。本ADRが解決する未確定事項（Consequences節）の起点であり、本ADRの`LayoutDetectionResult.layout_id: str`の型決定を`PersonnelSection.layout_id`にも適用する。

（本ADRはADR-0035の核心決定（PDF本文アクセスの独占）を変更しないため、ADR-0035をSupersededにはしない。ADR-0033が`DocumentAnalysisResult`のフィールド配置を確定した際と同型の、既存ADRを補強する関係にある。）
