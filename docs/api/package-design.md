# Package Design（`src/` パッケージ構成）

> **位置づけ**: 本ドキュメントは `src/mod_personnel_db/` 配下のパッケージ構成を定義する。個々のコンポーネントの公開APIは[`interfaces.md`](interfaces.md)、依存関係の許可/禁止ルールは[`dependency-rule.md`](dependency-rule.md)を参照。
>
> 本ドキュメントが定める構成は、[`src/README.md`](../../src/README.md)（初期設計時のラフスケッチ）を置き換える、より詳細な正式設計である。`src/README.md`は本ドキュメントへのポインタとして更新する。
>
> **実装状況**: [`docs/reports/phase5-final-audit.md`](../reports/phase5-final-audit.md)（2026-07-21時点）作成時は`config/`・`features/`・`ftp/`・`fetch/`・`services/`が未実装だったが、Phase6 Task14-5で`config/`パッケージ（[ADR-0028](../adr/0028-pydantic-settings-for-configuration.md)採用）が実装され、さらにPhase7 Task16-1〜16-4で`ftp/`・`features/`・`fetch/`・`services/`が実装されたことで、現在は全19パッケージが実装済みである。Phase7 Task17-1〜17-4で、`ftp/`・`fetch/`・`services/`（`JobOrchestrator`・`Scheduler`）は`cli/`（Composition Root）へ配線され、`schedule-now`/`list-schedule`/`fetch-stage`/`run-workflow`の4コマンドとして利用可能になった（詳細は各節の「統合状況」参照、監査結果は[`docs/reports/phase7-final-audit.md`](../reports/phase7-final-audit.md)）。`features/`（`JobRunner`からの呼び出しなし）のみ、実装済みであっても他コンポーネントからの統合が未了のまま残る。各パッケージ節の冒頭に実装状況（実装済み／未実装）を明記する。

## 実装状況の凡例

| 表記 | 意味 |
|---|---|
| **実装済み** | `src/mod_personnel_db/`配下に対応するパッケージが存在し、本節の記述と実装が一致することを確認済み |
| **未実装** | `src/mod_personnel_db/`配下に対応するパッケージが存在しない。本節は将来実装する際の設計目標として保持する |

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

### `config/`（**実装済み**）

