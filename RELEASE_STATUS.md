# RELEASE_STATUS

> 本ファイルはv1.0.0 Release Candidateとしてのリリース判定を記録する。ソースコード・テストの実装は一切含まない、読み取り専用の判定記録である。判定根拠はPhase6 Task15-0の最終監査（読み取り専用で実施、レポートファイルは作成していない）、[`CHANGELOG.md`](CHANGELOG.md)のPhase6節が記録するTask15-1のDocument Drift是正結果、[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)（Task17-5、Phase7 CLI統合完了後の最終監査）、および[`docs/reports/phase8-release-validation.md`](docs/reports/phase8-release-validation.md)（Task18-7、Production Release Validation、GitHub Actions実行履歴・実CLI実行による実測検証）に基づく。

## Version

`v1.0.0`（未タグ付け、候補版）。`pyproject.toml`の`version`は引き続き`0.0.0`のまま（[ADR-0001](docs/adr/0001-python-packaging.md)、実装着手時のバージョン運用は[ADR-0023](docs/adr/0023-parser-versioning-policy.md)のSemVer規則に従う）。タグ運用の詳細はREADMEの「[リリースタグ運用](README.md#リリースタグ運用)」を参照。

## Date

2026-07-22（Phase6 Task15-4作成時点）。2026-07-24、Task17-5（Phase7最終監査・CLI統合完了後のドキュメント同期）・Task17-6（Phase7 Closeout）で更新。2026-07-25、Task18-1（`FtpSettings`導入）・Task18-3〜18-5（GitHub Actions Scheduler統合）・Task18-6（Production FTP運用整備）・Task18-7（Production Release Validation、[`docs/reports/phase8-release-validation.md`](docs/reports/phase8-release-validation.md)）・Task18-7追記（運用担当者による実Production FTPサーバへの手動接続確認、`remote_directory`未配線の発見。続報でフルパス指定によるアップロード成功も確認）・Task18-8/18-9（`remote_directory`の`ftp/`実装・Composition Root配線）・Task18-10（デッドコンフィグ記述をドキュメントから解消）で更新。2026-07-25〜26、Task18-17（SQLite永続化Phase1、`download-db`/`upload-db`CLIコマンド追加）・Task19-5（`upload()`のatomic化・DB `integrity_check`追加）・Task19-15（既存ファイル確認方式を`NLST`から`SIZE`へ変更、ATSON FTPd v0.9.14.9の実挙動に対応）・Task19-17（既存`.bak`を`DELE`してから`rename`する対応、同サーバの`RNTO`拒否への対応）・Task19-20（運用ドキュメントの追従）で更新。2026-07-26、Task19-21（本ファイルの最新化）で更新。2026-07-26、Task20-7（Task20-1〜20-6のSQLiteレビュー結果をKnown Limitationsへ反映、ドキュメントのみの変更）で更新。2026-07-27、Task21-8（Task21-1〜21-7のSQLite Connection管理改善〔一本化・close責務整理・最終レビュー〕完了をKnown Limitations項目22へ反映、`version_command`のみが残課題である旨を明記、ドキュメントのみの変更）で更新。2026-07-27、Task21-9（Known Limitations項目22を現状のみの記載へ整理し、Task21-1〜21-7の経緯説明とTask21-6/21-7レビューで整理した将来改善候補を新設の「Technical Debt（Future Refactoring Candidates）」節へ分離、ドキュメントのみの変更）で更新。

## Current Status

**v1.0.0 Release Candidate（Phase7完了、CLI統合済み）**。Phase6 Task15-0で実施した最終監査（Architecture Contract全15 Guarantee・ADR全46本・Dependency Rule・Package Design・Protocol・Composition Root・Workflow・Testの整合性監査、読み取り専用）の結果、設計と実装の間に致命的な不整合は検出されなかった。Task15-1でDocument Drift（`config/`実装状況・`ExportService`実装状況注記・Golden Test配置説明の3件）を是正済み。Task15-2でREADME/CHANGELOGのバージョン整合・既知の制限事項の反映・docs索引の到達性確保・`release.yml`との整合を実施済み。Phase7（Task16-1〜16-4）で`ftp/`・`features/`・`fetch/`・`services/`の4パッケージを実装し、Task16-5の最終監査（読み取り専用）でArchitecture Contract・Dependency Ruleとの矛盾がないことを確認した。続くTask17-0〜17-4で、`ftp/`・`fetch/`・`services/`（`JobOrchestrator`・`Scheduler`）をComposition Root（`cli/`）へ配線し、`fetch-stage`/`run-workflow`/`schedule-now`/`list-schedule`の4コマンドとしてCLIから利用可能にした。Task17-5の最終監査（[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)）で、循環依存が存在しないこと・Composition Rootが唯一であること・`Scheduler`が`JobOrchestrator`のみに依存すること・CLIがProtocol経由のみ利用していること・`JobOrchestrator`の直接利用箇所が存在しないことを確認した。`features/`のみ、実装済みだが`JobRunner`への統合が未実装のため未接続のパッケージとして残る（詳細はKnown Limitations参照）。Task17-6でPhase7を正式に**Completed**としてクローズした（下記Completed Phases参照）。本Closeoutはドキュメント上の整理のみであり、v1.0.0 Release CandidateとしてのRelease Decisionは変更しない（下記参照）。続くPhase8では、Task18-0で実装設計（[`docs/phase8-integration-design.md`](docs/phase8-integration-design.md)）を確定した後、Task18-1で`FtpSettings`（`config/ftp.py`）を実装し、Task18-3〜18-5でGitHub Actions（`.github/workflows/scheduler.yml`）による`schedule-now run_pending_pipeline`のcron自動実行を追加し、Task18-6で対応するFTP Secretsの整備・運用手順文書化（[`docs/operations/release.md`](docs/operations/release.md#production-ftp運用)）を行った。Phase8は継続中であり、本Release DecisionはPhase7完了時点の判定を維持する。Task18-7では、GitHub Actions API（実行履歴）・実CLI実行（スクラッチDB）を用いたProduction Release Validationを実施した（[`docs/reports/phase8-release-validation.md`](docs/reports/phase8-release-validation.md)）。その結果、`scheduler.yml`・`release.yml`はいずれも実行履歴ゼロ（Actions API確認）であり、実FTPサーバへの接続実績・GitHub Secretsの実登録状況は本セッションからは確認できないことが判明した（いずれも「未確認」であり「失敗」ではない）。この監査結果に基づき、Production Ready判定は**Release Candidate maintained**とした（下記Release Decision・Release Recommendation参照）。Task18-7の実地検証で判明した「`remote_directory`が実行時に一切参照されないデッドコンフィグ」問題は、Task18-8（`ftp/`パッケージへの`cwd()`実装）・Task18-9（`cli/bootstrap.py`のComposition Root配線）で解消し、Task18-10で関連ドキュメント（本ファイル・[`docs/reports/phase8-release-validation.md`](docs/reports/phase8-release-validation.md)・[`docs/operations/release.md`](docs/operations/release.md)）を実装完了状態へ更新した。その後Task18-17でSQLite永続化Phase1（`download-db`/`upload-db`CLIコマンド、`scheduler.yml`への統合）を実装し、GitHub Actions実行履歴（Actions API）で実際に3ステップ（Download DB from FTP → schedule-now → Upload DB to FTP）が成功していることを確認した（Task18-22）。運用開始後、実FTPサーバ上で発生した実際のエラー（空文字列の`remote_path`、`500 Invalid argument`）の調査（Task18-18〜18-21）を経て、Task19ではアップロード処理の安全性向上に着手した。Task19-5で`upload()`のatomic化（一時ファイル経由の転送・backup退避）とアップロード前DB `integrity_check`を実装し、Task19-13・Task19-16の実FTP検証（ATSON FTPd v0.9.14.9）により判明した同サーバ固有の制約（単一ファイル存在確認への`NLST`使用が`426`で失敗すること、既存ファイルへの`RNTO`が`553 already exist`で失敗すること）に対応するため、Task19-15で存在確認方式を`SIZE`へ、Task19-17でbackup更新処理を`DELE`後`rename`へ変更した。Task19-20で運用ドキュメント（本README・`docs/operations/release.md`）をこれらの変更へ追従させた。**atomic upload手順全体（`DELE`→`rename`→`rename`）をATSON FTPd v0.9.14.9上でend-to-endに実行して確認する検証（Task19-18）は、実FTP認証情報がセッションになかったため未実施のまま残っている**（下記Known Limitations参照）。

## Release Decision

**Production Ready判定: Release Candidate maintained**（Task18-7、[`docs/reports/phase8-release-validation.md`](docs/reports/phase8-release-validation.md)の3択判定基準「Ready for v1.0.0 Release」「Release Candidate maintained」「Not Ready」のうち中位を選択）。「Not Ready（v1.0.0としての完全な本番リリースには未達）」であるが、実装済み範囲（中核パイプライン・Gold Database・Review・Export・CLI・CI/CD、および今回CLI統合が完了した`fetch/`・`ftp/`・`services/`）に限定したRelease Candidateとしては、構造的な不整合なく到達している。

判定根拠は「Known Limitations」節および「Release Recommendation」節、詳細な実測結果は[`docs/reports/phase8-release-validation.md`](docs/reports/phase8-release-validation.md)を参照。

## Completed Phases

| Phase | 内容 | 状態 |
|---|---|---|
| Phase1 | 設計フェーズ（リポジトリ構造・ADR・データモデル・API/Interface設計・Review Domain・運用設計の確定、[`docs/design-freeze.md`](docs/design-freeze.md)） | 完了 |
| Phase2 | 中核パイプライン6段階（Document Analyzer〜Validator）・Repository層・ドメインモデルの実装 | 完了 |
| Phase3 | JobRunner（Coordinator）・Composition Root（`cli/bootstrap.py`）・CLI Entry Pointの実装 | 完了 |
| Phase4 | ReviewService/ExportService実装、`review`/`export`サブコマンド追加、CLI E2E統合テスト追加 | 完了 |
| Phase5 | 全体最終監査（[`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md)）・ドキュメント同期・リリース準備 | 完了 |
| Phase6 | 公開JSON契約（Task14-2）・CSV/Parquetエクスポート（Task14-3）・Export完全性保証（Task14-4）・Pydantic Settings採用（Task14-5）・GitHub Actions Workflow Orchestration（Task14-6）の実装、Golden Test自動化（Task14-0/14-1）、v1.0.0 Release Candidateとしての最終監査（Task15-0）・Document Drift是正（Task15-1）・最終ドキュメント整備（Task15-2）・本リリース判定（Task15-4） | 完了 |
| Phase7 | `features/`・`fetch/`・`ftp/`・`services/`の設計方針確定・依存方向明文化・実装ロードマップ作成（Task16-0、[`docs/phase7-implementation-roadmap.md`](docs/phase7-implementation-roadmap.md)）、4パッケージの実装（Task16-1〜16-4）・最終監査（Task16-5、読み取り専用）・ドキュメント同期（Task16-6）、Composition Root統合設計（Task17-0、[`docs/phase7-integration-design.md`](docs/phase7-integration-design.md)）、`fetch/`・`ftp/`・`JobOrchestrator`のComposition Root配線（Task17-1）、CLIサブコマンド化`fetch-stage`/`run-workflow`（Task17-2）、`Scheduler`実装（Task17-3、`services/scheduler.py`）、CLIサブコマンド化`schedule-now`/`list-schedule`（Task17-4）、Phase7最終監査・ドキュメント同期（Task17-5、[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)）、Phase7 Closeout（Task17-6、`CHANGELOG.md`追記・本ファイルのPhase7 Completed化）。`features/`の`JobRunner`への統合のみ未着手のまま残る。 | **Completed** |

## Architecture Contract

[`docs/architecture/architecture-contract.md`](docs/architecture/architecture-contract.md)が定める**Guarantee 1〜15**全件を再監査した（Task15-0、Phase7完了後はTask17-5で再確認）。**15件すべてが構造的に維持されている**。Phase6で変更された`export/`・`config/`・`cli/bootstrap.py`についても、Guarantee 7（RepositoryがSQLiteを隠蔽）・8/9（Reviewのみがgold_recordsを書き換える）・15（依存生成責務はComposition Rootに一本化）を個別に再確認し、いずれも維持されていることを確認した（`export/`の新規モジュールは`GoldRepository.add_version()`/`supersede()`を一切呼び出さない、`AppSettings`の生成は`cli/bootstrap.py`の`build_settings()`一箇所に限定される）。Task17-5では、Guarantee 15の対象を`HTTPFetchClient`・`StandardFTPClient`・`DefaultJobOrchestrator`・`DefaultScheduler`（Phase7で追加された4つの具象実装）にも実務上拡張し、これらが`cli/bootstrap.py`以外のいかなる箇所からも生成されないことをAST検証（`tests/unit/cli/test_bootstrap.py`）で確認した。ただしGuarantee 15の**文面**（`architecture-contract.md`本文）自体は`repositories/sqlite/`・`KnowledgeService`・`LearningService`のみを列挙しており、この拡張を明記していない（本Taskでは`docs/architecture/`配下の変更は禁止されているため未修正、詳細は[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)を参照）。

## ADR Status

全46本（ADR-0001〜0046）は依然すべて`Status: Accepted`。Superseded・本文変更は検出されなかった。ADR間の矛盾も検出されていない（ADR-0041→ADR-0043は正当な改訂関係であり矛盾ではない）。

| 分類 | ADR | 件数 |
|---|---|---|
| 実装済み（実コードと一致） | 0001, 0002, 0004, 0006, 0007, 0009, 0013, 0014, 0016, 0017, 0019, 0021, 0022, 0025, 0027, 0028, 0030〜0040, 0042〜0046 | 32 |
| 部分実装 | 0003・0005（Layout/Knowledge外部データ化、エンジンは実装済みだが実データは最小限）, 0010（CI/CD戦略、3ワークフロー稼働）, 0011（6段階固定、`PipelineStageName`は5値）, 0015（スキーマ確定、`schema_migrations`未実装）, 0018・0023（PDF Registry・Parserバージョニング、運用処理未実装）, 0029（Export完全性・監査ログ、SHA-256のみ実装で署名等は未実装） | 8 |
| 未実装 | 0026（セキュリティポリシー、依存脆弱性スキャン未導入） | 1 |
| その他（方針・プロセス文書、コード実装の対象外） | 0008, 0012, 0020, 0024, 0041 | 5 |

（32+8+1+5=46で実ADR総数と一致する。「実装済み」欄の「0030〜0040」は11本、「0042〜0046」は5本の展開である。）

## Test Summary

- **Unit**: `tests/unit/`配下（`cli`, `config`, `document`, `export`, `extractors`, `features`, `fetch`, `ftp`, `knowledge`, `layout`, `learning`, `models`, `normalizers`, `pipeline`, `repositories`, `review`, `sections`, `services`, `validators`）。Phase7で`features`/`fetch`/`ftp`/`services`（`Scheduler`を含む）が追加された。
- **Integration**: `tests/integration/`配下（`cli/`（`test_cli_e2e.py`・`test_phase7_cli_workflow.py`・`test_phase7_integration.py`・`test_phase7_scheduler_cli.py`）, `config/test_settings_integration.py`, `export/test_export_personnel_records.py`, `export/test_export_csv_parquet.py`, `export/test_export_with_metadata.py`, `golden/test_golden.py`, `services/test_scheduler_integration.py`等）。Phase7でCLI・servicesの結合テストが追加された。
- **Golden**: [`tests/integration/golden/test_golden.py`](tests/integration/golden/test_golden.py)（Phase6 Task14-1）が実装済み。フィクスチャは`tests/golden/`に合成PDF・期待結果JSONを各1件配置（[ADR-0007](docs/adr/0007-golden-file-testing.md)）。
- **未着手のテスト層**: Regression / Performance / Acceptance / Benchmark / Mutation（[`docs/testing/test-policy.md`](docs/testing/test-policy.md)が定める8種のうち残り5種）。
- **実行結果**: `poetry run pytest --cov` → **875 passed**（0 failed、Phase6完了時点は634 passed、Phase7完了時点は816 passed、Task18-7時点は833 passed、Task18-9時点は838 passed、Task18-17時点は850 passed、Task19-5時点は864 passed、Task19-15時点は867 passed、Task19-17時点は875 passed。Task19-21完了報告時点で実測し確認）。

## Coverage

`poetry run pytest --cov` の TOTAL coverage は **98.96%**（Phase6完了時点は98.99%、Task18-9時点で98.99%、Task19-21完了報告時点で実測し98.96%とわずかに低下していることを確認。`pyproject.toml`の`[tool.coverage.report]`が定める閾値`fail_under = 80`は大きく上回る）。`ftp/client.py`（Task19-5/19-15/19-17でatomic upload・`SIZE`・`delete()`を追加）は100%カバレッジ。`cli/commands.py`は98%で、`_check_database_integrity()`内の「SQLiteとして開けるが`integrity_check`が`ok`以外を返す」分岐（286行目）のみ未到達（既存テストは`sqlite3.Error`を送出する破損ファイルのケースのみをカバーしており、開けるが破損した内部整合性エラーのケースは未検証）。Phase6で追加した`config/`・`export/`の新規モジュール（`csv_writer.py`, `parquet_writer.py`, `tabular.py`, `json_writer.py`, `integrity.py`, `settings.py`等）はいずれも100%カバレッジ。Phase7で追加した`fetch/`・`features/`・`services/__init__.py`・`services/orchestrator.py`はいずれもほぼ100%カバレッジ（`services/orchestrator.py`は99%、`services/scheduler.py`は97%）。

## Quality Gate（Task19-21完了報告時点で実測）

| チェック | 結果 |
|---|---|
| `poetry run ruff check .` | PASS（All checks passed!） |
| `poetry run ruff format --check .` | PASS（388 files already formatted） |
| `poetry run mypy --strict src` | PASS（Success: no issues found in 112 source files） |
| `poetry run pytest --cov` | **875 passed**（0 failed、Coverage 98.96%） |

## CI Status

3ワークフローが稼働（詳細は[`.github/workflows/README.md`](.github/workflows/README.md)）。いずれも同一の品質ゲート（ruff lint・ruff format check・mypy・pytest）を実行し、トリガーのみが異なる。

| ワークフロー | トリガー | インストール方法 |
|---|---|---|
| `ci.yml` | `pull_request`・`main`へのpush | `pip install -e ".[dev]"` |
| `release.yml` | `workflow_dispatch`・`v*`タグpush | Poetry（`pip install poetry` → `poetry install --extras dev`） |
| `nightly.yml` | `schedule`（cron、毎日）・`workflow_dispatch` | `pip install -e ".[dev]"` |

`actionlint`によるワークフロー構文検証・YAML構文検証はTask14-6実施時に合格済み。`GITHUB_TOKEN`の明示的最小権限設定（`permissions:`ブロック）・依存脆弱性スキャン（`pip-audit`等、[ADR-0026](docs/adr/0026-security-policy.md)）はいずれのワークフローにも未導入（下記Known Limitations参照）。

## Known Limitations

Task15-0監査で確認した既知の制限事項（Task15-1のDocument Drift是正により解消済みの項目は除く）。

1. `layouts/`（1様式）・`knowledge/`（8カテゴリ各1件）・Golden Testフィクスチャ（1件）とも実運用規模のデータには未到達。複数様式・表記ゆれを網羅したパイプライン実データ検証はできない。
2. リポジトリ直下の`sample_pdfs/`・`sample_outputs/`は空のまま。実データ（合成フィクスチャ）は`tests/golden/`配下という別の場所に置かれている。
3. `ftp/`・`fetch/`・`services/`（`JobOrchestrator`・`Scheduler`）パッケージはPhase7 Task16-1〜16-4で実装され、Task17-1〜17-4でComposition Root（`cli/bootstrap.py`）へ配線済みである（[`docs/api/package-design.md`](docs/api/package-design.md)参照）。`fetch-stage`/`run-workflow`/`schedule-now`/`list-schedule`の4コマンドとしてCLIから手動実行できる。Phase8 Task18-1で`FtpSettings`（`config/ftp.py`）を実装し、`build_ftp_client()`は`AppSettings.ftp`が設定されていれば実接続情報を用いる（未設定時は従来どおり`FTPConnectionConfig(host="")`というプレースホルダを生成する）。Task18-3〜18-5でGitHub Actions（`.github/workflows/scheduler.yml`）による`schedule-now run_pending_pipeline`のcron自動実行（毎日17:45 JST）を実装し、Task18-6で対応するFTP Secretsを同ワークフローへ整備した。ただし（a）`run_pending_pipeline`経路は`FTPClient`を一切呼び出さないため、自動実行されるのはPDFの取得・パース・Gold DB反映のみであり、実際のFTP公開（`run_workflow`系）は依然として`run-workflow --remote-path`によるCLI手動実行のみで到達可能、（b）実FTPサーバへの接続確認（実サーバ・実認証情報を用いた検証）はTask18-6時点でも未実施、（c）`schedule-now`/`list-schedule`の周期定義自体をCLI/設定から登録する経路は存在せず（`list-schedule`は現時点で常に0件を返す）、という3点により、PDFの自動取得からデータベース公開（FTP送信等）までを一気通貫で自動化する経路は依然として存在しない。`features/`は`pipeline/`（`JobRunner`）からも呼び出されておらず、独立した未接続のパッケージのままである。
4. ADR-0029の残部（Ed25519署名、GitHub Actionsの`GITHUB_TOKEN`最小権限設定、サードパーティActionsのコミットSHAピン留め）が未実装。Exportの完全性情報はSHA-256チェックサム（`ExportArtifact`、Phase6 Task14-4）のみ。
5. ADR-0026が求める依存脆弱性スキャン（`pip-audit`等）が3ワークフローいずれにも存在しない。
6. `export/`の新機能（`PersonnelRecord`/CSV/Parquet/完全性メタデータ、Phase6 Task14-2〜14-4）はCLIコマンドとして未公開であり、`ExportService`の内部APIとしてのみ利用できる。
7. `docs/operations/release.md`のRelease Flowが定める`parser_versions`自動記録・staging/production環境分離・データ公開（Export/FTP送信）の自動化は未実装。`release.yml`は品質ゲートの再実行のみを行う。
8. `repositories/__init__.py`に`UnitOfWork`が未定義（`docs/api/package-design.md`該当節が自己申告済み。`JobRunner`が`UnitOfWork`を使わない設計自体はADR-0046と整合）。
9. Architecture Contract Guarantee 8の文言（`promote_to_gold()`）と実装のprivateメソッド名（`_promote_to_gold()`、`approve()`から呼び出し）が完全一致しない（保証の実体は成立）。
10. `models/enums.py`の`PipelineStageName`が5値（Document Analyzerを含まない）。ADR-0032による正当な再定義が根拠だが、ADR-0011単体の字面とは異なる。
11. `docs/database/schema.md`が定める`schema_migrations`管理テーブル・`PRAGMA user_version`が未実装（`apply_schema()`は単発DDL適用のみ）。あわせて`journal_mode=WAL`・`busy_timeout`・`VACUUM`運用方針もいずれも未実装/未定である（Task20-4/Task20-7で確認、詳細は[`docs/database/schema.md`](docs/database/schema.md#運用上の注意事項)）。
12. `review/`・`export/`パッケージは、Phase4で確定した狭い契約（`docs/api/review.md`・`docs/api/interfaces.md`が描く広い契約とは異なる）のまま拡張されている（両パッケージの`__init__.py`docstringが自己申告済み）。
13. Golden以外のテスト層（Regression/Performance/Acceptance/Benchmark/Mutation）は未着手。
14. Task18-7の実測により新たに判明した2件（[`docs/reports/phase8-release-validation.md`](docs/reports/phase8-release-validation.md)）: (a) FTP接続失敗時（`FTPConnectionError`）が`cli/app.py::main()`の`except`節（`CliCommandError`/`NoPendingJobError`）のいずれにも該当せず、捕捉されないままPythonの生トレースバックとして出力される（未是正のまま残る）。(b) **（Task18-22で解消・実行実績を確認済み）** Task18-7確認時点では`scheduler.yml`・`release.yml`とも実行履歴が0件だったが、Task18-17（SQLite永続化Phase1）実装後、Task18-22でGitHub Actions API（`actions_list`/`actions_get`）により直近の実行を確認したところ、`workflow_dispatch`によるScheduler実行（run ID `30175995974`）が`success`で完了しており、「Download DB from FTP」「Run schedule-now via CLI」「Upload DB to FTP」の3ステップすべてが成功していることを実測で確認した。Production環境での実行実績は存在する。
15. **（Task18-8/18-9で解消済み、Task18-21の実FTPログで動作確認済み）** 2026-07-25、運用担当者が実際のProduction FTPサーバに対して`run-workflow --remote-path`を手動実行したところ、`connect()`/`login()`は成功したが、`upload()`（`STOR`）が絶対パス指定時に`530 You cannot upload file here`で失敗した。コード読解の結果、当時`FtpSettings.remote_directory`（`MOD_PERSONNEL_DB_FTP__REMOTE_DIRECTORY`に対応）は`FTPConnectionConfig`（`ftp/config.py`）にフィールドが存在せず、`build_ftp_client()`（`cli/bootstrap.py`）でもマッピングされず、`StandardFTPClient.connect()`（`ftp/client.py`）も`cwd()`を呼ばないため実行時に一切参照されない状態だった（フルパスを`--remote-path`に指定する運用で回避は可能だった）。**Task18-8**で`FTPConnectionConfig`へ`remote_directory`フィールドを追加し`StandardFTPClient.connect()`が`cwd()`を実行するよう実装し、**Task18-9**で`build_ftp_client()`が`FtpSettings.remote_directory`を実際に渡すよう配線した。その後Task18-21のデバッグ計装による実FTPログ（`CWD`コマンド送信後`250 CWD command succesful.`を受信）により、この`cwd(remote_directory)`経路自体が実FTPサーバ上で正常に動作することを確認済みである。
16. **（Task19-15で解消済み、実FTP検証結果に基づく）** Task19-13の実FTP検証により、ATSON FTPd v0.9.14.9では単一ファイルの存在確認に`NLST`を用いると`TYPE A`への切り替えが発生し、後続の`PASV`で`426 ASCII Transfer aborted`となり既存ファイルでも存在確認が失敗することが判明した。Task19-15で存在確認方式を`SIZE`へ変更し解消した。
17. **（Task19-17で解消済み、実FTP検証結果に基づく）** Task19-16の実FTP検証により、ATSON FTPd v0.9.14.9では既存ファイルへの`RNTO`が`553 already exist`で拒否されることが判明した。Task19-17で、既存の`remote_path.bak`がある場合は`rename`の前に`DELE`で削除する対応を実装し解消した。
18. **（残存）** atomic upload手順全体（既存`.bak`の`DELE`→`remote_path`の`.bak`への`rename`→`remote_path.uploading`の`remote_path`への`rename`）を、ATSON FTPd v0.9.14.9上でend-to-endに実行して確認する検証（Task19-18）は、実FTP認証情報がセッションになかったため未実施のまま残っている。項目16・17は個々のFTPコマンド挙動としての実FTP検証結果であり、一連の手順を通しで実行した確認ではない。
19. **（残存）** `.uploading`（アップロード中の一時ファイル名）の自動清掃機構がない。誤削除リスクを避けるための意図的な設計判断（Task19-7）であり、失敗が続いた場合はリモートに`.uploading`が蓄積しうる。
20. **（残存）** `remote_path.bak`は1世代のみ保持し、複数世代管理・自動削除の機構がない（Task19-7、実装複雑性とのバランスを取った意図的な設計判断）。
21. **（残存）** `.bak`からの手動復旧（`rename(remote_path.bak, remote_path)`等）を行う専用CLIコマンド（`restore-db-backup`等）が存在しない。復旧には汎用FTPクライアントでの手動操作が必要（Task19-7/19-8で指摘済み）。
22. **（残存）** `version_command`のConnection管理が他コマンドと異なる: `cli/commands.py::version_command()`は`build_application(settings)`を`connection`引数なしで呼び出すため、内部で生成されたConnectionが`try/finally`でcloseされない（他8コマンドはclose済み）。あわせて、`version`表示に不要なRepository（`jobs`以外の6種・Candidate Repository）・JobRunnerが毎回生成される。将来の改善候補は下記「Technical Debt（Future Refactoring Candidates）」節を参照。
23. **（残存、Task20-4確認）** 未インデックスFK列: `gold_records.superseded_by`・`learning_dataset.source_review_change_id`・`learning_dataset.reflected_in_knowledge_item_id`・`learning_dataset.reflected_in_layout_id`・`jobs.parser_version_id`の5列は外部キーだがインデックスが存在しない（詳細は[`docs/database/schema.md`](docs/database/schema.md#運用上の注意事項)）。
24. **（Task20-6で強化）** SQLite Repository境界テスト: `SqliteJobRepository.add()`が外部キー制約違反（存在しない`pdf_id`）を`sqlite3.IntegrityError`として拒否することを保証するテストを追加した。あわせて`SqliteGoldRepository.get_history()`・`SqliteKnowledgeRepository.list_items()`・`SqliteReviewRepository.list_open_sessions()`について、既存テストが未証明だった境界・フィルタ条件（空結果、複数カテゴリ、複数セッション混在時の除外）を明示的に検証するテストを追加した（いずれのメソッドも既存テストで部分的に呼び出し済みだった点はTask20-6完了報告で訂正済み）。

## Technical Debt（Future Refactoring Candidates）

現時点の不具合ではなく、将来のリファクタリング候補として記録する項目。SQLite Connection管理（`cli/bootstrap.py`・`cli/commands.py`）に関するレビューで整理した。

1. **`version_command`専用の軽量Builder導入（最有力候補）**: `bootstrap.py`に`version_command`専用のBuilder（`FileKnowledgeService`と`SqliteJobRepository`のみを組み立てる関数）を追加し、`build_application()`が持つ不要なRepository生成・JobRunner構築・`parser_versions`書き込み副作用を回避する。Composition Root一本化原則（Architecture Contract Guarantee 15）を維持できる案。
2. **`_build_job_orchestrator()`のRepository二重生成解消**: `build_application()`が生成する`SqlitePdfRepository`（Connection共有済み）を`_build_job_orchestrator()`側でも再利用し、`build_sqlite_repositories()`の2回目呼び出し（jobs/gold/knowledge/review/export/learning 6 Repository分の無駄な生成）を排除する。
3. **Connectionを`commands.py`へ露出しない設計への整理**: 現行の`tuple[JobOrchestrator, sqlite3.Connection]`方式は、Connectionという実装詳細をコマンド層まで運んでいる。Repositoryという上位の抽象のみを受け渡す設計へ整理する。
4. **`tuple[JobOrchestrator, sqlite3.Connection]`の廃止**: 上記3の帰結として、`_build_job_orchestrator()`/`_build_scheduler()`の戻り値からConnectionを取り除き、`JobOrchestrator`/`Scheduler`単体を返す形へ整理する。
5. **Connection生成・所有・close責務をComposition Rootへ完全集約**: 現状は生成者（`commands.py`内の`_build_job_orchestrator()`）とclose責務者（呼び出し元コマンド関数）が分離している。これを`bootstrap.py`側のみで完結させる。
6. **（参考、不採用）`commands.py`でRepository具象を直接生成する案**: 項目1の代替として検討したが、Composition Root原則（Architecture Contract Guarantee 15）を崩すため採用候補とはしない。参考案としてのみ記録する。

## Phase8開始前の残課題一覧（Task17-6で整理、Task18-0で実装設計を確定）

Phase7 Closeoutにあたり、Phase8着手前に解消が必要な5項目を明示する（下記「Remaining Work」の該当項目と対応する。詳細な設計・実装方針は各項目のリンク先を正とする）。5項目それぞれの実装設計（`AppSettings`拡張方法・環境変数名・Validation方針・`Scheduler`自動起動方式・Production Workflow・Composition Root更新方針・Release Readiness残Task一覧）は[`docs/phase8-integration-design.md`](docs/phase8-integration-design.md)（Task18-0、設計のみ・実装は別タスク）が確定した。

1. **FtpSettings実装（Task18-1で完了）**: `config/ftp.py`に`FtpSettings`（host/port/username/password等、`SecretStr`によるパスワード秘匿を含む）を実装した。`cli/bootstrap.py`の`build_ftp_client()`は`AppSettings.ftp`が設定されていれば実接続情報を用いる（未設定時は従来どおり`FTPConnectionConfig(host="")`というプレースホルダを生成する）。
2. **Scheduler永続化**: `Scheduler`（`DefaultScheduler`）はコンストラクタ注入された`JobSchedule`一覧をメモリ上に保持するのみで、永続化・CLI/設定からの登録経路が存在しない。現状`cli/commands.py`の`_build_scheduler()`は常に空タプルを渡すため、`list-schedule`は常に0件を返す。
3. **自動実行経路（Task18-3〜18-5で完了）**: GitHub Actions（`.github/workflows/scheduler.yml`）による`schedule-now run_pending_pipeline`のcron自動実行（毎日17:45 JST）を実装した。対象は`run_pending_pipeline`のみであり、Fetch/Export/FTP Publishを含む`run_workflow`系の自動化は対象外のまま残る。
4. **release.yml**: `parser_versions`自動記録・staging/production環境分離・データ公開（Export/FTP送信）の自動化が未実装。現状の`release.yml`は品質ゲートの再実行のみを行う（[`docs/operations/release.md`](docs/operations/release.md#release-flow)）。
5. **Production FTP接続（Task18-8/18-9/18-21/18-22で完了）**: 上記1（`FtpSettings`）はTask18-1で実装済みであり、対応するGitHub SecretsもTask18-6で`scheduler.yml`へ整備済みである。実FTPサーバへの接続・`cwd(remote_directory)`実行・アップロードは、Task18-7追記（フルパス指定での`STOR`成功）・Task18-21（`CWD`成功の実ログ）・Task18-22（GitHub Actions実行での3ステップ成功）でいずれも実地検証済みである。Task19では、`upload()`のatomic化に伴い新設した`SIZE`（存在確認）・`DELE`（backup更新）について、個々のFTPコマンド挙動としての実FTP検証（Task19-13/19-16）は得られたが、atomic upload手順全体をend-to-endで実行する検証（Task19-18）は実FTP認証情報の制約により未実施のまま残る（[`docs/operations/release.md`](docs/operations/release.md#production-ftp運用)参照）。

## Remaining Work

v1.0.0正式版に向けた残タスクの一覧は、[`docs/operations/release.md`](docs/operations/release.md#release-candidateからv100正式版までの残タスク)に集約した（本ファイルとの重複記載を避けるため、詳細は同節を正とする）。主要カテゴリは以下のとおり。

- データ整備（`layouts/`・`knowledge/`・Golden Testフィクスチャの実運用規模への拡充）
- `ftp/`の実接続情報整備（`config/`への`FtpSettings`追加・`build_ftp_client()`更新、Task18-1）、対応するGitHub Secrets整備（Task18-6）、`cwd(remote_directory)`経路の実装・配線・実地検証（Task18-8/18-9/18-21）、GitHub Actions経由の自動実行実績確認（Task18-22）はいずれも完了した。Production FTPサーバへの手動公開経路（`run-workflow --remote-path`）・定期自動実行経路（`scheduler.yml`のDB同期ステップ）のいずれも実際に機能することが実測で確認されている。
- SQLite DBの永続化（`download-db`/`upload-db`CLIコマンド、Task18-17）・`upload()`のatomic化とDB `integrity_check`（Task19-5）・存在確認方式の`SIZE`化（Task19-15、ATSON FTPd v0.9.14.9対応）・backup更新処理の`DELE`対応（Task19-17、同サーバ対応）は完了した。**残るのは、atomic upload手順全体（`DELE`→`rename`→`rename`）をend-to-endで実FTPサーバ上で確認する検証（Task19-18）、`.uploading`/`.bak`関連の復旧を行う専用CLIコマンドの実装、`.bak`の複数世代管理である**（詳細は上記Known Limitations項目18〜21、[`docs/operations/release.md`](docs/operations/release.md#atomic-upload障害時の復旧手順)参照）。
- 定期実行の自動化のうち、cronによる`schedule-now run_pending_pipeline`の起動（`.github/workflows/scheduler.yml`）・DB同期（Download/Upload DB from/to FTP）はTask18-3〜18-5・Task18-17で完了し、Task18-22でGitHub Actions実行の成功を実測確認済みである。`Scheduler`本体（`trigger_now`/`list_upcoming`）・CLI統合（`schedule-now`/`list-schedule`）はTask17-3/17-4で実装済み。ただし`JobSchedule`をCLI/設定から登録する経路（周期定義自体の永続化）は未実装のまま残り、`list-schedule`は現時点で常に0件を返す
- `features/`の`JobRunner`への統合（`FeatureVector`を`Normalizer`/`Validator`のコンストラクタへ注入する設計、新規ADR起票が前提）
- セキュリティ強化（ADR-0026の依存脆弱性スキャン、ADR-0029の署名・`GITHUB_TOKEN`最小権限）
- リリース自動化（`parser_versions`自動記録、staging/production環境分離）
- CLI公開範囲の拡張（`export/`新機能のコマンド化）
- 残りのテスト層整備（Regression/Performance/Acceptance/Benchmark/Mutation）

## Release Recommendation

- **v1.0.0タグ付与（正式リリース）は推奨しない。** 上記Known Limitations、特に(a)`schedule-now run_pending_pipeline`（SQLite DB自体のFTP同期を含め自動実行経路が整備された、Task18-17/Task19）は、公開用データ（`PersonnelRecord`/CSV/Parquet）を配布する`run_workflow`系のFTP公開（`export_and_publish()`）を依然として自動実行しないため、実際の外部公開（データ配布）への**自動化された**経路は存在しないこと、(b)`layouts/`・`knowledge/`・Golden Testフィクスチャが実運用規模に未到達であること、(c)ADR-0026・ADR-0029が求めるセキュリティ関連実装が未着手であること、(d)atomic upload手順全体のend-to-end実FTP検証（Task19-18）が未実施であること、の4点は「継続的にPDFを収集・公開する」というプロジェクトの中核目的に直接関わるため、これらの解消を待つべきである。
- **v1.0.0-rc1等のPre-releaseタグ付与、または内部的なRelease Candidateとしての継続利用は妥当である。** Architecture Contract 15/15維持、ADR間の矛盾ゼロ、テスト875件全通過・Coverage 98.96%、mypy --strict / ruff（check・format）とも成功しており、実装済み範囲（中核パイプライン・Gold Database・Review・Export・CLI・CI/CD基盤、およびCLI統合が完了した`fetch/`・`ftp/`・`services/`）における構造的な健全性は監査により裏付けられている。Phase6時点からの前進として、`fetch-stage`/`run-workflow`/`schedule-now`/`list-schedule`の4コマンドが手動実行可能になった。Phase8ではさらに`FtpSettings`実装（Task18-1）・cron自動実行（Task18-3〜18-5）・FTP Secrets整備（Task18-6）・`remote_directory`の`ftp/`実装とComposition Root配線（Task18-8/18-9）・SQLite永続化（`download-db`/`upload-db`、Task18-17）・GitHub Actions実行実績の実測確認（Task18-22）・atomic upload・DB `integrity_check`（Task19-5/19-15/19-17）が加わった。
- 次のマイルストーンは「Remaining Work」節の各カテゴリのうち、特にデータ整備・セキュリティ強化・atomic upload end-to-end実FTP検証（Task19-18）を優先することを推奨する（`FtpSettings`整備・cron定期実行自動化・SQLite永続化・`remote_directory`配線はいずれも完了・実地検証済みのため優先順位から外れた）（詳細な優先順位付けは本ファイルの範囲外とし、`docs/roadmap.md`等の別途の意思決定に委ねる）。
- **Production Ready判定: Release Candidate maintained（Task19-21時点で根拠を更新、判定自体は変更なし）。** Task18-7時点で「未確認」だった（1）実FTPサーバへの接続実績、（2）GitHub Secretsの実登録状況、（3）`scheduler.yml`のGitHub Actions runner上での実行実績のうち、（1）はTask18-7追記・Task18-21の実ログで、（3）はTask18-22のGitHub Actions API確認で、いずれも**成功として確認済み**に更新された。（2）はGitHub Secretsの値自体を本セッションから直接閲覧する手段がないため引き続き未確認のままである。「`remote_directory`が実行時に一切効果を持たないデッドコンフィグである」問題（Task18-8・Task18-9で実装解消、Task18-21で実地検証も完了）に続き、Task19では運用中に実際に発生したエラー（`remote_path`が空文字列になる問題、`500 Invalid argument`）の調査を経て、DBファイル自体のFTP同期処理をatomic化した（Task19-5）。この過程でATSON FTPd v0.9.14.9固有の制約（`NLST`使用時の`426`、既存ファイルへの`RNTO`時の`553 already exist`）が実FTP検証（Task19-13/19-16）で判明し、Task19-15（`SIZE`方式）・Task19-17（`DELE`対応）で解消した。ただし、この一連の手順を実FTPサーバ上でend-to-endに実行して確認する検証（Task19-18）は、実FTP認証情報がセッションになかったため未実施のまま残っている。（i）データ整備・セキュリティ強化等の他のKnown Limitationsが未解消であること、（ii）atomic upload全体のend-to-end実地検証（Task19-18）が未実施であること、（iii）FTP公開（`export_and_publish()`）自体が`schedule-now`の自動実行経路には含まれない設計上の制約が変わらないこと、の3点により、Release Candidate maintainedの判定を継続する。

## 関連ドキュメント

- [`README.md`](README.md) — プロジェクト概要、「既知の制限事項」節、「リリースタグ運用」節
- [`CHANGELOG.md`](CHANGELOG.md) — Phase1〜Phase6の変更履歴
- [`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md) — Phase5時点の詳細監査レポート
- [`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md) — Phase7（CLI統合完了後）の詳細監査レポート（Task17-5）
- [`docs/operations/release.md`](docs/operations/release.md) — Release Flow・残タスク一覧
- [`docs/architecture/architecture-contract.md`](docs/architecture/architecture-contract.md) — Architecture Contract（15 Guarantee）
- [`docs/adr/`](docs/adr/) — Architecture Decision Records（全46本）
- [`docs/phase7-implementation-roadmap.md`](docs/phase7-implementation-roadmap.md) — Phase7 4パッケージの設計方針・実装ロードマップ（Task16-0）
- [`docs/phase7-integration-design.md`](docs/phase7-integration-design.md) — Phase7 Composition Root統合設計（Task17-0、Task17-1/17-4で実装済み）
- [`docs/phase8-integration-design.md`](docs/phase8-integration-design.md) — Phase8統合設計（Task18-0、`FtpSettings`・`Scheduler`自動起動・Production Workflow・Composition Root更新方針・Release Readiness残Task。設計のみ、実装は別タスク）
- [`docs/reports/phase8-release-validation.md`](docs/reports/phase8-release-validation.md) — Production Release Validationレポート（Task18-7、GitHub Actions実行履歴・実CLI実行による実測検証、Production Ready判定）
