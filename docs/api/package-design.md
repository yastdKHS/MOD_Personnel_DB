# Package Design（`src/` パッケージ構成）

> **位置づけ**: 本ドキュメントは `src/mod_personnel_db/` 配下のパッケージ構成を定義する。**Pythonの実装（関数・メソッドの中身）はまだ開始しない。** ここで決めるのはパッケージの境界・責務・依存関係のみである。個々のコンポーネントの公開APIは[`interfaces.md`](interfaces.md)、依存関係の許可/禁止ルールは[`dependency-rule.md`](dependency-rule.md)を参照。
>
> 本ドキュメントが定める構成は、[`src/README.md`](../../src/README.md)（初期設計時のラフスケッチ）を置き換える、より詳細な正式設計である。`src/README.md`は本ドキュメントへのポインタとして更新する。

## 前提: 中核パイプラインとの対応

[ADR-0011](../adr/0011-fixed-core-pipeline.md)が固定した中核パイプライン（Document Analyzer → Layout Detector → Section Parser → Field Extractor → Normalizer → Validator）は変更しない。本ドキュメントの`document/` 〜 `validators/` の6パッケージは、この6段階に1対1で対応する。ユーザー提示の「Version 2.0 Architecture」図が追加する `Candidate Repository → Review → Gold Database` は、[`docs/architecture.md`](../architecture.md)が既に定義していた中核パイプライン外側の「格納（Store）」ステージを具体化したものであり、`repositories/`（Candidate/Gold双方の永続化）と`review/`（人手レビュー、[ADR-0021](../adr/0021-review-ui-strategy.md)）として実現する。中核パイプラインの構成自体への変更ではない。

## パッケージ一覧

```
src/mod_personnel_db/
    config/
    utils/
    models/
    repositories/
        sqlite/
    document/
    layout/
    sections/
    extractors/
    normalizers/
    validators/
    knowledge/
    learning/
    features/
    review/
    export/
    ftp/
    fetch/
    pipeline/
    services/
    cli/
```

ユーザー提示の一覧（`document/, layout/, sections/, extractors/, normalizers/, validators/, repositories/, knowledge/, learning/, features/, review/, export/, ftp/, pipeline/, models/, services/, utils/, config/`）を基本としつつ、以下2点を明示的に追加している。理由は各パッケージの節に記す。

- **`fetch/`**: PDF取得（[ADR-0006](../adr/0006-pipeline-provenance.md)・[ADR-0018](../adr/0018-pdf-registry-and-retention.md)）を担う。中核パイプラインの入力を用意する外側のステージとして必須だが、提示リストに含まれていなかったため追加した。
- **`cli/`**: [ADR-0021](../adr/0021-review-ui-strategy.md)が決定したレビュー用CLIツール、および運用コマンド全般のエントリポイント。

## 命名衝突に関する注意

以下2つのパッケージ名は、リポジトリ直下の**データディレクトリ**と同名である。両者は明確に別物であり、混同してはならない。

| コード（`src/mod_personnel_db/`配下） | データ（リポジトリ直下） | 関係 |
|---|---|---|
| `layout/`（Layout Detectorの実装コード） | `layouts/`（[ADR-0003](../adr/0003-layout-definition-strategy.md)、様式の構造定義YAML） | `layout/`パッケージは`layouts/`ディレクトリの内容を**読み込んで解釈するコード**。データそのものは持たない |
| `knowledge/`（KnowledgeServiceの実装コード） | `knowledge/`（[ADR-0005](../adr/0005-knowledge-base-normalization.md)、ドメイン知識YAML） | `knowledge/`パッケージは`knowledge/`ディレクトリの内容を**読み込んで解釈するコード**。データそのものは持たない |

---

## 各パッケージの詳細

### `config/`