- **目的**: 実行環境ごとの設定（DB接続情報、ストレージパス、外部サービス認証情報の参照先）を一箇所に集約する。
- **責務**: 環境変数・設定ファイルの読み込みと、型付き設定オブジェクト（`Settings`。実装はPydantic Settings、[ADR-0028](../adr/0028-pydantic-settings-for-configuration.md)、詳細は[`docs/configuration.md`](../configuration.md)）への変換。どのRepository実装（SQLite/将来のPostgreSQL）を使うかは、`config/`は文字列・enum等の**値**として提供するに留まり、実際にその実装クラスを`import`して組み立てる**配線**は行わない（配線は`cli/`が合成ルートとして担う、下記および[`dependency-rule.md`](dependency-rule.md#合成ルートcomposition-root)参照）。
- **依存先**: `utils/`のみ。**例外なし。**（現在の実装は`utils/`への実際のimportすら持たず、外部ライブラリ`pydantic-settings`のみに依存する最小構成である）
- **依存禁止**: `utils/`以外の全パッケージ（`models/`を含む）。`config/`は誰からも依存されるが、他のいかなるパッケージにも依存しない、依存関係グラフの絶対的な末端である。`repositories/sqlite/`への依存は持たない——これを`config/`に許すと`repositories/sqlite/ → config/ → repositories/sqlite/`という循環（[`import-graph.md`](import-graph.md)で検出・修正済み）を生むため、合成ルートの役割は`cli/`に一本化する。
- **現状**: Phase6 Task14-5で実装済み。`config/settings.py`の`AppSettings`（`pydantic_settings.BaseSettings`）が、環境変数（`MOD_PERSONNEL_DB_`プレフィックス）・`.env`ファイル・コンストラクタ引数から設定値を読み込む（読み込み優先順位: コンストラクタ引数 > 環境変数 > `.env`ファイル > フィールドのデフォルト値、pydantic-settingsの既定動作）。フィールド構成（`db_path`/`knowledge_root`/`layouts_root`/`parser_code_version`）は、Task14-5より前に`cli/bootstrap.py`が保持していたローカルな`CompositionSettings`データクラスと等価である。`cli/bootstrap.py`は現在`CompositionSettings = AppSettings`という別名でこれを参照し、既存の呼び出し元（`cli/commands.py`・`cli/app.py`）は後方互換のまま同じ名前でimportし続けられる。`AppSettings`の生成（`AppSettings(...)`の呼び出し）は`cli/bootstrap.py`の`build_settings()`一箇所に限定される（[architecture-contract.md 保証15](../architecture/architecture-contract.md#15-依存生成責務はcomposition-rootcliに一本化される)）。`pydantic`・`pydantic-settings`は`pyproject.toml`に依存追加済み。`docs/configuration.md`が設計する`DatabaseSettings`/`FtpSettings`等のネスト構造・`Environment`・`SecretStr`は本Taskの対象外のままであり、未実装として残る。

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

### `repositories/`（**実装済み**）

- **目的**: 永続化の抽象契約（Protocol）を定義する。詳細は[`repositories.md`](repositories.md)。
- **責務**: `CandidateRepository`, `GoldRepository`, `KnowledgeRepository`, `LearningRepository`, `PDFRepository`, `JobRepository`, `ExportRepository`, `ReviewRepository`の8つのインターフェース（Protocol）を定義する。**具体的なDB技術（SQLite/PostgreSQL）への言及を一切含まない。**
- **依存先**: `models/`のみ。
- **依存禁止**: `sqlite3`等の具体的なDBドライバ、`config/`（接続情報はインターフェースの引数ではなく、具象実装側の関心事）。
- **`UnitOfWork`について**: 本節は策定当初、上記8 Protocolに加えて複数Repositoryにまたがる原子性のための`UnitOfWork`を定義するとしていたが、`repositories/__init__.py`に`UnitOfWork`は定義されていない。`JobRunner`（`pipeline/job_runner.py`）は`pdfs`/`jobs`/`candidates`の3 Repositoryのみを個別に注入する設計を採用しており（ADR-0046）、`UnitOfWork`を必要とする複数Repository原子性操作は現時点で存在しない。`UnitOfWork`は将来そのような操作が必要になった時点で追加検討する、未実装の設計候補である（詳細は[`repositories.md#unitofwork`](repositories.md#unitofwork)）。

#### `repositories/sqlite/`（**実装済み**）

- **目的**: `repositories/`が定義する8つのProtocolのSQLite実装を提供する。
- **責務**: `sqlite3`モジュールを用いたCRUD操作の実装。[`docs/database/schema.md`](../database/schema.md)のDDLに対応するSQL文を保持する。
- **依存先**: `repositories/`（実装するProtocol）、`models/`、`utils/`。**`config/`には依存しない**（`config/`は実装済みだが、DB接続先は`connect(db_path: str)`のように呼び出し元＝合成ルートの`cli/`から単純な文字列として渡され、`repositories/sqlite/`自身が設定オブジェクトを参照することはない、という設計判断による）。
- **依存禁止**: `document/`〜`validators/`, `knowledge/`, `learning/`, `features/`, `review/`, `export/`, `ftp/`, `pipeline/`, `services/`。**`repositories/sqlite/`は誰からも直接importされてはならない**（合成ルート以外）。これが[Task 3](repositories.md)の「SQLite依存禁止・PostgreSQL移行可能」を実現する境界である。将来`repositories/postgres/`を追加する場合も同じ境界規則に従う。

> **`PipelineContext`型依存について（中核6段階共通）**: `document/`〜`validators/`の6パッケージはいずれも、`PipelineStage.run(self, context: PipelineContext, input: TIn) -> TOut`（[`pipeline.md`](pipeline.md)）というProtocol実装のため、`from mod_personnel_db.pipeline import PipelineContext`をimportする。これは**型シグネチャ上必要な型参照のみ**であり、`repositories/`・`knowledge/`・`learning/`・`review/`・`export/`へのアクセスや`pipeline/`の実行ロジックへの依存を一切伴わない。`pipeline/__init__.py`が`job_runner.py`・6段階パッケージ自体をimportしないため、実行時の循環importは発生しない（詳細は[`dependency-rule.md#pipelinecontext型依存`](dependency-rule.md#pipelinecontext型依存)）。以下各節の「依存先」には、この型のみの依存を`pipeline/`（`PipelineContext`型のみ）と明記する。

### `document/`（Document Analyzer、**実装済み**）

- **目的**: 取得したPDFのメタデータ・健全性・基本統計を取得し、`Document`（Document Identity）を生成する（[ADR-0011](../adr/0011-fixed-core-pipeline.md)段階1、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)でVersion 2.0に再定義）。
- **責務**: PDFの存在確認・メタデータ取得（SHA256・ファイル名・作成/更新日時・PDFバージョン・暗号化有無）・健全性確認（破損有無）・基本統計取得（ページ数・ファイルサイズ・画像数・回転数・軽量プローブによる文字数）・警告生成のみ。PDF解析（構造抽出）・OCR・文字抽出・様式判定は行わない（Version 1設計からの変更点、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)）。
- **依存先**: `models/`, `utils/`, `pipeline/`（`PipelineContext`型のみ、上記参照）。
- **依存禁止**: `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`, `repositories/`（抽象含む）, `knowledge/`, その他すべてのサービス層パッケージ。「Document Analyzerはlayoutを知らない」（[`architecture-contract.md`](../architecture/architecture-contract.md)）をパッケージレベルで強制する。

### `layout/`（Layout Detector、**実装済み**）

- **目的**: `Document`から、`layouts/`（トップレベルのデータディレクトリ）のどの`era_id`に該当するかを判定する（段階2）。
- **責務**（Version 2.0、[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md), [ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）: `document.file_path`を用いてPDFファイルを自ら再読込し、ページ解析・文字列取得・座標取得・Font取得・Rotation取得・Block取得を行ってLayout特徴量（`LayoutEvidence`）を抽出する。抽出したEvidenceを`LayoutDefinition`（判定ルール）と照合してConfidenceを算出し、`LayoutDetectionResult`を生成する。戻り値は、これを`.detection`として内包し、再読込した各ページの生テキストを`.pages`として保持する`LayoutArtifact`（ADR-0037）——これがSection ParserがPDF本文を得る唯一の経路となる。**PDF本文（文字列・Font・Bounding Box・Drawing・Rotation・画像・Annotation）へアクセスできるのは中核パイプライン中で`layout/`のみ**（Document Analyzerはメタデータ・健全性・統計のみ、[ADR-0032](../adr/0032-redefine-document-analyzer-responsibility.md)）。
- **依存先**: `models/`, `utils/`, `pipeline/`（`PipelineContext`型のみ、上記参照）（プロジェクト内パッケージ）。外部ライブラリとして`pypdf`（PDF再読込、[ADR-0034](../adr/0034-pypdf-for-document-analyzer.md)）・`pyyaml`（`LayoutDefinition`のYAMLロード、[ADR-0036](../adr/0036-pyyaml-for-layout-definition.md)）に依存する。`layouts/<era_id>/manifest.yaml`のファイルI/Oは`layout/`パッケージ自身が直接行う（`document/`がPDFファイルを直接読むのと同様、Repositoryを経由しない）。
- **依存禁止**: `sections/`, `extractors/`, `normalizers/`, `validators/`, `repositories/`（抽象含む）, `knowledge/`, その他すべてのサービス層パッケージ。「Layout Detectorはfieldを知らない」を強制する。

### `sections/`（Section Parser、**実装済み**）

- **目的**: Layout Detectorが生成した`LayoutArtifact`から、対象セクション（Personnel Block）を切り出す（段階3）。
- **責務**: `LayoutArtifact` → `SectionParseResult`（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）。Header/Body/Footer判定・Section境界判定・Section Evidence生成・Section Confidence算出を行う。
- **PDF非アクセス（ADR-0037）**: `sections/`パッケージはPDFファイルを直接読み込まず、`pypdf`等のPDF解析ライブラリにも依存しない。利用できるPDF由来のテキストは、入力`LayoutArtifact.pages`のみである（[ADR-0035](../adr/0035-layout-detector-owns-pdf-content-access.md)が確立した「Layout DetectorのみがPDF本文にアクセスできる」という保証の直接の帰結）。
- **依存先**: `models/`, `utils/`, `pipeline/`（`PipelineContext`型のみ、上記参照）。
- **依存禁止**: `knowledge/`, `repositories/`, `extractors/`, `normalizers/`, `validators/`。「Section Parserはknowledgeを知らない」を強制する。

### `extractors/`（Field Extractor、**実装済み**）

- **目的**: セクションから個々のフィールドを抽出する（段階4）。
- **責務**（[ADR-0038](../adr/0038-field-extractor-produces-field-extraction-result.md)）: `PersonnelSection` → `FieldExtractionResult`。`section_text`の各行を構造的な区切り（連続空白等）で列に分割し、列位置ベースの汎用フィールド名（`column_1`, `column_2`, ...）で`RawRecord`を生成する。意味的フィールド名（`name`/`rank`等）への対応付け・正規化は行わない。
- **依存先**: `models/`, `utils/`, `pipeline/`（`PipelineContext`型のみ、上記参照）。
- **依存禁止**: `repositories/`（抽象・具象いずれも）, `knowledge/`, `learning/`, `features/`。「Field ExtractorはDBを知らない」を、一般的なDependency Rule（[`dependency-rule.md`](dependency-rule.md)）が許容する「repository経由なら可」よりも**厳格に**、repositoryへの依存自体を禁止する形で強制する（理由は[`dependency-rule.md`](dependency-rule.md#本プロジェクト固有の追加制約)参照）。

### `normalizers/`（Normalizer、**実装済み**）

- **目的**: 抽出値を`knowledge/`の知識で正規化する（段階5）。
- **責務**: `RawRecord` → `NormalizationResult`（ADR-0040）。`KnowledgeSnapshot`（呼び出し元から注入される値オブジェクト）は`run()`の引数ではなく**コンストラクタ**で受け取る（`PipelineStage[RawRecord, NormalizationResult]`の単一入力規約を満たすため、ADR-0040）。
- **依存先**: `models/`, `utils/`, `pipeline/`（`PipelineContext`型のみ、上記参照）。`KnowledgeSnapshot`は`models/`に属する値オブジェクトであり、`knowledge/`パッケージ（サービス）そのものには依存しない。
- **依存禁止**: `knowledge/`（サービスパッケージ）, `repositories/`。「Normalizerは正規表現を持たない」の意味は[`architecture-contract.md`](../architecture/architecture-contract.md)を参照（ハードコードされたドメイン固有の正規表現パターンを禁止する趣旨であり、`re`モジュールの汎用的な利用自体は妨げない）。

### `validators/`（Validator、**実装済み**）

- **目的**: 正規化後のデータをドメイン制約に基づき検証する（段階6）。
- **責務**: `NormalizedRecord` → `ValidationResult`（ADR-0041/ADR-0043）。`ValidationRuleSet`・`KnowledgeSnapshot`（いずれも呼び出し元から注入される値オブジェクト）・`RuleEngine`（差し替え可能な具象クラス、デフォルト実装あり）は`run()`の引数ではなく**コンストラクタ**で受け取る（`PipelineStage[NormalizedRecord, ValidationResult]`の単一入力規約を満たすため、ADR-0041）。`KnowledgeSnapshot`は、`column_N`から意味的フィールド名への対応付け（`category="layout"`、Normalizerと同じ規約）をValidatorも参照するために必要（ADR-0043）。**レコードの値そのものは変更しない**（[`architecture-contract.md`](../architecture/architecture-contract.md)）。
- **依存先**: `models/`, `utils/`, `pipeline/`（`PipelineContext`型のみ、上記参照）。`ValidationRuleSet`・`KnowledgeSnapshot`・`RuleEngine`はいずれも`models/`に属する値オブジェクト・具象クラスであり、`knowledge/`パッケージ（サービス）そのものには依存しない。
- **依存禁止**: `repositories/`, `knowledge/`, `learning/`, `normalizers/`（他段階への直接依存はしない。意味的フィールド名解決ロジックはNormalizerと重複するが、`validators/`内に独立実装する、ADR-0043）。検証NGの`learning_dataset`への記録は`validators/`自身ではなく`pipeline/`（呼び出し元）が行う。

### `knowledge/`（KnowledgeService、**実装済み**）

- **目的**: `knowledge/`ディレクトリ（データ、8カテゴリ、[`docs/knowledge/schema.md`](../knowledge/schema.md)）を読み込み、`KnowledgeSnapshot`として提供する。
- **責務**: YAMLファイルの読み込み・検証・`KnowledgeSnapshot`/`ValidationRuleSet`への変換。
- **依存先**: `models/`, `utils/`のみ。具象実装（`FileKnowledgeService`）はYAML読込に責務を限定し、DBインデックス更新は行わない（[interfaces.md#knowledgeservice](interfaces.md#knowledgeservice)）。
- **依存禁止**: `document/`〜`validators/`（中核パイプライン6段階への逆依存はしない。データは常に「注入される」側であり、パイプライン段階を呼び出すことはない）、`repositories/`（抽象含む）、`repositories/sqlite/`（具象、直接は使わない）。

### `learning/`（LearningService、**実装済み**）

- **目的**: Learning Dataset（[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md), [ADR-0017](../adr/0017-learning-dataset-field-expansion.md)）のライフサイクル管理。
- **責務**: エントリの作成・状態遷移（open→in_review→reflected→verified/wontfix）・集計クエリの提供。
- **依存先**: `models/`, `repositories/`（抽象、`LearningRepository`のみ）, `utils/`。
- **依存禁止**: `document/`〜`validators/`, `repositories/sqlite/`。

### `features/`（FeatureStore、**実装済み、Phase7 Task16-2**）

- **目的**: `Confidence`算出等に用いる派生特徴量（`FeatureVector`）を計算・提供する。
- **責務**: `src/mod_personnel_db/features/__init__.py`が`FeatureStore` Protocol（`compute(subject: RawRecord | NormalizedRecord) -> FeatureVector`、[interfaces.md#featurestore](interfaces.md)とシグネチャ一致）を定義する。具象実装`DefaultFeatureStore`（`features/store.py`）は、`RawRecord`/`NormalizedRecord`の内容のみから決定的に計算できる特徴量（`raw_field_fill_rate`：非空フィールド比率、`ocr_suspicious_char_rate`：疑わしい文字の混入率、`normalization_change_rate`：正規化による変化率、`NormalizedRecord`入力時のみ）を計算する。コンストラクタで`LearningService`（Protocol、オプション）を受け取った場合は`learning_open_error_count`（未解決Learning Dataset件数）を補助特徴量として追加する。`subject_ref`（`CandidateId`）は、`compute()`呼び出し時点でまだ永続化されていない入力に実DB主キーが存在しないため、`layout_id`・`section_ref`・`record_index`から決定的に導出した代理識別子とする。`*_confidence`/`*_rate`接尾辞の`float`特徴量は`features/validation.py`の`validate_feature_ranges()`が`0.0`〜`1.0`の値域を検証し、範囲外の場合`FeatureRangeError`を送出する（`models/feature.py`の`FeatureVector`docstringが`features/`パッケージへ委譲していた値域検証責務）。テスト用モック実装`MockFeatureStore`・既定値ヘルパー`default_feature_vector()`を`features/mock.py`が提供する。**V2.0時点では永続ストレージを持たず、都度計算（on-demand）とする**（専用の`FeatureRepository`は[Task 3](repositories.md)の8リポジトリに含まれておらず、過剰設計を避けるため）。
- **統合状況（Phase7 Task16-2時点）**: `pipeline/job_runner.py`（`JobRunner`）は`features/`を一切import・呼び出ししていない（確認済み）。`normalizers/`・`validators/`のコンストラクタへ`FeatureVector`を注入する統合（`KnowledgeSnapshot`/`ValidationRuleSet`のADR-0040/ADR-0041パターンに準じる計画）は、Phase7 Task16-0で設計方針のみ確定しており、**実装はまだ行われていない**。したがって`features/`は現時点でどのコンポーネントからも呼び出されない、独立した未接続のユーティリティパッケージである。この統合を実装する場合は、[ADR-0040](../adr/0040-normalizer-produces-normalization-result.md)/[ADR-0041](../adr/0041-validator-constructor-injects-validation-rule-set.md)に準じる新規ADRの起票と、`Normalizer`/`Validator`のコンストラクタ引数追加（後方互換に影響しうる変更）が前提となる。
- **依存先（実装確認済み）**: `models/`（`FeatureVector`, `NormalizedRecord`, `RawRecord`, `CandidateId`）, `learning/`（`LearningService` Protocolの型参照のみ、`DefaultFeatureStore`へのオプション注入用）, `utils/`（`features/exceptions.py`が`MODPersonnelDBError`を参照）。
- **依存禁止**: `document/`〜`validators/`（中核パイプラインへの逆依存はしない）, `repositories/`, `pipeline/`, `ftp/`, `fetch/`, `services/`, `cli/`（`tests/unit/features/test_dependency_ownership.py`がAST走査で機械的に検証）。
- **既存判断との関係**: [`gap-analysis.md`](../adr/gap-analysis.md#feature-store)は「機械学習の学習・推論を行わないため」Feature Store関連のADRを不要と判定した。本パッケージはその判断と矛盾しない。ここでの`FeatureStore`は機械学習モデルの学習用データストアではなく、Validator/Confidence算出（[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)）を補助する**決定的な特徴量計算ユーティリティ**である。詳細な位置づけの整理は[`gap-analysis.md`](../adr/gap-analysis.md)末尾の追記を参照。

### `review/`（ReviewService、**実装済み・下記の限定スコープで**）

- **目的**: 人手レビューのワークフローを提供する（[ADR-0021](../adr/0021-review-ui-strategy.md)）。
- **現在の責務（実装済み、Phase4 Task12-0）**: `review/__init__.py`が定める`ReviewService` Protocolと、その唯一の具象実装`RepositoryReviewService`（`review/service.py`）は、**Learning Dataset（`learning_dataset`テーブル、ADR-0013/0017）エントリの人手レビューに責務を限定する**——`list_pending()`（`status='open'`の一覧化）、`start_review()`/`approve()`/`reject()`（`LearningService.transition()`への委譲によるステータス遷移）のみを提供する。`approve()`は`GoldPromotion`（`review/__init__.py`）を指定した場合に限り、`GoldRepository.add_version()`への反映を内部で行う（この書き込み経路は`_promote_to_gold()`という非公開メソッドに一本化されている）。
- **本節が元々想定していたより広い設計**: 本節はもともと、検証NGキュー（`CandidateRecord`）の一覧化・レビューセッション管理・`ReviewRepository`を用いたレビュー全体のワークフローを想定していた（[`docs/api/review.md`](review.md)・[`docs/review/`](../review/)が定める、より広範な設計）。実装済みの`ReviewService`はこの広い設計のサブセットではなく、**別の狭い契約**である。両者の統合・命名の整理は将来のADRに委ねる（詳細はPhase4 Task12-0 Review Report）。
- **依存先（実装済みの狭い契約）**: `models/`, `repositories/`（抽象、`LearningRepository`, `GoldRepository`のみ。`CandidateRepository`・`ReviewRepository`は使用しない）, `learning/`, `utils/`。
- **依存禁止**: `document/`〜`validators/`, `repositories/sqlite/`, `knowledge/`（レビュー担当者が知識ベースを直接変更することはない。知識の変更は別途`knowledge/`配下ファイルへの通常のPRで行う、[ADR-0005](../adr/0005-knowledge-base-normalization.md)）。「Reviewはgold_recordsだけを更新できる」という制約の詳細解釈は[`architecture-contract.md`](../architecture/architecture-contract.md)を参照。

### `export/`（ExportService、**実装済み・下記の限定スコープで**）

- **目的**: 公開用エクスポート（[ADR-0016](../adr/0016-public-json-format.md), [ADR-0022](../adr/0022-export-policy.md)）を生成する。
- **現在の責務（実装済み、Phase4 Task12-1）**: `export/__init__.py`が定める`ExportService` Protocolと、その唯一の具象実装`RepositoryExportService`（`export/service.py`）は、**`GoldRepository`からの読み出しに責務を限定する**——`export_all()`（`list_current()`）、`export_since(since)`（`list_current(as_of=since)`）、`export_person(person_id)`（`get_history()`）のみを提供し、`GoldRecord`をそのまま返す。JSON Schema検証・CSV/Parquet変換・`ExportRepository`への記録は行わない。
- **本節が元々想定していたより広い設計**: 本節はもともと、JSON Schema検証・CSV/Parquet変換・`ExportRepository`を用いたエクスポート実行記録の管理までを想定していた（[`docs/api/interfaces.md#exportservice`](interfaces.md#exportservice)が定める、より広範な設計）。実装済みの`ExportService`はこの広い設計のサブセットではなく、**Gold Database読み出しに特化した別の契約**である。両者の統合・命名の整理は将来のADRに委ねる（詳細はPhase4 Task12-1 Review Report）。
- **依存先（実装済みの狭い契約）**: `models/`, `repositories/`（抽象、`GoldRepository`のみ。`ExportRepository`は使用しない）, `utils/`。
- **依存禁止**: `document/`〜`validators/`, `repositories/sqlite/`。

### `ftp/`（**実装済み、Phase7 Task16-1**）

- **目的**: FTP経由でのファイル配信・取得（既存の配布慣行がある場合の代替搬送路）。
- **責務**: `src/mod_personnel_db/ftp/__init__.py`が`FTPClient` Protocol（`connect()`/`upload(local_path, remote_path)`/`download(remote_path, local_path)`/`list_remote(remote_dir)`/`disconnect()`）を定義する。これは[interfaces.md#ftpservice](interfaces.md)が定める`FTPService`Protocol（`upload`/`download`/`list_remote`のみ）に、明示的な接続ライフサイクル管理（`connect`/`disconnect`）を加えた別の型であり、両者の統合・命名整理は将来のADRに委ねる（`review/`・`export/`の狭い契約と広い契約の関係と同様の扱い）。具象実装`StandardFTPClient`（`ftp/client.py`）は標準ライブラリ`ftplib`のみに依存し（新規の外部依存を追加しない）、接続・アップロード・ダウンロード・一覧取得・切断の各操作で`OSError`/`ftplib.Error`を`FTPConnectionError`/`FTPTransferError`（`ftp/exceptions.py`）へ変換する。テスト用モック実装`InMemoryFTPClient`（`ftp/mock.py`）を提供する。バイト列・パス文字列のみを扱う、プロトコル層に徹する（ドメインモデルを一切知らない）。
- **認証情報の扱い（実装確認済み）**: `ftp/`は`config/`に依存しない（実装上も参照なし）。接続先ホスト・ポート・ユーザー名・パスワード・タイムアウト・パッシブモードは`FTPConnectionConfig`（`ftp/config.py`、frozen dataclass）として、呼び出し側がプレーンな引数で渡す。これは上記[`repositories/sqlite/`](#repositoriessqlite実装済み)が`config/`に直接依存せず、DB接続文字列を合成ルート`cli/`から単純な文字列として受け取る既存の設計判断と同じ理由による。
- **依存先（実装確認済み）**: `utils/`のみ（`ftp/exceptions.py`が`MODPersonnelDBError`を参照）。
- **依存禁止**: `repositories/`, `models/`のドメインモデル, `config/`（実装上も参照なし、`tests/unit/ftp/test_dependency_ownership.py`がAST走査で機械的に検証）。
- **統合状況（Phase7 Task17-1で更新）**: `export/`・`fetch/`は`ftp/`を呼び出していない（実装上も参照なし）。`ftp/`を実際に呼び出すのは`services/`（`DefaultJobOrchestrator.export_and_publish()`が`remote_path`指定時に`connect`/`upload`/`disconnect`を呼び出す）である。`cli/bootstrap.py`の`build_ftp_client()`（Task17-1で追加）が`StandardFTPClient`を生成し、`cli/`の`run-workflow --remote-path`コマンド経由で到達可能になった。ただし`build_ftp_client()`は`FTPConnectionConfig(host="")`という接続情報を持たないプレースホルダを生成しており（`config/`に`FtpSettings`が未実装のため）、実際のFTPサーバへは接続できない状態のまま残る（下記`config/`節・[`RELEASE_STATUS.md`](../../RELEASE_STATUS.md)のKnown Limitations参照）。

### `fetch/`（**実装済み、Phase7 Task16-3、HTTP経由の取得機構に限定**）

- **目的**: 発令PDFを取得する（中核パイプラインの外側、[ADR-0006](../adr/0006-pipeline-provenance.md)）。
- **責務（実装確認済み）**: `src/mod_personnel_db/fetch/__init__.py`が`FetchClient` Protocol（`fetch(request: FetchRequest) -> FetchResult`）を定義する。具象実装`HTTPFetchClient`（`fetch/client.py`）は標準ライブラリ`urllib.request`のみに依存し（新規の外部依存を追加しない）、`http`/`https`以外のURLスキームを明示的に拒否する（`file://`等の意図しないローカルファイル読み取りを防ぐ安全対策）。HTTPステータスコード・Content-Typeを検証し（既定は`200`のみ許可、`expected_content_types`で追加検証可能）、タイムアウト・ネットワークエラーを`FetchTimeoutError`/`FetchNetworkError`（`fetch/exceptions.py`）へラッピングする。`FetchRequest`/`FetchResult`（`fetch/messages.py`）は`fetch/`ローカルの値オブジェクトであり、`models/`のドメインモデルではない。テスト用モック実装`MockFetchClient`・既定値ヘルパー`default_fetch_result()`を`fetch/mock.py`が提供する。
- **Scope（Task16-3で確定した狭い契約）**: 本節が元々想定していた「`ftp/`経由の取得」「`content_hash`計算・`PDFRepository`への重複排除登録」は、**`fetch/`パッケージ自体には実装されていない**（`fetch/`は`models/`・`repositories/`・`ftp/`のいずれもimportしない、実装上も確認済み）。これらの責務は`services/`（`DefaultJobOrchestrator.fetch_and_stage()`）が代わりに実装している（下記`services/`節参照）。`fetch/`はHTTP経由の取得機構（転送層）のみを提供する、より狭い契約として実装された。
- **PDF本文へのアクセスに関する制約（実装確認済み）**: `fetch/`はPDFファイルのバイト列を取得するのみであり、**PDF本文（テキスト・レイアウト構造）を解析・読み取りしてはならない**。これは「Layout DetectorだけがPDF本文にアクセスできる」という[architecture-contract.md 保証11](../architecture/architecture-contract.md#11-layout-detectorだけがpdf本文にアクセスできる)を`fetch/`にも適用したものであり、`fetch/`配下のソースは`pypdf`等のPDF専用ライブラリを一切importしないことを確認済み。
- **起動契機（Phase7 Task17-1で更新）**: `fetch/`は`JobRunner`・`pipeline/`から直接呼び出されない（実装上も参照なし）。`fetch/`（`FetchClient`）を実際に呼び出すのは`services/`（`DefaultJobOrchestrator.fetch_and_stage()`）である。`cli/bootstrap.py`の`build_fetch_client()`（Task17-1で追加）が`HTTPFetchClient`を生成し、`cli/`の`fetch-stage`コマンド経由で到達可能になった。
- **依存先（実装確認済み）**: `utils/`のみ（`fetch/exceptions.py`が`MODPersonnelDBError`を参照）。
- **依存禁止**: `document/`〜`validators/`, `models/`, `repositories/`, `ftp/`, `features/`, `services/`, `cli/`（`tests/unit/fetch/test_dependency_ownership.py`がAST走査で機械的に検証）。

### `pipeline/`（**実装済み**）

- **目的**: 中核パイプライン6段階の実行を調整する。詳細は[`pipeline.md`](pipeline.md)。パッケージ内部は「`JobRunner` → `PipelineRunner` → `PipelineStage`」の層構造を持ち、両者の責務は分離されている（[ADR-0044](../adr/0044-pipelinerunner-jobrunner-boundary.md)）。
- **責務（`PipelineRunner`、`pipeline/runner.py`、実装済み）**: `PipelineContext`/`PipelineStage`/`PipelineResult`/`PipelineEvent`/`PipelineException`/`PipelineMetrics`の提供、および登録済み`PipelineStage`列の順次呼び出し（Artifact受け渡し・イベント記録）のみ。Stage生成（コンストラクタ注入）・`PipelineContext`生成・永続化は行わない。
- **責務（`JobRunner`、`pipeline/job_runner.py`、実装済み）**: `PipelineContext`生成、`KnowledgeSnapshot`/`ValidationRuleSet`取得によるStage生成（コンストラクタ注入）、`PipelineBuilder`経由での`PipelineRunner`への登録・呼び出し、`PipelineResult`のRepositoryへの永続化、Learning記録（[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md)）。加えて、集約Artifact（`SectionParseResult`/`FieldExtractionResult`/`NormalizationResult`）を反復処理し`PipelineRunner`を必要な回数呼び出すCoordinator責務を持つ（[ADR-0045](../adr/0045-job-runner-aggregate-artifact-coordinator.md)）。この展開は`PipelineRunner`側では行わない。
- **依存先（パッケージ全体、`JobRunner`が必要とする分を含む）**: `models/`, `repositories/`（抽象、`PDFRepository`, `CandidateRepository`, `JobRepository`）, `document/`, `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`, `knowledge/`, `learning/`, `utils/`。**ただし`PipelineRunner`自身のコードは`repositories/`, `knowledge/`, `learning/`のいずれにも依存しない**（[architecture-contract.md 保証13](../architecture/architecture-contract.md#13-pipelinerunnerはrepositoryknowledgelearningreviewexportを知らない)）。これらへの依存は`JobRunner`の責務としてのみ生じる。逆方向として、`document/`〜`validators/`の6パッケージ側から`pipeline/`（`PipelineContext`型のみ）への型依存がある（上記「`PipelineContext`型依存について」参照）。この逆方向の依存は`pipeline/__init__.py`が6段階パッケージ・`job_runner.py`をimportしないことで循環を回避しており、`pipeline/ → 6段階`という一方向の実行時依存構造そのものは維持される。
- **依存禁止**: `repositories/sqlite/`（具象）, `review/`, `export/`, `ftp/`（これらは中核パイプラインの外側であり、`pipeline/`から呼び出さない。実際の連携は`cli/`が合成ルートとして直接束ねる。`services/`は実装済みだが、`pipeline/`はこれとも依存関係を持たない。下記`services/`節参照）。

### `services/`（**実装済み、Phase7 Task16-4**）

- **目的**: 単一の中核パイプライン実行に閉じない、横断的な運用オーケストレーションを提供する。
- **責務（実装確認済み）**: `src/mod_personnel_db/services/__init__.py`が`JobOrchestrator` Protocol（`fetch_and_stage`/`run_job`/`run_pending_pipeline`/`list_pending_reviews`/`export_and_publish`/`run_workflow`）を定義する。これは[interfaces.md#scheduler](interfaces.md)が定める`Scheduler`Protocol（`trigger_now`/`list_upcoming`）とは異なる、別の独立した契約である。`Scheduler`は`services/scheduler.py`（Phase7 Task17-3）に標準実装`DefaultScheduler`が存在し、`JobOrchestrator`のみに依存する（`JobRunner`・`ReviewService`・`ExportService`・`FetchClient`・`FTPClient`・Repositoryのいずれにも直接依存しない）。具象実装`DefaultJobOrchestrator`（`services/orchestrator.py`）は、`OrchestratorDependencies`（コンストラクタ注入専用のfrozen dataclass、`pipeline.job_runner.JobRunnerRepositories`と同じ設計判断）経由でのみ依存を受け取る。`fetch_and_stage()`は`FetchClient`で取得したバイト列のSHA-256を`content_hash`として計算し、`PDFRepository.get_by_hash()`で重複排除した上で`PDFRepository.add()`へ登録する（`fetch/`自体が実装していない責務を`services/`側で担う、上記`fetch/`節参照）。`run_job()`/`run_pending_pipeline()`は`JobRunner`へ委譲する。`export_and_publish()`は`ExportService`でエクスポートを生成し、`remote_path`指定時のみ`FTPClient`でアップロードする。`run_workflow()`はFetch（個別URL失敗を収集し継続）→Pipeline→Review（読み取りのみ）→Export/Publish（フェイルファスト）の順に実行する。
- **依存先（実装確認済み）**: `fetch/`（`FetchClient`, `FetchRequest`, `FetchError`）, `ftp/`（`FTPClient`）, `pipeline/`（`PipelineResult`型、および`pipeline.job_runner.JobRunner`——`cli/bootstrap.py`が同モジュールから直接importする既存の慣行に準じる）, `review/`（`ReviewService`）, `export/`（`ExportService`）, `repositories/`（抽象、`PDFRepository`のみの型参照。具象は一切生成しない）, `models/`（`ExportArtifact`, `ExportFormat`, `LearningRecord`, `PdfId`, `PdfRecord`）。**`utils/`への依存は持たない**（`services/`は独自の例外クラスを持たず、`utils.exceptions`を参照する必要がないため。Phase7 Task16-0時点の計画では`utils/`への依存を想定していたが、実装では不要であった）。
- **依存生成責務についての確認（実装確認済み）**: `services/`は`fetch/`・`ftp/`・`pipeline/`・`review/`・`export/`の**具象実装を自ら生成しない**（`tests/unit/services/test_dependency_ownership.py`がAST走査で、`DefaultJobOrchestrator.__init__`が属性代入のみを行い新規オブジェクトを生成しないことを機械的に検証）。他のいかなるパッケージも具象実装を生成しないという[architecture-contract.md 保証15](../architecture/architecture-contract.md#15-依存生成責務はcomposition-rootcliに一本化される)は`services/`にもそのまま適用される。
- **依存禁止**: `repositories/sqlite/`（具象）, `document/`〜`validators/`, `cli/`（実装上も参照なし）。
- **統合状況（Phase7 Task17-1/17-3/17-4で更新）**: `cli/bootstrap.py`は`build_job_orchestrator()`（Task17-1）・`build_scheduler()`（Task17-4）を通じて`services/`（`DefaultJobOrchestrator`・`DefaultScheduler`・`OrchestratorDependencies`）を参照する（`services/`自体は依然`cli/`をimportしない、一方向の依存のまま）。`cli/`は、既存の`pipeline/`・`review/`・`export/`直接呼び出しの構成を維持したまま、これに加算する形で`services/`層経由のコマンド4種（`fetch-stage`/`run-workflow`/`schedule-now`/`list-schedule`）を追加した（下記`cli/`参照）。`cli/commands.py`は`JobOrchestrator`/`Scheduler`をいずれもProtocol型としてのみ参照し、具象実装（`DefaultJobOrchestrator`・`DefaultScheduler`）の生成は`cli/bootstrap.py`（Composition Root）に一本化されている。`schedule-now`（`Scheduler.trigger_now()`のみ呼び出す）・`list-schedule`（`Scheduler.list_upcoming()`のみ呼び出す）はいずれも`JobOrchestrator`を直接呼び出さない。CLIから周期実行対象（`JobSchedule`）を設定する手段は未実装のため、`list-schedule`は現時点で常に0件を返す。

### `cli/`（**実装済み**）

- **目的**: 人間が操作するコマンドラインエントリポイント（[ADR-0021](../adr/0021-review-ui-strategy.md)のレビューCLI等）であり、かつ**アプリケーション全体の合成ルート（Composition Root）**を担う。他のいかなるパッケージ（`pipeline/`・`repositories/`を含む）も具象実装を生成しない（[ADR-0046](../adr/0046-composition-root-dependency-injection-contract.md)、[architecture-contract.md 保証15](../architecture/architecture-contract.md#15-依存生成責務はcomposition-rootcliに一本化される)）。
- **責務**: コマンドライン引数の解析、`review/`・`export/`等のAPI呼び出しに加え、起動時に`repositories/sqlite/`（将来は`repositories/postgres/`も）・`KnowledgeService`・`LearningService`・`ReviewService`・`ExportService`の具象実装を、Repository具象生成→`KnowledgeService`生成→`LearningService`生成→`ReviewService`生成→`ExportService`生成→`JobRunner`生成の順に構築する（ADR-0046）。`JobRunner`（`pipeline/job_runner.py`）へは`JobRunnerRepositories`・`KnowledgeService`・`LearningService`・`ParserVersionId`・`layout_definitions`を個別に注入する。`UnitOfWork`（未実装、上記`repositories/`節参照）は`JobRunner`へは注入しない（`JobRunner`が必要とするRepositoryは`pdfs`/`jobs`/`candidates`の3種のみであり、複数Repositoryにまたがる原子性が必要な操作を現時点で行わないため）。パイプライン実行（`run-pending`/`run-job`）・Review（`review list`/`start`/`approve`/`reject`）・Export（`export all`/`person`/`since`）は、それぞれ独立したCLIサブコマンドとして提供し、`cli/`がこれらを1プロセス内で自動的に直列実行することはない。
- **依存先**: `review/`, `export/`, `pipeline/`, `models/`, **`repositories/sqlite/`（合成ルートとしての唯一の例外、[`dependency-rule.md`](dependency-rule.md#合成ルートcomposition-root)）**, `knowledge/`, `learning/`, `layout/`（`layouts/<era_id>/manifest.yaml`の読み込みに`layout.definitions.load_layout_definitions`を利用するため）, `config/`（Phase6 Task14-5で追加。`cli/bootstrap.py`が`AppSettings`を`build_settings()`経由で生成する唯一の箇所、上記`config/`節参照）。**`services/`・`fetch/`・`ftp/`はPhase7 Task17-1〜17-4で`cli/bootstrap.py`へ配線済みである**（`build_fetch_client()`/`build_ftp_client()`/`build_job_orchestrator()`/`build_scheduler()`）。`features/`のみ、Phase7で実装済みだが`cli/bootstrap.py`はこれを参照していない（`JobRunner`への統合が未実装のため、上記`features/`節参照）。
- **依存禁止**: `document/`〜`validators/`（`layout/`を除き直接は呼ばない、`pipeline/`経由）。`repositories/sqlite/`への依存は`cli/`にのみ許される例外であり、他のいかなるパッケージにも拡大しない。
- **Phase7統合の生成順序（Task17-0で設計確定、Task17-1/17-4で実装済み）**: [`docs/phase7-integration-design.md`](../phase7-integration-design.md)が設計した、既存の生成順序1〜7（上記）に続く順序8「`FetchClient`生成」（`build_fetch_client()`）・順序9「`FTPClient`生成」（`build_ftp_client()`。`AppSettings`への`FtpSettings`追加が前提だったが未実装のまま`FTPConnectionConfig(host="")`というプレースホルダで生成する暫定実装とした）・順序10「`JobOrchestrator`生成」（`build_job_orchestrator()`）をTask17-1で実装した。Task17-4はこれに続けて`build_scheduler()`（`JobOrchestrator`・周期実行対象一覧・`clock`を受け取り`DefaultScheduler`を返す）を追加した。既存の生成順序1〜7・`build_settings()`等の既存公開関数のシグネチャはこの統合によって変更していない（加算的統合）。`FeatureStore`用の`build_feature_store()`は生成済みだが、消費先（`JobRunner`のコンストラクタ拡張）が未確定なため、いずれの生成順序にも組み込まれず未使用のまま提供される。

---

## パッケージ横断の依存先サマリ表

| パッケージ | 実装状況 | 依存してよい | 依存してはならない（代表例） |
|---|---|---|---|
| `config/` | 実装済み | `utils/` | ビジネスロジック全般、`repositories/sqlite/`（合成の配線は`cli/`が担う。`config/`自身が担うと循環参照を生むため） |
| `utils/` | 実装済み | （なし） | プロジェクト内の全パッケージ |
| `models/` | 実装済み | `utils/` | ビジネスロジック全般、`repositories/` |
| `repositories/` | 実装済み | `models/` | `sqlite3`等の具体DBドライバ、`config/` |
| `repositories/sqlite/` | 実装済み | `repositories/`, `models/`, `utils/`（`config/`には依存しない。DB接続先は合成ルート`cli/`から単純な文字列として渡される設計のため） | 中核パイプライン6段階、サービス層 |
| `document/`〜`validators/` | 実装済み | `models/`, `utils/`, `pipeline/`（`PipelineContext`型のみ） | `repositories/`（抽象含む）, `knowledge/`, 他段階間の直接依存 |
| `knowledge/` | 実装済み | `models/`, `utils/` | 中核パイプライン6段階, `repositories/`（抽象含む）, `repositories/sqlite/` |
| `learning/` | 実装済み | `models/`, `repositories/`（抽象）, `utils/` | 中核パイプライン6段階, `repositories/sqlite/` |
| `features/` | 実装済み（`JobRunner`未統合） | `models/`, `learning/`, `utils/` | 中核パイプライン6段階, `repositories/`, `pipeline/`, `ftp/`, `fetch/`, `services/`, `cli/` |
| `review/` | 実装済み（限定スコープ） | `models/`, `repositories/`（抽象、`LearningRepository`, `GoldRepository`のみ）, `learning/`, `utils/` | 中核パイプライン6段階, `repositories/sqlite/`, `knowledge/` |
| `export/` | 実装済み（限定スコープ） | `models/`, `repositories/`（抽象、`GoldRepository`のみ）, `utils/` | 中核パイプライン6段階, `repositories/sqlite/` |
| `ftp/` | 実装済み | `utils/` | `repositories/`, `models/`, `config/` |
| `fetch/` | 実装済み（HTTP経由の取得機構に限定） | `utils/` | 中核パイプライン6段階, `models/`, `repositories/`, `ftp/`, `features/`, `services/`, `cli/` |
| `pipeline/`（パッケージ全体・`JobRunner`分を含む） | 実装済み | `models/`, `repositories/`（抽象）, 中核パイプライン6段階, `knowledge/`, `learning/`, `utils/` | `repositories/sqlite/`, `review/`, `export/`, `ftp/`, `features/`, `services/` |
| `services/` | 実装済み（`cli/`配線済み） | `fetch/`, `ftp/`, `pipeline/`, `review/`, `export/`, `repositories/`（抽象、`PDFRepository`のみ）, `models/` | `repositories/sqlite/`, 中核パイプライン6段階（直接）, `cli/` |
| `cli/` | 実装済み | `review/`, `export/`, `pipeline/`, `models/`, `knowledge/`, `learning/`, `layout/`, `config/`, `fetch/`, `ftp/`, `services/`, `repositories/sqlite/`（合成ルートとしての例外） | 中核パイプライン6段階（直接、`layout/`を除く）, `features/` |

上記`pipeline/`行はパッケージ全体（`JobRunner`が必要とする依存を含む）のサマリである。`PipelineRunner`（`pipeline/runner.py`）自身は`repositories/`, `knowledge/`, `learning/`のいずれにも依存しない（[ADR-0044](../adr/0044-pipelinerunner-jobrunner-boundary.md)、[architecture-contract.md 保証13](../architecture/architecture-contract.md#13-pipelinerunnerはrepositoryknowledgelearningreviewexportを知らない)）。この区別はパッケージ単位の本表では表現できないモジュール単位の規律であり、[`dependency-rule.md`](dependency-rule.md)の注記を参照。`document/`〜`validators/`行の`pipeline/`（`PipelineContext`型のみ）は、実行ロジックへの依存ではなく型シグネチャ上の参照であることに注意（上記「`PipelineContext`型依存について」参照）。`cli/`行の`services/`・`fetch/`・`ftp/`はPhase7 Task17-1/17-4で`cli/bootstrap.py`へ配線され、依存先に含まれる（`services/`は`cli/`を依存禁止に含んだままであり、逆方向の依存は生じていない）。`config/`はPhase6 Task14-5で実装済みとなり、`cli/`の依存先に含まれる。`features/`は`models/`・`learning/`・`utils/`に依存するが、実装済みのどのパッケージからも呼び出されていない（`pipeline/job_runner.py`からの統合は未実装、上記`features/`節参照）。

完全な依存グラフ（Mermaid）は[`dependency-rule.md`](dependency-rule.md)を参照。
