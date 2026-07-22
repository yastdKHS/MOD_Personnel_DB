# RELEASE_STATUS

> 本ファイルはv1.0.0 Release Candidateとしてのリリース判定を記録する。ソースコード・テストの実装は一切含まない、読み取り専用の判定記録である。判定根拠はPhase6 Task15-0の最終監査（読み取り専用で実施、レポートファイルは作成していない）、および[`CHANGELOG.md`](CHANGELOG.md)のPhase6節が記録するTask15-1のDocument Drift是正結果に基づく。

## Version

`v1.0.0`（未タグ付け、候補版）。`pyproject.toml`の`version`は引き続き`0.0.0`のまま（[ADR-0001](docs/adr/0001-python-packaging.md)、実装着手時のバージョン運用は[ADR-0023](docs/adr/0023-parser-versioning-policy.md)のSemVer規則に従う）。タグ運用の詳細はREADMEの「[リリースタグ運用](README.md#リリースタグ運用)」を参照。

## Date

2026-07-22（Phase6 Task15-4作成時点）。

## Current Status

**v1.0.0 Release Candidate（Phase6完了）**。Phase6 Task15-0で実施した最終監査（Architecture Contract全15 Guarantee・ADR全46本・Dependency Rule・Package Design・Protocol・Composition Root・Workflow・Testの整合性監査、読み取り専用）の結果、設計と実装の間に致命的な不整合は検出されなかった。Task15-1でDocument Drift（`config/`実装状況・`ExportService`実装状況注記・Golden Test配置説明の3件）を是正済み。Task15-2でREADME/CHANGELOGのバージョン整合・既知の制限事項の反映・docs索引の到達性確保・`release.yml`との整合を実施済み。

## Release Decision

**Not Ready（v1.0.0としての完全な本番リリースには未達）。実装済み範囲（中核パイプライン・Gold Database・Review・Export・CLI・CI/CD）に限定したRelease Candidateとしては、構造的な不整合なく到達している。**

判定根拠は「Known Limitations」節および「Release Recommendation」節を参照。

## Completed Phases

| Phase | 内容 | 状態 |
|---|---|---|
| Phase1 | 設計フェーズ（リポジトリ構造・ADR・データモデル・API/Interface設計・Review Domain・運用設計の確定、[`docs/design-freeze.md`](docs/design-freeze.md)） | 完了 |
| Phase2 | 中核パイプライン6段階（Document Analyzer〜Validator）・Repository層・ドメインモデルの実装 | 完了 |
| Phase3 | JobRunner（Coordinator）・Composition Root（`cli/bootstrap.py`）・CLI Entry Pointの実装 | 完了 |
| Phase4 | ReviewService/ExportService実装、`review`/`export`サブコマンド追加、CLI E2E統合テスト追加 | 完了 |
| Phase5 | 全体最終監査（[`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md)）・ドキュメント同期・リリース準備 | 完了 |
| Phase6 | 公開JSON契約（Task14-2）・CSV/Parquetエクスポート（Task14-3）・Export完全性保証（Task14-4）・Pydantic Settings採用（Task14-5）・GitHub Actions Workflow Orchestration（Task14-6）の実装、Golden Test自動化（Task14-0/14-1）、v1.0.0 Release Candidateとしての最終監査（Task15-0）・Document Drift是正（Task15-1）・最終ドキュメント整備（Task15-2）・本リリース判定（Task15-4） | 完了 |

## Architecture Contract

[`docs/architecture/architecture-contract.md`](docs/architecture/architecture-contract.md)が定める**Guarantee 1〜15**全件を再監査した（Task15-0）。**15件すべてが構造的に維持されている**。Phase6で変更された`export/`・`config/`・`cli/bootstrap.py`についても、Guarantee 7（RepositoryがSQLiteを隠蔽）・8/9（Reviewのみがgold_recordsを書き換える）・15（依存生成責務はComposition Rootに一本化）を個別に再確認し、いずれも維持されていることを確認した（`export/`の新規モジュールは`GoldRepository.add_version()`/`supersede()`を一切呼び出さない、`AppSettings`の生成は`cli/bootstrap.py`の`build_settings()`一箇所に限定される）。

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

- **Unit**: `tests/unit/`配下64ファイル（`cli`, `config`, `document`, `export`, `extractors`, `knowledge`, `layout`, `learning`, `models`, `normalizers`, `pipeline`, `repositories`, `review`, `sections`, `validators`）。
- **Integration**: `tests/integration/`配下6ファイル（`cli/test_cli_e2e.py`, `config/test_settings_integration.py`, `export/test_export_personnel_records.py`, `export/test_export_csv_parquet.py`, `export/test_export_with_metadata.py`, `golden/test_golden.py`）。
- **Golden**: [`tests/integration/golden/test_golden.py`](tests/integration/golden/test_golden.py)（Phase6 Task14-1）が実装済み。フィクスチャは`tests/golden/`に合成PDF・期待結果JSONを各1件配置（[ADR-0007](docs/adr/0007-golden-file-testing.md)）。
- **未着手のテスト層**: Regression / Performance / Acceptance / Benchmark / Mutation（[`docs/testing/test-policy.md`](docs/testing/test-policy.md)が定める8種のうち残り5種）。
- **実行結果**: `poetry run pytest --cov` → **634 passed**（0 failed）。

## Coverage

`poetry run pytest --cov` の TOTAL coverage は **98.99%**。`pyproject.toml`の`[tool.coverage.report]`が定める閾値（`fail_under = 80`）を大きく上回る。Phase6で追加した`config/`・`export/`の新規モジュール（`csv_writer.py`, `parquet_writer.py`, `tabular.py`, `json_writer.py`, `integrity.py`, `settings.py`等）はいずれも100%カバレッジ。

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
3. `features/`・`ftp/`・`fetch/`・`services/`パッケージが未実装。PDFの自動取得・実際のデータベース公開（FTP送信等）の経路が存在しない。
4. ADR-0029の残部（Ed25519署名、GitHub Actionsの`GITHUB_TOKEN`最小権限設定、サードパーティActionsのコミットSHAピン留め）が未実装。Exportの完全性情報はSHA-256チェックサム（`ExportArtifact`、Phase6 Task14-4）のみ。
5. ADR-0026が求める依存脆弱性スキャン（`pip-audit`等）が3ワークフローいずれにも存在しない。
6. `export/`の新機能（`PersonnelRecord`/CSV/Parquet/完全性メタデータ、Phase6 Task14-2〜14-4）はCLIコマンドとして未公開であり、`ExportService`の内部APIとしてのみ利用できる。
7. `docs/operations/release.md`のRelease Flowが定める`parser_versions`自動記録・staging/production環境分離・データ公開（Export/FTP送信）の自動化は未実装。`release.yml`は品質ゲートの再実行のみを行う。
8. `repositories/__init__.py`に`UnitOfWork`が未定義（`docs/api/package-design.md`該当節が自己申告済み。`JobRunner`が`UnitOfWork`を使わない設計自体はADR-0046と整合）。
9. Architecture Contract Guarantee 8の文言（`promote_to_gold()`）と実装のprivateメソッド名（`_promote_to_gold()`、`approve()`から呼び出し）が完全一致しない（保証の実体は成立）。
10. `models/enums.py`の`PipelineStageName`が5値（Document Analyzerを含まない）。ADR-0032による正当な再定義が根拠だが、ADR-0011単体の字面とは異なる。
11. `docs/database/schema.md`が定める`schema_migrations`管理テーブル・`PRAGMA user_version`が未実装（`apply_schema()`は単発DDL適用のみ）。
12. `review/`・`export/`パッケージは、Phase4で確定した狭い契約（`docs/api/review.md`・`docs/api/interfaces.md`が描く広い契約とは異なる）のまま拡張されている（両パッケージの`__init__.py`docstringが自己申告済み）。
13. Golden以外のテスト層（Regression/Performance/Acceptance/Benchmark/Mutation）は未着手。

## Remaining Work

v1.0.0正式版に向けた残タスクの一覧は、[`docs/operations/release.md`](docs/operations/release.md#release-candidateからv100正式版までの残タスク)に集約した（本ファイルとの重複記載を避けるため、詳細は同節を正とする）。主要カテゴリは以下のとおり。

- データ整備（`layouts/`・`knowledge/`・Golden Testフィクスチャの実運用規模への拡充）
- 未実装パッケージの実装（`features/`・`ftp/`・`fetch/`・`services/`）
- セキュリティ強化（ADR-0026の依存脆弱性スキャン、ADR-0029の署名・`GITHUB_TOKEN`最小権限）
- リリース自動化（`parser_versions`自動記録、staging/production環境分離）
- CLI公開範囲の拡張（`export/`新機能のコマンド化）
- 残りのテスト層整備（Regression/Performance/Acceptance/Benchmark/Mutation）

## Release Recommendation

- **v1.0.0タグ付与（正式リリース）は推奨しない。** 上記Known Limitations、特に(a)`features/`・`ftp/`・`fetch/`・`services/`未実装によりPDF自動取得・実際の外部公開経路が存在しないこと、(b)`layouts/`・`knowledge/`・Golden Testフィクスチャが実運用規模に未到達であること、(c)ADR-0026・ADR-0029が求めるセキュリティ関連実装が未着手であること、の3点は「継続的にPDFを収集・公開する」というプロジェクトの中核目的に直接関わるため、これらの解消を待つべきである。
- **v1.0.0-rc1等のPre-releaseタグ付与、または内部的なRelease Candidateとしての継続利用は妥当である。** Architecture Contract 15/15維持、ADR間の矛盾ゼロ、テスト634件全通過・Coverage 98.99%、mypy --strict / ruffとも成功しており、実装済み範囲（中核パイプライン・Gold Database・Review・Export・CLI・CI/CD基盤）における構造的な健全性は監査により裏付けられている。
- 次のマイルストーンは「Remaining Work」節の各カテゴリのうち、特にデータ整備とセキュリティ強化を優先することを推奨する（詳細な優先順位付けは本ファイルの範囲外とし、`docs/roadmap.md`等の別途の意思決定に委ねる）。

## 関連ドキュメント

- [`README.md`](README.md) — プロジェクト概要、「既知の制限事項」節、「リリースタグ運用」節
- [`CHANGELOG.md`](CHANGELOG.md) — Phase1〜Phase6の変更履歴
- [`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md) — Phase5時点の詳細監査レポート
- [`docs/operations/release.md`](docs/operations/release.md) — Release Flow・残タスク一覧
- [`docs/architecture/architecture-contract.md`](docs/architecture/architecture-contract.md) — Architecture Contract（15 Guarantee）
- [`docs/adr/`](docs/adr/) — Architecture Decision Records（全46本）