- **目的**: 実行環境ごとの設定（DB接続情報、ストレージパス、外部サービス認証情報の参照先）を一箇所に集約する。
- **責務**: 環境変数・設定ファイルの読み込みと、型付き設定オブジェクト（`Settings`。実装はPydantic Settings、[ADR-0028](../adr/0028-pydantic-settings-for-configuration.md)、詳細は[`docs/configuration.md`](../configuration.md)）への変換。どのRepository実装（SQLite/将来のPostgreSQL）を使うかは、`config/`は文字列・enum等の**値**として提供するに留まり、実際にその実装クラスを`import`して組み立てる**配線**は行わない（配線は`cli/`が合成ルートとして担う、下記および[`dependency-rule.md`](dependency-rule.md#合成ルートcomposition-root)参照）。
- **依存先**: `utils/`のみ。**例外なし。**
- **依存禁止**: `utils/`以外の全パッケージ（`models/`を含む）。`config/`は誰からも依存されるが、他のいかなるパッケージにも依存しない、依存関係グラフの絶対的な末端である。`repositories/sqlite/`への依存は持たない——これを`config/`に許すと`repositories/sqlite/ → config/ → repositories/sqlite/`という循環（[`import-graph.md`](import-graph.md)で検出・修正済み）を生むため、合成ルートの役割は`cli/`に一本化する。

### `utils/`

- **目的**: ドメイン知識を一切持たない、汎用的な補助関数を提供する。
- **責務**: ハッシュ計算、日時フォーマット変換、汎用的なリトライ・バックオフヘルパー等。
- **依存先**: なし（標準ライブラリのみ）。
- **依存禁止**: 本プロジェクトの他の全パッケージ。`utils/`はプロジェクト内の依存関係グラフにおける絶対的な葉（leaf）でなければならない。

### `models/`

- **目的**: パイプライン全体で受け渡しされるドメインモデル（値オブジェクト）を定義する。詳細は[`models.md`](models.md)。
- **責務**: `Document`, `PersonnelSection`, `RawRecord`, `NormalizedRecord`, `ValidationResult`, `ReviewItem`, `KnowledgeItem`, `LearningRecord`, `ExportRecord`, `Job`, `ParserVersion`, `Layout`, `FeatureVector`等の不変（immutable）なデータ構造を持つ。ロジックを持たない、または持っても自己完結した検証ロジック（[`python-contract.md`](python-contract.md)参照）に限る。
- **依存先**: `utils/`のみ。
- **依存禁止**: `models/`は他のいかなるビジネスロジックパッケージにも依存しない。パイプライン全体・Repository全体から参照される中心的な語彙であり、循環依存を避けるため常に依存グラフの根に近い位置に置く。

### `repositories/`

- **目的**: 永続化の抽象契約（Protocol）を定義する。詳細は[`repositories.md`](repositories.md)。
- **責務**: `CandidateRepository`, `GoldRepository`, `KnowledgeRepository`, `LearningRepository`, `PDFRepository`, `JobRepository`, `ExportRepository`, `ReviewRepository`の8つのインターフェース（Protocol）と`UnitOfWork`を定義する。**具体的なDB技術（SQLite/PostgreSQL）への言及を一切含まない。**
- **依存先**: `models/`のみ。
- **依存禁止**: `sqlite3`等の具体的なDBドライバ、`config/`（接続情報はインターフェースの引数ではなく、具象実装側の関心事）。

#### `repositories/sqlite/`

- **目的**: `repositories/`が定義する8つのProtocolのSQLite実装を提供する。
- **責務**: `sqlite3`モジュールを用いたCRUD操作の実装。[`docs/database/schema.md`](../database/schema.md)のDDLに対応するSQL文を保持する。
- **依存先**: `repositories/`（実装するProtocol）、`models/`、`config/`（接続情報）、`utils/`。
- **依存禁止**: `document/`〜`validators/`, `knowledge/`, `learning/`, `features/`, `review/`, `export/`, `ftp/`, `pipeline/`, `services/`。**`repositories/sqlite/`は誰からも直接importされてはならない**（合成ルート以外）。これが[Task 3](repositories.md)の「SQLite依存禁止・PostgreSQL移行可能」を実現する境界である。将来`repositories/postgres/`を追加する場合も同じ境界規則に従う。

### `document/`（Document Analyzer）

- **目的**: 取得したPDFのメタデータ・健全性・基本統計を取得し、`Document`（Document Identity）を生成する（[ADR-0011](../adr/0011-fixed-core-pipeline.md)段階1、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)でVersion 2.0に再定義）。
- **責務**: PDFの存在確認・メタデータ取得（SHA256・ファイル名・作成/更新日時・PDFバージョン・暗号化有無）・健全性確認（破損有無）・基本統計取得（ページ数・ファイルサイズ・画像数・回転数・軽量プローブによる文字数）・警告生成のみ。PDF解析（構造抽出）・OCR・文字抽出・様式判定は行わない（Version 1設計からの変更点、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)）。
- **依存先**: `models/`, `utils/`のみ。
- **依存禁止**: `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`, `repositories/`（抽象含む）, `knowledge/`, その他すべてのサービス層パッケージ。「Document Analyzerはlayoutを知らない」（[`architecture-contract.md`](../architecture/architecture-contract.md)）をパッケージレベルで強制する。

