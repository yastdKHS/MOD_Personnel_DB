# Phase5 Task13-0 — 最終監査レポート

> 実施日: 2026-07-21。対象: リポジトリ全体（設計書・ADR・Architecture Contract・Dependency Rule・実装・テスト）。本レポートはコード変更・テスト変更を一切伴わない、読み取り専用の監査である。改善提案は含まない。

## Architecture Summary

[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) は **Guarantee 1〜15** を定義している（Guarantee 10〜15はADR-0032/0035/0037/0044/0045/0046により後から追加）。全15件を`src/mod_personnel_db/`の実コードと突き合わせた結果、**15件すべてが構造的に実装されている**。

| Guarantee | 内容（要約） | 検証結果 | 根拠 |
|---|---|---|---|
| 1 | Document AnalyzerはLayoutを知らない | 実装済み | `document/analyzer.py`は`layout`を一切importしない |
| 2 | Layout Detectorはfieldを知らない | 実装済み | `layout/detector.py`は`extractors`を一切importしない |
| 3 | Section Parserはknowledgeを知らない | 実装済み | `sections/parser.py`は`knowledge`を一切importしない |
| 4 | Field ExtractorはDBを知らない | 実装済み | `extractors/extractor.py`は`repositories`を一切importしない |
| 5 | Normalizerにドメイン正規表現がない | 実装済み | `normalizers/normalizer.py`に`re`のimport・使用が皆無 |
| 6 | Validatorは値を直さない | 実装済み | `ValidationResult`/`ValidationEvidence`（`models/validation.py`）に補正値フィールドなし |
| 7 | RepositoryがSQLiteを隠蔽する | 実装済み | 抽象`repositories/__init__.py`に`sqlite3`・SQL文字列が皆無 |
| 8 | Reviewのみが`gold_records`を更新できる | 実装済み（命名に軽微な乖離） | `add_version()`の呼び出しは`review/service.py`の`_promote_to_gold()`（`approve()`から呼ばれる）のみ。Contract文の「`promote_to_gold()`」という表記と実装のprivateメソッド名`_promote_to_gold()`が完全一致しない（書き込み経路の単一性という保証の実体は成立） |
| 9 | Reviewのみが`gold_records`へ書き込む | 実装済み | `export/service.py`は`GoldRepository`の読み取り専用メソッドのみ使用（`add_version`/`supersede`を呼ばない） |
| 10 | 各段階は自段階の出力型のみを生成する | 実装済み | `Document`/`LayoutArtifact`/`SectionParseResult`等、型ごとに生成元パッケージが1つに限定 |
| 11 | PDF本文アクセスはLayout Detectorが独占する | 実装済み | `pypdf`のimportは`document/`（メタデータ用）・`layout/`のみ。`sections/`〜`validators/`にはimportなし |
| 12 | Section ParserはPDFテキストをLayoutArtifact経由でのみ得る | 実装済み | `SectionParser.run(context, artifact: LayoutArtifact)`が唯一の入力 |
| 13 | PipelineRunnerはRepository/Knowledge/Learning/Review/Exportを知らない | 実装済み | `pipeline/runner.py`のimportは`models`と`pipeline.*`のみ |
| 14 | PipelineRunnerは集約Artifactを展開しない | 実装済み | `runner.py::run()`は`current: object`を不透明に扱う。`.sections`/`.records`の展開は`job_runner.py`側のみ |
| 15 | 依存生成責務はComposition Root（`cli/`）に一本化される | 実装済み | `Sqlite*Repository`/`FileKnowledgeService`/`RepositoryLearningService`/`RepositoryReviewService`/`RepositoryExportService`の生成箇所は`cli/bootstrap.py`のみ |

## ADR Summary

全46本のADR（0001〜0046）はすべて **Status: Accepted**。ステータスが`Superseded by ADR-XXXX`となっているADRは存在しない（ADR-0032内の「Superseded Design」節は同一ADR内でのVersion 1設計の不採用表明であり、他ADR全体を置き換えるものではない）。

