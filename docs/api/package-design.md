# Package Design（`src/` パッケージ構成）

> **位置づけ**: 本ドキュメントは `src/mod_personnel_db/` 配下のパッケージ構成を定義する。個々のコンポーネントの公開APIは[`interfaces.md`](interfaces.md)、依存関係の許可/禁止ルールは[`dependency-rule.md`](dependency-rule.md)を参照。
>
> 本ドキュメントが定める構成は、[`src/README.md`](../../src/README.md)（初期設計時のラフスケッチ）を置き換える、より詳細な正式設計である。`src/README.md`は本ドキュメントへのポインタとして更新する。
>
> **実装状況（[`docs/reports/phase5-final-audit.md`](../reports/phase5-final-audit.md)、2026-07-21時点）**: 本ドキュメント作成時点では実装未着手だったが、現在は`config/`・`features/`・`ftp/`・`fetch/`・`services/`を除く全パッケージが実装済みである。各パッケージ節の冒頭に実装状況（実装済み／未実装）を明記する。未実装パッケージの節は、将来実装する際の設計目標として保持する（削除しない）。

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

### `config/`（**未実装**）

- **目的**: 実行環境ごとの設定（DB接続情報、ストレージパス、外部サービス認証情報の参照先）を一箇所に集約する。
- **責務**: 環境変数・設定ファイルの読み込みと、型付き設定オブジェクト（`Settings`。実装はPydantic Settings、[ADR-0028](../adr/0028-pydantic-settings-for-configuration.md)、詳細は[`docs/configuration.md`](../configuration.md)）への変換。どのRepository実装（SQLite/将来のPostgreSQL）を使うかは、`config/`は文字列・enum等の**値**として提供するに留まり、実際にその実装クラスを`import`して組み立てる**配線**は行わない（配線は`cli/`が合成ルートとして担う、下記および[`dependency-rule.md`](dependency-rule.md#合成ルートcomposition-root)参照）。
- **依存先**: `utils/`のみ。**例外なし。**
- **依存禁止**: `utils/`以外の全パッケージ（`models/`を含む）。`config/`は誰からも依存されるが、他のいかなるパッケージにも依存しない、依存関係グラフの絶対的な末端である。`repositories/sqlite/`への依存は持たない——これを`config/`に許すと`repositories/sqlite/ → config/ → repositories/sqlite/`という循環（[`import-graph.md`](import-graph.md)で検出・修正済み）を生むため、合成ルートの役割は`cli/`に一本化する。
- **現状**: `pydantic`/`pydantic-settings`は`pyproject.toml`に依存追加されておらず、`config/`パッケージ自体が`src/mod_personnel_db/`配下に存在しない。現在は`cli/bootstrap.py`内のローカルな`CompositionSettings`データクラス（`db_path`/`knowledge_root`/`layouts_root`/`parser_code_version`の4フィールド）が、本節が想定する設定値の一部を暫定的に代替している。ADR-0028自体は撤回されておらず、`config/`パッケージ化は今後の実装対象として残る。

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
- **依存先**: `repositories/`（実装するProtocol）、`models/`、`utils/`。**`config/`には依存しない**（`config/`が未実装のため。DB接続先は`connect(db_path: str)`のように呼び出し元＝合成ルートの`cli/`から単純な文字列として渡され、`repositories/sqlite/`自身が設定オブジェクトを参照することはない）。
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

### `features/`（FeatureStore、**未実装**）

- **目的**: `Confidence`算出等に用いる派生特徴量（`FeatureVector`）を計算・提供する。
- **責務**: `RawRecord`/`NormalizedRecord`等から特徴量（OCR品質シグナル、layout判定信頼度、過去の誤り発生率等）を計算する。**V2.0時点では永続ストレージを持たず、都度計算（on-demand）とする**（専用の`FeatureRepository`は[Task 3](repositories.md)の8リポジトリに含まれておらず、過剰設計を避けるため。将来キャッシュ性能が必要になった場合、非破壊的な拡張として`FeatureRepository`＋DBテーブルを追加検討する）。
- **依存先**: `models/`, `learning/`（過去の誤り発生率等の特徴量計算に`LearningService`の集計結果を使うため）, `utils/`。
- **依存禁止**: `document/`〜`validators/`（中核パイプラインへの逆依存はしない）, `repositories/`（直接のDB永続化を持たないため）。
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

### `ftp/`（FTPService、**未実装**）

- **目的**: FTP/SFTP経由でのファイル配信・取得（既存の配布慣行がある場合の代替搬送路）。
- **責務**: `export/`が生成した成果物のFTPアップロード、または将来的な取得元がFTPを要求する場合のダウンロード。
- **依存先**: `utils/`のみ。
- **依存禁止**: `repositories/`, `models/`のドメインモデルへの依存はしない（バイト列・パス文字列のみを扱う、プロトコル層に徹する）。`export/`・`fetch/`から呼び出される側であり、逆方向の依存はしない。

### `fetch/`（**未実装**）

- **目的**: 発令PDFを取得する（中核パイプラインの外側、[ADR-0006](../adr/0006-pipeline-provenance.md)）。
- **責務**: HTTPまたは`ftp/`経由でPDFを取得し、`PDFRepository`に記録する。
- **依存先**: `models/`, `repositories/`（抽象、`PDFRepository`）, `ftp/`, `utils/`。
- **依存禁止**: `document/`〜`validators/`（中核パイプラインへの依存はしない。取得と解析は独立したステージ）。

### `pipeline/`（**実装済み**）

- **目的**: 中核パイプライン6段階の実行を調整する。詳細は[`pipeline.md`](pipeline.md)。パッケージ内部は「`JobRunner` → `PipelineRunner` → `PipelineStage`」の層構造を持ち、両者の責務は分離されている（[ADR-0044](../adr/0044-pipelinerunner-jobrunner-boundary.md)）。
- **責務（`PipelineRunner`、`pipeline/runner.py`、実装済み）**: `PipelineContext`/`PipelineStage`/`PipelineResult`/`PipelineEvent`/`PipelineException`/`PipelineMetrics`の提供、および登録済み`PipelineStage`列の順次呼び出し（Artifact受け渡し・イベント記録）のみ。Stage生成（コンストラクタ注入）・`PipelineContext`生成・永続化は行わない。
- **責務（`JobRunner`、`pipeline/job_runner.py`、実装済み）**: `PipelineContext`生成、`KnowledgeSnapshot`/`ValidationRuleSet`取得によるStage生成（コンストラクタ注入）、`PipelineBuilder`経由での`PipelineRunner`への登録・呼び出し、`PipelineResult`のRepositoryへの永続化、Learning記録（[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md)）。加えて、集約Artifact（`SectionParseResult`/`FieldExtractionResult`/`NormalizationResult`）を反復処理し`PipelineRunner`を必要な回数呼び出すCoordinator責務を持つ（[ADR-0045](../adr/0045-job-runner-aggregate-artifact-coordinator.md)）。この展開は`PipelineRunner`側では行わない。
- **依存先（パッケージ全体、`JobRunner`が必要とする分を含む）**: `models/`, `repositories/`（抽象、`PDFRepository`, `CandidateRepository`, `JobRepository`）, `document/`, `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`, `knowledge/`, `learning/`, `utils/`。**ただし`PipelineRunner`自身のコードは`repositories/`, `knowledge/`, `learning/`のいずれにも依存しない**（[architecture-contract.md 保証13](../architecture/architecture-contract.md#13-pipelinerunnerはrepositoryknowledgelearningreviewexportを知らない)）。これらへの依存は`JobRunner`の責務としてのみ生じる。逆方向として、`document/`〜`validators/`の6パッケージ側から`pipeline/`（`PipelineContext`型のみ）への型依存がある（上記「`PipelineContext`型依存について」参照）。この逆方向の依存は`pipeline/__init__.py`が6段階パッケージ・`job_runner.py`をimportしないことで循環を回避しており、`pipeline/ → 6段階`という一方向の実行時依存構造そのものは維持される。
- **依存禁止**: `repositories/sqlite/`（具象）, `review/`, `export/`, `ftp/`（これらは中核パイプラインの外側であり、`pipeline/`から呼び出さない。実際の連携は`cli/`が合成ルートとして直接束ねる。下記`services/`の実装状況を参照）。

### `services/`（**未実装**）

- **目的**: 単一の中核パイプライン実行に閉じない、横断的な運用オーケストレーションを提供する。
- **責務**: `Scheduler`（[ADR-0019](../adr/0019-workflow-orchestration.md)、実行トリガーの決定）。将来、複数パッケージ（`pipeline/`, `review/`, `export/`）を束ねる上位のワークフローが必要になった場合もここに置く。
- **依存先**: `pipeline/`, `review/`, `export/`, `models/`, `utils/`。
- **依存禁止**: `repositories/sqlite/`（具象）, `document/`〜`validators/`（`pipeline/`を介さず中核パイプライン段階を直接呼び出さない）。
- **現状**: `src/mod_personnel_db/`配下に`services/`パッケージは存在しない。`cli/bootstrap.py`（合成ルート）が`services/`層を介さず`pipeline/`・`review/`・`export/`を直接呼び出す構成になっている（下記`cli/`参照）。

### `cli/`（**実装済み**）

- **目的**: 人間が操作するコマンドラインエントリポイント（[ADR-0021](../adr/0021-review-ui-strategy.md)のレビューCLI等）であり、かつ**アプリケーション全体の合成ルート（Composition Root）**を担う。他のいかなるパッケージ（`pipeline/`・`repositories/`を含む）も具象実装を生成しない（[ADR-0046](../adr/0046-composition-root-dependency-injection-contract.md)、[architecture-contract.md 保証15](../architecture/architecture-contract.md#15-依存生成責務はcomposition-rootcliに一本化される)）。
- **責務**: コマンドライン引数の解析、`review/`・`export/`等のAPI呼び出しに加え、起動時に`repositories/sqlite/`（将来は`repositories/postgres/`も）・`KnowledgeService`・`LearningService`・`ReviewService`・`ExportService`の具象実装を、Repository具象生成→`KnowledgeService`生成→`LearningService`生成→`ReviewService`生成→`ExportService`生成→`JobRunner`生成の順に構築する（ADR-0046）。`JobRunner`（`pipeline/job_runner.py`）へは`JobRunnerRepositories`・`KnowledgeService`・`LearningService`・`ParserVersionId`・`layout_definitions`を個別に注入する。`UnitOfWork`（未実装、上記`repositories/`節参照）は`JobRunner`へは注入しない（`JobRunner`が必要とするRepositoryは`pdfs`/`jobs`/`candidates`の3種のみであり、複数Repositoryにまたがる原子性が必要な操作を現時点で行わないため）。パイプライン実行（`run-pending`/`run-job`）・Review（`review list`/`start`/`approve`/`reject`）・Export（`export all`/`person`/`since`）は、それぞれ独立したCLIサブコマンドとして提供し、`cli/`がこれらを1プロセス内で自動的に直列実行することはない。
- **依存先**: `review/`, `export/`, `pipeline/`, `models/`, **`repositories/sqlite/`（合成ルートとしての唯一の例外、[`dependency-rule.md`](dependency-rule.md#合成ルートcomposition-root)）**, `knowledge/`, `learning/`, `layout/`（`layouts/<era_id>/manifest.yaml`の読み込みに`layout.definitions.load_layout_definitions`を利用するため）。**`services/`・`config/`は未実装のため現時点では依存しない**（`services/`が実装された場合、`cli/`はその配下の`pipeline/`・`review/`・`export/`直接呼び出しを`services/`経由に置き換えることを検討する）。
- **依存禁止**: `document/`〜`validators/`（`layout/`を除き直接は呼ばない、`pipeline/`経由）。`repositories/sqlite/`への依存は`cli/`にのみ許される例外であり、他のいかなるパッケージにも拡大しない。

---

## パッケージ横断の依存先サマリ表

| パッケージ | 実装状況 | 依存してよい | 依存してはならない（代表例） |
|---|---|---|---|
| `config/` | 未実装 | `utils/` | ビジネスロジック全般、`repositories/sqlite/`（合成の配線は`cli/`が担う。`config/`自身が担うと循環参照を生むため） |
| `utils/` | 実装済み | （なし） | プロジェクト内の全パッケージ |
| `models/` | 実装済み | `utils/` | ビジネスロジック全般、`repositories/` |
| `repositories/` | 実装済み | `models/` | `sqlite3`等の具体DBドライバ、`config/` |
| `repositories/sqlite/` | 実装済み | `repositories/`, `models/`, `utils/`（`config/`は未実装のため依存しない） | 中核パイプライン6段階、サービス層 |
| `document/`〜`validators/` | 実装済み | `models/`, `utils/`, `pipeline/`（`PipelineContext`型のみ） | `repositories/`（抽象含む）, `knowledge/`, 他段階間の直接依存 |
| `knowledge/` | 実装済み | `models/`, `utils/` | 中核パイプライン6段階, `repositories/`（抽象含む）, `repositories/sqlite/` |
| `learning/` | 実装済み | `models/`, `repositories/`（抽象）, `utils/` | 中核パイプライン6段階, `repositories/sqlite/` |
| `features/` | 未実装 | `models/`, `learning/`, `utils/` | 中核パイプライン6段階, `repositories/` |
| `review/` | 実装済み（限定スコープ） | `models/`, `repositories/`（抽象、`LearningRepository`, `GoldRepository`のみ）, `learning/`, `utils/` | 中核パイプライン6段階, `repositories/sqlite/`, `knowledge/` |
| `export/` | 実装済み（限定スコープ） | `models/`, `repositories/`（抽象、`GoldRepository`のみ）, `utils/` | 中核パイプライン6段階, `repositories/sqlite/` |
| `ftp/` | 未実装 | `utils/` | `repositories/`, `models/` |
| `fetch/` | 未実装 | `models/`, `repositories/`（抽象）, `ftp/`, `utils/` | 中核パイプライン6段階 |
| `pipeline/`（パッケージ全体・`JobRunner`分を含む） | 実装済み | `models/`, `repositories/`（抽象）, 中核パイプライン6段階, `knowledge/`, `learning/`, `utils/` | `repositories/sqlite/`, `review/`, `export/`, `ftp/` |
| `services/` | 未実装 | `pipeline/`, `review/`, `export/`, `models/`, `utils/` | `repositories/sqlite/`, 中核パイプライン6段階（直接） |
| `cli/` | 実装済み | `review/`, `export/`, `pipeline/`, `models/`, `knowledge/`, `learning/`, `layout/`, `repositories/sqlite/`（合成ルートとしての例外） | 中核パイプライン6段階（直接、`layout/`を除く） |

上記`pipeline/`行はパッケージ全体（`JobRunner`が必要とする依存を含む）のサマリである。`PipelineRunner`（`pipeline/runner.py`）自身は`repositories/`, `knowledge/`, `learning/`のいずれにも依存しない（[ADR-0044](../adr/0044-pipelinerunner-jobrunner-boundary.md)、[architecture-contract.md 保証13](../architecture/architecture-contract.md#13-pipelinerunnerはrepositoryknowledgelearningreviewexportを知らない)）。この区別はパッケージ単位の本表では表現できないモジュール単位の規律であり、[`dependency-rule.md`](dependency-rule.md)の注記を参照。`document/`〜`validators/`行の`pipeline/`（`PipelineContext`型のみ）は、実行ロジックへの依存ではなく型シグネチャ上の参照であることに注意（上記「`PipelineContext`型依存について」参照）。`cli/`行の`services/`・`config/`は、両パッケージが未実装のため現時点では依存先に含まれない（実装後は`cli/`の直接依存の一部を置き換える想定）。

完全な依存グラフ（Mermaid）は[`dependency-rule.md`](dependency-rule.md)を参照。