### `layout/`（Layout Detector）

- **目的**: `Document`から、`layouts/`（トップレベルのデータディレクトリ）のどの`era_id`に該当するかを判定する（段階2）。
- **責務**（Version 2.0、[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md), [ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）: `document.file_path`を用いてPDFファイルを自ら再読込し、ページ解析・文字列取得・座標取得・Font取得・Rotation取得・Block取得を行ってLayout特徴量（`LayoutEvidence`）を抽出する。抽出したEvidenceを`LayoutDefinition`（判定ルール）と照合してConfidenceを算出し、`LayoutDetectionResult`を生成する。戻り値は、これを`.detection`として内包し、再読込した各ページの生テキストを`.pages`として保持する`LayoutArtifact`（ADR-0037）——これがSection ParserがPDF本文を得る唯一の経路となる。**PDF本文（文字列・Font・Bounding Box・Drawing・Rotation・画像・Annotation）へアクセスできるのは中核パイプライン中で`layout/`のみ**（Document Analyzerはメタデータ・健全性・統計のみ、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)）。
- **依存先**: `models/`, `utils/`のみ（プロジェクト内パッケージ）。外部ライブラリとして`pypdf`（PDF再読込、[ADR-0034](../adr/0034-pypdf-for-document-analyzer.md)）・`pyyaml`（`LayoutDefinition`のYAMLロード、[ADR-0036](../adr/0036-pyyaml-for-layout-definition.md)）に依存する。`layouts/<era_id>/manifest.yaml`のファイルI/Oは`layout/`パッケージ自身が直接行う（`document/`がPDFファイルを直接読むのと同様、Repositoryを経由しない）。
- **依存禁止**: `sections/`, `extractors/`, `normalizers/`, `validators/`, `repositories/`（抽象含む）, `knowledge/`, その他すべてのサービス層パッケージ。「Layout Detectorはfieldを知らない」を強制する。

### `sections/`（Section Parser）

- **目的**: Layout Detectorが生成した`LayoutArtifact`から、対象セクション（Personnel Block）を切り出す（段階3）。
- **責務**: `LayoutArtifact` → `SectionParseResult`（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）。Header/Body/Footer判定・Section境界判定・Section Evidence生成・Section Confidence算出を行う。
- **PDF非アクセス（ADR-0037）**: `sections/`パッケージはPDFファイルを直接読み込まず、`pypdf`等のPDF解析ライブラリにも依存しない。利用できるPDF由来のテキストは、入力`LayoutArtifact.pages`のみである（[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md)が確立した「Layout DetectorのみがPDF本文にアクセスできる」という保証の直接の帰結）。
- **依存先**: `models/`, `utils/`のみ。
- **依存禁止**: `knowledge/`, `repositories/`, `extractors/`, `normalizers/`, `validators/`。「Section Parserはknowledgeを知らない」を強制する。

### `extractors/`（Field Extractor）