**実装との整合（Consistent）**: 0001, 0002, 0004, 0006, 0009, 0013, 0014, 0017, 0021, 0025, 0027, 0030〜0040, 0042〜0046（StrEnum採用・PipelineMetrics確定・Document Analyzer責務再定義・pypdf/PyYAML採用・LayoutArtifact/FieldExtractionResult/NormalizationResult/ValidationResult確定・Python 3.13統一・PipelineRunner/JobRunner境界・JobRunner Coordinatorパターン・Composition Root DI契約を含む、実装契約に踏み込んだADRはすべて実コードと一致）。

**部分的に実装（Partially implemented）**:
- ADR-0003・0005（Layout/Knowledgeの外部データ化）: `layout/definitions.py`・`knowledge/loader.py`はハードコードのないYAML汎用エンジンとして実装済みだが、`layouts/`・`knowledge/`配下は依然README以外のデータファイルを持たない
- ADR-0010（CI/CD戦略）: `ci.yml`は稼働しているが、コメント文言・`.github/workflows/README.md`が「src/に実装コードがまだ存在しない」という当時の前提のまま更新されていない
- ADR-0011（中核6段階固定）: 6パッケージ（document/layout/sections/extractors/normalizers/validators）は存在するが、`PipelineStageName`（`models/enums.py`）は5値（Document Analyzerを含まない）。これはADR-0032による正当な再定義であり矛盾ではないが、ADR-0011単体を読む読者には伝わりにくい
- ADR-0015（SQLiteスキーマ確定）: 12業務テーブルは`_schema.py`に完全一致するが、`docs/database/schema.md`が言及する`schema_migrations`管理テーブルは未実装（`apply_schema()`は単発DDL適用のみ）
- ADR-0018・0023（PDF Registry・Parserバージョニング）: テーブル・FK構造は一致するが、保持ポリシーの運用処理・CIでのタグ起点自動バージョニングは未実装

**未実装（Not yet implemented）**:
- ADR-0007（Golden File Testing）: `tests/golden/`ディレクトリ自体が存在せず、`sample_pdfs/`・`sample_outputs/`もREADMEのみ
- ADR-0016（公開JSON形式）: `PersonnelRecord`相当のJSON組み立て・confidence/provenance導出コードが`src/`に見当たらない（`export/service.py`は`GoldRecord`をそのまま返すのみ）
- ADR-0019（Workflow Orchestration・cron実行）: `.github/workflows/`は`ci.yml`のみで、スケジュール実行ワークフローは未追加
- ADR-0022（Export Policy・CSV/Parquet変換）: JSON中心の`ExportRecord`のみで、CSV/Parquet変換ロジックは未実装
- ADR-0026（セキュリティポリシー）: gitleaksはpre-commitに導入済みだが、依存脆弱性スキャン（pip-audit等）が`ci.yml`に存在しない
- ADR-0028（Pydantic Settings採用）: `pydantic`/`pydantic-settings`への依存が`pyproject.toml`になく、`config/`パッケージ自体が存在しない
- ADR-0029（Export完全性・監査ログ方針）: 署名・チェックサム・監査ログ配線が`export/service.py`にない。GITHUB_TOKENの明示的最小権限設定も`ci.yml`にない

**ADR間の矛盾**: 検出なし。ADR-0041（Validatorコンストラクタ、RuleEngineなし）とADR-0043（RuleEngine追加）は一見矛盾に見えるが、ADR-0043は0041を正当に改訂したものであり、実コードは最新のADR-0043に一致している（矛盾ではなく正常な改訂関係）。

## Dependency Summary

[`docs/api/dependency-rule.md`](../api/dependency-rule.md)が定める依存方向を、`src/mod_personnel_db/`内の実際のimportとつき合わせた。

**一致**: `models/`（`utils/`のみ）、`repositories/`（抽象、`models/`のみ）、`repositories/sqlite/`（`sqlite3`はこの配下のみに限定）、`knowledge/`・`learning/`・`review/`・`export/`（それぞれ文書どおりの依存）、`pipeline/runner.py`（`repositories`/`knowledge`/`learning`/`review`/`export`への依存なし）、`cli/`（Composition Rootとして全体を束ねる）。