- **目的**: セクションから個々のフィールドを抽出する（段階4）。
- **責務**（[ADR-0038](../adr/0038-field-extractor-produces-field-extraction-result.md)）: `PersonnelSection` → `FieldExtractionResult`。`section_text`の各行を構造的な区切り（連続空白等）で列に分割し、列位置ベースの汎用フィールド名（`column_1`, `column_2`, ...）で`RawRecord`を生成する。意味的フィールド名（`name`/`rank`等）への対応付け・正規化は行わない。
- **依存先**: `models/`, `utils/`のみ。
- **依存禁止**: `repositories/`（抽象・具象いずれも）, `knowledge/`, `learning/`, `features/`。「Field ExtractorはDBを知らない」を、一般的なDependency Rule（[`dependency-rule.md`](dependency-rule.md)）が許容する「repository経由なら可」よりも**厳格に**、repositoryへの依存自体を禁止する形で強制する（理由は[`dependency-rule.md`](dependency-rule.md#本プロジェクト固有の追加制約)参照）。

### `normalizers/`（Normalizer）

- **目的**: 抽出値を`knowledge/`の知識で正規化する（段階5）。
- **責務**: `RawRecord` → `NormalizationResult`（ADR-0040）。`KnowledgeSnapshot`（呼び出し元から注入される値オブジェクト）は`run()`の引数ではなく**コンストラクタ**で受け取る（`PipelineStage[RawRecord, NormalizationResult]`の単一入力規約を満たすため、ADR-0040）。
- **依存先**: `models/`, `utils/`のみ。`KnowledgeSnapshot`は`models/`に属する値オブジェクトであり、`knowledge/`パッケージ（サービス）そのものには依存しない。
- **依存禁止**: `knowledge/`（サービスパッケージ）, `repositories/`。「Normalizerは正規表現を持たない」の意味は[`architecture-contract.md`](../architecture/architecture-contract.md)を参照（ハードコードされたドメイン固有の正規表現パターンを禁止する趣旨であり、`re`モジュールの汎用的な利用自体は妨げない）。

### `validators/`（Validator）

- **目的**: 正規化後のデータをドメイン制約に基づき検証する（段階6）。
- **責務**: `NormalizedRecord` → `ValidationResult`（ADR-0041/ADR-0043）。`ValidationRuleSet`・`KnowledgeSnapshot`（いずれも呼び出し元から注入される値オブジェクト）・`RuleEngine`（差し替え可能な具象クラス、デフォルト実装あり）は`run()`の引数ではなく**コンストラクタ**で受け取る（`PipelineStage[NormalizedRecord, ValidationResult]`の単一入力規約を満たすため、ADR-0041）。`KnowledgeSnapshot`は、`column_N`から意味的フィールド名への対応付け（`category="layout"`、Normalizerと同じ規約）をValidatorも参照するために必要（ADR-0043）。**レコードの値そのものは変更しない**（[`architecture-contract.md`](../architecture/architecture-contract.md)）。
- **依存先**: `models/`, `utils/`のみ。`ValidationRuleSet`・`KnowledgeSnapshot`・`RuleEngine`はいずれも`models/`に属する値オブジェクト・具象クラスであり、`knowledge/`パッケージ（サービス）そのものには依存しない。
- **依存禁止**: `repositories/`, `knowledge/`, `learning/`, `normalizers/`（他段階への直接依存はしない。意味的フィールド名解決ロジックはNormalizerと重複するが、`validators/`内に独立実装する、ADR-0043）。検証NGの`learning_dataset`への記録は`validators/`自身ではなく`pipeline/`（呼び出し元）が行う。

### `knowledge/`（KnowledgeService）

- **目的**: `knowledge/`ディレクトリ（データ、8カテゴリ、[`docs/knowledge/schema.md`](../knowledge/schema.md)）を読み込み、`KnowledgeSnapshot`として提供する。
- **責務**: YAMLファイルの読み込み・検証（Draft 2020-12スキーマ）・`KnowledgeRepository`経由でのDBインデックス更新。
- **依存先**: `models/`, `repositories/`（抽象、`KnowledgeRepository`のみ）, `utils/`。
- **依存禁止**: `document/`〜`validators/`（中核パイプライン6段階への逆依存はしない。データは常に「注入される」側であり、パイプライン段階を呼び出すことはない）、`repositories/sqlite/`（具象、直接は使わない）。

### `learning/`（LearningService）

- **目的**: Learning Dataset（[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md), [ADR-0017](../adr/0017-learning-dataset-field-expansion.md)）のライフサイクル管理。
- **責務**: エントリの作成・状態遷移（open→in_review→reflected→verified/wontfix）・集計クエリの提供。
- **依存先**: `models/`, `repositories/`（抽象、`LearningRepository`のみ）, `utils/`。
- **依存禁止**: `document/`〜`validators/`, `repositories/sqlite/`。

### `features/`（FeatureStore）

- **目的**: `Confidence`算出等に用いる派生特徴量（`FeatureVector`）を計算・提供する。
- **責務**: `RawRecord`/`NormalizedRecord`等から特徴量（OCR品質シグナル、layout判定信頼度、過去の誤り発生率等）を計算する。**V2.0時点では永続ストレージを持たず、都度計算（on-demand）とする**（専用の`FeatureRepository`は[Task 3](repositories.md)の8リポジトリに含まれておらず、過剰設計を避けるため。将来キャッシュ性能が必要になった場合、非破壊的な拡張として`FeatureRepository`＋DBテーブルを追加検討する）。
- **依存先**: `models/`, `learning/`（過去の誤り発生率等の特徴量計算に`LearningService`の集計結果を使うため）, `utils/`。
- **依存禁止**: `document/`〜`validators/`（中核パイプラインへの逆依存はしない）, `repositories/`（直接のDB永続化を持たないため）。
- **既存判断との関係**: [`gap-analysis.md`](../adr/gap-analysis.md#feature-store)は「機械学習の学習・推論を行わないため」Feature Store関連のADRを不要と判定した。本パッケージはその判断と矛盾しない。ここでの`FeatureStore`は機械学習モデルの学習用データストアではなく、Validator/Confidence算出（[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)）を補助する**決定的な特徴量計算ユーティリティ**である。詳細な位置づけの整理は[`gap-analysis.md`](../adr/gap-analysis.md)末尾の追記を参照。

### `review/`（ReviewService）

- **目的**: 人手レビューのワークフローを提供する（[ADR-0021](../adr/0021-review-ui-strategy.md)）。
- **責務**: 検証NGキューの一覧化、レビュー確定処理、`gold_records`への昇格。
- **依存先**: `models/`, `repositories/`（抽象、`CandidateRepository`, `GoldRepository`, `ReviewRepository`, `LearningRepository`）, `learning/`, `utils/`。
- **依存禁止**: `document/`〜`validators/`, `repositories/sqlite/`, `knowledge/`（レビュー担当者が知識ベースを直接変更することはない。知識の変更は別途`knowledge/`配下ファイルへの通常のPRで行う、[ADR-0005](../adr/0005-knowledge-base-normalization.md)）。「Reviewはgold_recordsだけを更新できる」という制約の詳細解釈は[`architecture-contract.md`](../architecture/architecture-contract.md)を参照。

### `export/`（ExportService）

- **目的**: 公開用エクスポート（[ADR-0016](../adr/0016-public-json-format.md), [ADR-0022](../adr/0022-export-policy.md)）を生成する。
- **責務**: `GoldRepository`からのスナップショット取得、JSON Schema検証、CSV/Parquet変換、`ExportRepository`への記録。
- **依存先**: `models/`, `repositories/`（抽象、`GoldRepository`, `ExportRepository`）, `utils/`。
- **依存禁止**: `document/`〜`validators/`, `repositories/sqlite/`。

### `ftp/`（FTPService）

- **目的**: FTP/SFTP経由でのファイル配信・取得（既存の配布慣行がある場合の代替搬送路）。
- **責務**: `export/`が生成した成果物のFTPアップロード、または将来的な取得元がFTPを要求する場合のダウンロード。
- **依存先**: `utils/`のみ。
- **依存禁止**: `repositories/`, `models/`のドメインモデルへの依存はしない（バイト列・パス文字列のみを扱う、プロトコル層に徹する）。`export/`・`fetch/`から呼び出される側であり、逆方向の依存はしない。

### `fetch/`

- **目的**: 発令PDFを取得する（中核パイプラインの外側、[ADR-0006](../adr/0006-pipeline-provenance.md)）。
- **責務**: HTTPまたは`ftp/`経由でPDFを取得し、`PDFRepository`に記録する。
- **依存先**: `models/`, `repositories/`（抽象、`PDFRepository`）, `ftp/`, `utils/`。
- **依存禁止**: `document/`〜`validators/`（中核パイプラインへの依存はしない。取得と解析は独立したステージ）。

### `pipeline/`

- **目的**: 中核パイプライン6段階の実行を調整する。詳細は[`pipeline.md`](pipeline.md)。
- **責務**: `PipelineContext`/`PipelineStage`/`PipelineResult`/`PipelineEvent`/`PipelineException`/`PipelineMetrics`の提供、および`JobRunner`（各段階の呼び出し・Repositoryへの永続化）。
- **依存先**: `models/`, `repositories/`（抽象、`PDFRepository`, `CandidateRepository`, `JobRepository`）, `document/`, `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`, `knowledge/`, `learning/`, `utils/`。
- **依存禁止**: `repositories/sqlite/`（具象）, `review/`, `export/`, `ftp/`（これらは中核パイプラインの外側であり、`pipeline/`から呼び出さない。連携が必要な場合は`services/`が両者を束ねる）。

### `services/`

- **目的**: 単一の中核パイプライン実行に閉じない、横断的な運用オーケストレーションを提供する。
- **責務**: `Scheduler`（[ADR-0019](../adr/0019-workflow-orchestration.md)、実行トリガーの決定）。将来、複数パッケージ（`pipeline/`, `review/`, `export/`）を束ねる上位のワークフローが必要になった場合もここに置く。
- **依存先**: `pipeline/`, `review/`, `export/`, `models/`, `utils/`。
- **依存禁止**: `repositories/sqlite/`（具象）, `document/`〜`validators/`（`pipeline/`を介さず中核パイプライン段階を直接呼び出さない）。

### `cli/`

- **目的**: 人間が操作するコマンドラインエントリポイント（[ADR-0021](../adr/0021-review-ui-strategy.md)のレビューCLI等）であり、かつ**アプリケーション全体の合成ルート（Composition Root）**を担う。
- **責務**: コマンドライン引数の解析、`services/`・`review/`・`export/`等のAPI呼び出しに加え、起動時に`config/`から設定値を読み込み、それに基づいて`repositories/sqlite/`（将来は`repositories/postgres/`も）の具象実装を構築し、`UnitOfWork`として`pipeline/`・`services/`・`review/`・`export/`に注入する。
- **依存先**: `services/`, `review/`, `export/`, `pipeline/`, `config/`, `models/`, **`repositories/sqlite/`（合成ルートとしての唯一の例外、[`dependency-rule.md`](dependency-rule.md#合成ルートcomposition-root)）**。
- **依存禁止**: `document/`〜`validators/`（直接は呼ばない、`pipeline/`経由）。`repositories/sqlite/`への依存は`cli/`にのみ許される例外であり、他のいかなるパッケージにも拡大しない。

---

## パッケージ横断の依存先サマリ表

| パッケージ | 依存してよい | 依存してはならない（代表例） |
|---|---|---|
| `config/` | `utils/` | ビジネスロジック全般、`repositories/sqlite/`（合成の配線は`cli/`が担う。`config/`自身が担うと循環参照を生むため） |
| `utils/` | （なし） | プロジェクト内の全パッケージ |
| `models/` | `utils/` | ビジネスロジック全般、`repositories/` |
| `repositories/` | `models/` | `sqlite3`等の具体DBドライバ、`config/` |
| `repositories/sqlite/` | `repositories/`, `models/`, `config/`, `utils/` | 中核パイプライン6段階、サービス層 |
| `document/`〜`validators/` | `models/`, `utils/` | `repositories/`（抽象含む）, `knowledge/`, 他段階間の直接依存 |
| `knowledge/` | `models/`, `repositories/`（抽象）, `utils/` | 中核パイプライン6段階, `repositories/sqlite/` |
| `learning/` | `models/`, `repositories/`（抽象）, `utils/` | 中核パイプライン6段階, `repositories/sqlite/` |
| `features/` | `models/`, `learning/`, `utils/` | 中核パイプライン6段階, `repositories/` |
| `review/` | `models/`, `repositories/`（抽象）, `learning/`, `utils/` | 中核パイプライン6段階, `repositories/sqlite/`, `knowledge/` |
| `export/` | `models/`, `repositories/`（抽象）, `utils/` | 中核パイプライン6段階, `repositories/sqlite/` |
| `ftp/` | `utils/` | `repositories/`, `models/` |
| `fetch/` | `models/`, `repositories/`（抽象）, `ftp/`, `utils/` | 中核パイプライン6段階 |
| `pipeline/` | `models/`, `repositories/`（抽象）, 中核パイプライン6段階, `knowledge/`, `learning/`, `utils/` | `repositories/sqlite/`, `review/`, `export/`, `ftp/` |
| `services/` | `pipeline/`, `review/`, `export/`, `models/`, `utils/` | `repositories/sqlite/`, 中核パイプライン6段階（直接） |
| `cli/` | `services/`, `review/`, `export/`, `pipeline/`, `config/`, `models/`, `repositories/sqlite/`（合成ルートとしての例外） | 中核パイプライン6段階（直接） |

完全な依存グラフ（Mermaid）は[`dependency-rule.md`](dependency-rule.md)を参照。