**未文書化の依存（1件）**: `document/`・`layout/`・`sections/`・`extractors/`・`normalizers/`・`validators/`の6パッケージは、いずれも`from mod_personnel_db.pipeline import PipelineContext`をimportしている。しかし`dependency-rule.md`のMermaid図・依存表、および`docs/api/package-design.md`のこれら6パッケージの「依存先: `models/`, `utils/`のみ」という記述には、この`pipeline/`への依存が一切記載されていない。これは`docs/api/pipeline.md`が定める`PipelineStage.run(self, context: PipelineContext, input: TIn) -> TOut`というProtocol設計上、各Stage実装が`PipelineContext`型を参照する以上避けられない構造的帰結であり、`pipeline/__init__.py`が`job_runner.py`や6段階パッケージ自体をimportしないため実行時の循環importは発生しない。ただし、文書上の一方向依存グラフ（`pipeline/ → document/`等の一方向のみ）とは異なる、逆方向の型依存が実在する。

**未実装パッケージに関する依存の空文化**: `dependency-rule.md`・`package-design.md`が言及する`config/`・`features/`・`ftp/`・`fetch/`・`services/`は`src/mod_personnel_db/`配下に存在しないため、これらを起点/終点とする依存エッジ（`cli/ → services/`等）は「違反」ではなく「実現されていない」状態である。

## Package Summary

`docs/api/package-design.md`記載の各パッケージの責務・公開APIを`__init__.py`の実際のexportと突き合わせた。

**一致**: `document/`, `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`, `knowledge/`, `learning/`, `pipeline/`（`JobRunner`は意図的に`pipeline/__init__.py`で再exportしない設計、循環import回避のため）, `cli/`。

**乖離（自己申告あり）**: `review/`・`export/`の各`__init__.py`docstringは、自身が`docs/api/review.md`／`package-design.md`が描く本来の広い契約（`CandidateRepository`/`ReviewRepository`利用、CSV/Parquet変換、JSON Schema検証等を含む）ではなく、Phase4 Task12-0/12-1で意図的に確定した狭い契約（`LearningRepository`+`GoldRepository`のみに基づくLearning Dataset固有のレビュー／Gold読み出し専用のExport）であることを明記しており、整合の再検討は将来のADRに委ねられている（この差異はTask12-0/12-1のReview Reportで既に透明化済み）。

**乖離（未実装）**: `repositories/__init__.py`は`UnitOfWork`を定義しない（`package-design.md`の`repositories/`節本文は依然`UnitOfWork`に言及しており記述が古い。ただし`JobRunner`が`UnitOfWork`を使わないという後続の設計判断＝ADR-0046と整合するため、実装自体に問題はない）。`config/`・`features/`・`ftp/`・`fetch/`・`services/`は`package-design.md`に記載があるが`src/`には存在しない。`cli/bootstrap.py`は`config/`の代わりにcli内のローカル`CompositionSettings`データクラスで設定を保持し、`services/`層を介さず`pipeline/`・`review/`・`export/`を直接呼び出している。

## Protocol Summary

以下すべてについて、唯一の具象実装であることを確認した（複数具象・重複実装は検出されず）。

| Protocol | 定義場所 | 具象実装 | 件数 |
|---|---|---|---|
| `CandidateRepository` | `repositories/__init__.py` | `SqliteCandidateRepository`（`repositories/sqlite/candidate.py`） | 1 |
| `GoldRepository` | 同上 | `SqliteGoldRepository`（`repositories/sqlite/gold.py`） | 1 |
| `KnowledgeRepository` | 同上 | `SqliteKnowledgeRepository`（`repositories/sqlite/knowledge.py`） | 1 |
| `LearningRepository` | 同上 | `SqliteLearningRepository`（`repositories/sqlite/learning.py`） | 1 |
| `PDFRepository` | 同上 | `SqlitePdfRepository`（`repositories/sqlite/pdf.py`） | 1 |
| `JobRepository` | 同上 | `SqliteJobRepository`（`repositories/sqlite/job.py`） | 1 |
| `ExportRepository` | 同上 | `SqliteExportRepository`（`repositories/sqlite/export.py`） | 1 |
| `ReviewRepository` | 同上 | `SqliteReviewRepository`（`repositories/sqlite/review.py`） | 1 |
| `KnowledgeService` | `knowledge/__init__.py` | `FileKnowledgeService`（`knowledge/service.py`） | 1 |
| `LearningService` | `learning/__init__.py` | `RepositoryLearningService`（`learning/service.py`） | 1 |
| `ReviewService` | `review/__init__.py` | `RepositoryReviewService`（`review/service.py`） | 1 |
| `ExportService` | `export/__init__.py` | `RepositoryExportService`（`export/service.py`） | 1 |

## Composition Root Summary

`Sqlite*Repository`（8種）・`FileKnowledgeService`・`RepositoryLearningService`・`RepositoryReviewService`・`RepositoryExportService`のインスタンス生成箇所を`src/mod_personnel_db/`全体でgrep検索した結果、**すべて`src/mod_personnel_db/cli/bootstrap.py`内**（`build_sqlite_repositories`/`build_knowledge_service`/`build_learning_service`/`build_review_service`/`build_export_service`/`build_application`）に限定されていることを確認した。他のいかなるパッケージ（`pipeline/`, `review/`, `export/`, `cli/app.py`, `cli/commands.py`含む）にも具象生成は存在しない。生成順序（Repository具象生成 → KnowledgeService生成 → LearningService生成 → ReviewService生成 → ExportService生成 → CandidateRepository生成 → JobRunnerRepositories生成 → JobRunner生成）は`bootstrap.py`内で固定されている。

## CLI Summary

公開コマンド一覧（`cli/app.py`の`COMMANDS`）: `init-db`, `run-pending`, `run-job`, `version`, `review`（`list`/`start`/`approve`/`reject`）, `export`（`all`/`person`/`since`）, `help`。

依存方向: `cli/app.py` → `cli/commands.py` → `cli/bootstrap.build_application()`/`build_job_runner()` → `Application`の公開メンバ（`job_runner`/`review_service`/`export_service`/限定的な`read_*`メソッド）。`app.py`・`commands.py`のimport文をgrep検証した結果、`repositories`・`knowledge`・`learning`・`review`・`export`各パッケージへの直接importは0件であり、Composition Root経由の利用のみであることを確認した。

## Test Summary

- **Unit**: `tests/unit/`配下に53ファイル。対象パッケージ: `cli`, `document`, `export`, `extractors`, `knowledge`, `layout`, `learning`, `models`, `normalizers`, `pipeline`, `repositories`, `review`, `sections`, `validators`。
- **Integration**: `tests/integration/`配下に1ファイル（`tests/integration/cli/test_cli_e2e.py`、Phase4 Task12-4で追加）。実際のComposition Rootを`app.main()`経由でend-to-end駆動する9シナリオ（init-db／run-pending／review list・start・approve・reject／export all・person・since）。
- **Golden**: `tests/golden/`は未作成（ADR-0007の戦略は文書化済みだが、`sample_pdfs/`・`sample_outputs/`にサンプルデータが存在しないため実行不可能な状態。`tests/README.md`自身が「未整備」と明記）。
- **Coverage**: `poetry run pytest --cov` — **528 passed**、TOTAL coverage **98.91%**（`pyproject.toml`の`fail_under = 80`を大きく上回る）。
- **静的検証**: `poetry run mypy --strict src/ tests/` → `Success: no issues found in 172 source files`。`poetry run ruff check src/ tests/` → `All checks passed!`。

## Remaining Known Limitations

1. `tests/golden/`・`sample_pdfs/`・`sample_outputs/`に実データが存在せず、ADR-0007のGolden Test戦略は文書化のみで未実行状態。
2. `layouts/`・`knowledge/`配下はREADMEのみで、実際の`era_id`マニフェスト・knowledge YAMLエントリが存在しない。パイプラインを実データでend-to-endに検証できない状態。
3. ADR-0016が定める公開JSON契約（`PersonnelRecord`相当の組み立て・confidence/provenance導出）を実装するコードが未発見（`export/service.py`は`GoldRecord`をそのまま返すのみ）。
4. ADR-0022のCSV/Parquetエクスポート、ADR-0029の完全性保証（署名・チェックサム）・監査ログが未実装。
5. ADR-0028のPydantic Settings採用が未実装（`config/`パッケージ自体が存在せず、`cli/bootstrap.py`内のローカル`CompositionSettings`データクラスで代替）。
6. `package-design.md`/`dependency-rule.md`が記述する`features/`・`ftp/`・`fetch/`・`services/`パッケージが未実装。`cli/`は`services/`層を介さず`pipeline/`・`review/`・`export/`を直接呼び出している。
7. ADR-0019のcronスケジュール実行ワークフロー、および将来予定の`release.yml`が未実装（`ci.yml`のみ存在）。
8. ADR-0026が求める依存脆弱性スキャン（pip-audit等）が`ci.yml`に存在しない。ADR-0029が求めるGITHUB_TOKEN明示的最小権限設定も未設定。
9. `review/`・`export/`パッケージは、Phase4 Task12-0/12-1で確定した狭い契約（`docs/api/review.md`等が描く本来の広い契約とは異なる）で実装されており、両パッケージの`__init__.py`docstringが自己申告済み。整合の再検討は将来のADRに委ねられている。
10. `document/`〜`validators/`の6パッケージが`pipeline.PipelineContext`をimportする依存が、`dependency-rule.md`・`package-design.md`の依存先記述に反映されていない（`PipelineStage.run(context, ...)`というProtocol設計上避けられない構造的帰結であり、実行時の循環importは発生しないが、文書との不一致は存在する）。
11. `repositories/__init__.py`に`UnitOfWork`が未定義（`package-design.md`の該当節本文は依然言及しており記述が古い。ADR-0046の設計自体には矛盾しない）。
12. Architecture Contract Guarantee 8の文言（`promote_to_gold()`）と実装のメソッド名（private `_promote_to_gold()`、`approve()`から呼び出し）が完全一致しない（書き込み経路単一性という保証の実体は成立）。
13. `.github/workflows/ci.yml`のコメント・`.github/workflows/README.md`・`docs/database/schema.md`冒頭に、「`src/`に実装コードがまだ存在しない」という初期フェーズ時点の記述が残存しており、現状（172ソースファイル・528テスト）と乖離している。
14. `models/enums.py`の`PipelineStageName`が5値（Document Analyzerを含まない）であり、ADR-0011の「6段階固定」という原文の字面とは異なる。ADR-0032による正当な再定義が根拠だが、ADR-0011単体からは読み取れない。
15. `docs/database/schema.md`が言及する`schema_migrations`管理テーブルが実際のDDL（`_schema.py`）に未実装。

## Final Assessment

Architecture Contractの全15 Guarantee、Dependency Ruleの大部分、Package Designの中核6段階・Repository/Knowledge/Learning/CLIパッケージ、Protocol単一具象実装の原則、Composition Root一本化、CLI公開APIの依存方向は、いずれも実コードによって裏付けられており、監査の結果**設計と実装の間に致命的な不整合は検出されなかった**。ADR間の矛盾も検出されず、後続ADRによる正当な改訂関係（0041→0043、0011→0032）はいずれも実装が最新のADRに追随している。

一方で、(a) `layouts/`・`knowledge/`・`sample_pdfs/`・`sample_outputs/`に実データが存在せずパイプラインの実データ検証ができない状態、(b) 公開JSON形式・エクスポート完全性・Pydantic Settings・`config/`/`features/`/`ftp/`/`fetch/`/`services/`パッケージなど、複数のAccepted ADR・設計文書が想定する機能が未実装、(c) 6段階パッケージから`pipeline/`への未文書化の型依存、(d) 一部の文書（CI関連README・schema.md冒頭・package-design.mdのrepositories/節）に実装進捗を反映していない古い記述が残存、という3種類の「設計と実装のギャップ」が確認された。これらはいずれも既存ADR・Architecture Contract・Dependency Ruleの**決定内容そのものへの違反ではなく**、実装がまだそこに到達していない、または文書更新が実装に追いついていない状態であり、`review/`・`export/`のように意図的なスコープ限定として当該パッケージ自身が自己申告しているものも含まれる。

Test Summaryの観点では、Unit Test層は53ファイル・98.91%カバレッジで堅牢に整備されている一方、Golden/Regression/Acceptance/Performance/Benchmark Testの各層（`docs/testing/test-policy.md`が定義する8種のうち5種）は依然未着手であり、Integration Testも現時点でCLI経路の1ファイルのみである。

以上より、**現時点の実装はConstitution → ADR → Architecture Contract → Implementation Guideという統治構造に忠実であり、検出された相違はいずれも「未実装」「文書の遅延更新」に分類される事実であって、無断でのルール逸脱や無許可のリファクタリングは確認されなかった**。
