# Implementation Checklist

> 実装開始前・実装中・実装完了時に確認するチェックリスト。[`docs/implementation.md`](implementation.md)の「Definition of Done」を、実行可能なチェック項目に分解したものである。各項目は既存の設計文書のいずれかに根拠を持ち、本ドキュメントで新しい判断基準を追加するものではない。実装コードは含まない。

## 使い方

- 新しい実装タスク（1つのPull Requestに対応する単位）に着手する前に、関連する節のチェック項目を確認する。
- すべての項目がすべてのPRに該当するわけではない。該当しない項目は読み飛ばしてよいが、「該当しない」という判断自体をPR説明に明記することを推奨する（レビュー担当者が判断根拠を追えるようにするため）。

## Architecture

- [ ] 変更は中核パイプライン6段階（Document Analyzer → Layout Detector → Section Parser → Field Extractor → Normalizer → Validator）の構成・順序を変更していないか（[ADR-0011](adr/0011-fixed-core-pipeline.md)）。変更する場合はプロジェクトオーナーの明示的承認を得たか。
- [ ] 新しいパッケージ・モジュールの依存先は[`docs/api/dependency-rule.md`](api/dependency-rule.md)の依存グラフに違反していないか。
- [ ] Architecture Contract（[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)）の10の保証のいずれも侵害していないか。

## ADR

- [ ] データモデル・技術選定・パイプライン構成に関わる変更の場合、対応するADRが存在するか。存在しない場合、実装着手前に新規ADRを起票したか（[`docs/adr/README.md`](adr/README.md#いつadrを書くか作成ルール)）。
- [ ] 既存ADRと矛盾する変更をしていないか。矛盾する場合、既存ADRをSupersededにする手続きを踏んだか（無断で書き換えていないか）。
- [ ] Constitution（[`docs/constitution.md`](constitution.md)）と矛盾していないか。

## Repository

- [ ] 新しい永続化要求は、既存の8 Repository Protocol（[`docs/api/repositories.md`](api/repositories.md)）で表現できるか。できない場合、SQL実装より先にProtocol定義を更新したか（[`docs/implementation.md`](implementation.md#repository-first)の「Repository First」）。
- [ ] Repository実装（`repositories/sqlite/`）にドメイン判断（Confidence算出等のビジネスロジック）を含めていないか（[`docs/implementation.md`](implementation.md#no-business-logic-in-repository)）。
- [ ] `repositories/sqlite/`以外のパッケージが`sqlite3`を直接importしていないか（[`docs/implementation.md`](implementation.md#no-sqlite-dependency-outside-infrastructure)）。
- [ ] 複数Repositoryにまたがる操作は`UnitOfWork`を`with`文で使っているか（[`docs/api/repositories.md`](api/repositories.md#unitofwork)）。

## Knowledge

- [ ] 未知パターンへの対応は、Knowledge追加 > Layout追加 > 例外処理の優先順位（[ADR-0012](adr/0012-error-handling-priority-order.md)）に従っているか。
- [ ] `knowledge/`への変更は一括置換・自動生成でなく、差分が説明可能な単位か（[`CLAUDE.md`](../CLAUDE.md)）。
- [ ] AIコーディングエージェントが`knowledge/`を直接確定させていないか（提案のみで、人間の承認を経ているか、[`docs/constitution.md`](constitution.md)のAI Principles）。
- [ ] `knowledge_items.category`のDB制約とYAML Schemaのカテゴリ（8種）が一致しているか（[`docs/knowledge/schema.md`](knowledge/schema.md)）。

## Review

- [ ] `gold_records`への書き込みは`ReviewDecision`経由のみか（他の経路を実装していないか、Architecture Contract保証8・9）。
- [ ] レビュー担当者の承認権限・差戻し・再レビュー条件は[`docs/review/policy.md`](review/policy.md)に従っているか。
- [ ] Reviewキューの優先度スコア計算に影響する変更の場合、[`docs/review/queue.md`](review/queue.md)の式との整合を確認したか。

## Workflow

- [ ] 変更はWorkflow State Machine（[`docs/workflow/state-machine.md`](workflow/state-machine.md)）の10状態・遷移規則と矛盾しないか。
- [ ] `Approved`以降のデータに対して、削除ではなくCompensating Action（新バージョン追加）で訂正する設計になっているか（[`docs/workflow/state-machine.md`](workflow/state-machine.md#rollback)）。
- [ ] Retry Policy・Timeoutの値を変更する場合、既存の分類・バックオフ戦略と整合しているか。

## Configuration

- [ ] 新しい設定項目は`config/`パッケージのPydantic Settings（[ADR-0028](adr/0028-pydantic-settings-for-configuration.md)）として追加され、`models/`のPydantic不採用方針を侵害していないか。
- [ ] 環境（dev/test/staging/production）ごとの必須/任意の区別（[`docs/configuration.md`](configuration.md#validation-rule)）を満たしているか。
- [ ] Secretを`.env`・環境変数以外（コード・ログ・Git履歴）に含めていないか（[`docs/configuration.md`](configuration.md#secret管理)）。
- [ ] 設定スキーマの変更は後方互換の移行手順（非推奨期間の設定）に従っているか（[`docs/configuration.md`](configuration.md#migration)）。

## Security

- [ ] 新しい外部依存ライブラリの追加は、着手前にADR確認・Security Review（[`docs/security.md`](security.md#security-review)）のトリガー条件に該当しないか。
- [ ] Secretの種類・スコープの変更がある場合、最小権限（[`docs/security.md`](security.md#最小権限)）に従っているか。
- [ ] 公開成果物に関わる変更は、Checksum/署名の仕組み（[`docs/security.md`](security.md#checksum--hash)）を損なっていないか。
- [ ] GitHub Actionsワークフローの権限変更は、最小権限（`GITHUB_TOKEN`の`permissions`）を明示しているか（[`docs/security.md`](security.md#github-actions)）。
- [ ] `.pre-commit-config.yaml`のgitleaksが誤検知していないか（Secretの誤コミットがないか）。

## Logging

- [ ] `print()`を使わず`logging`を使っているか（[`docs/api/python-contract.md`](api/python-contract.md#logging設計)）。
- [ ] ログレベル（DEBUG/INFO/WARNING/ERROR）が[`docs/api/python-contract.md`](api/python-contract.md#logging設計)の指針に沿っているか。
- [ ] パイプライン関連のログに`correlation_id`を含めているか。
- [ ] ログに個人情報を、公開JSONで許容される範囲を超えて出力していないか（[ADR-0008](adr/0008-data-ethics-policy.md)）。
- [ ] Secretの値をログに出力していないか（`SecretStr`型が正しく使われているか、[`docs/configuration.md`](configuration.md#secret管理)）。

## Testing

- [ ] 新機能・変更に対応するテストが追加されているか（[`docs/testing/test-policy.md`](testing/test-policy.md)の該当種別）。
- [ ] パーサー関連の変更にはゴールデンファイルテスト（`tests/golden`）を追加・確認したか。
- [ ] `pytest`がローカル・CIでグリーンか。
- [ ] Coverage目標（暫定80%、[`docs/testing/test-policy.md`](testing/test-policy.md#unit-test)）を著しく下回っていないか。

## Observability

- [ ] 新しいジョブ種別・処理経路は`jobs`テーブルへの記録経路を持っているか（[`docs/operations/observability.md`](operations/observability.md#health-check)）。
- [ ] 新しい運用上重要な指標（Metrics）は、既存の5カテゴリ（パイプライン実行系/データ鮮度系/品質系/Review系/運用基盤系）のいずれかに位置づけられるか（[`docs/operations/observability.md`](operations/observability.md#metrics)）。
- [ ] SLO/SLI/Error Budgetに影響する変更の場合、[`docs/operations/observability.md`](operations/observability.md#slo)を更新したか。

## CI/CD

- [ ] `ruff check` / `ruff format --check` / `mypy --strict`がグリーンか。
- [ ] `.github/workflows/ci.yml`の対象ファイル有無チェック（`has_code` / `has_tests`）が、追加したファイルを正しく検出するか。
- [ ] コードリリースとデータ公開が分離された設計になっているか（[`docs/operations/release.md`](operations/release.md#release-flow)、`main`マージが即座にデータを公開しないか）。
- [ ] GitHub Actionsで新しいSecretを使う場合、`production`専用のGitHub Environmentに限定されているか（[`docs/security.md`](security.md#github-actions)）。

## Documentation

- [ ] 影響する設計文書（`docs/api/models.md`, `docs/database/schema.md`等）を同一PRで更新したか。
- [ ] 新しいドキュメントを追加した場合、[`README.md`](../README.md) / `docs/README.md`のドキュメント目次に追加したか。
- [ ] リンク切れ（相対パス・アンカー）がないか確認したか。
- [ ] ドキュメントの記述が日本語規約（[`CLAUDE.md`](../CLAUDE.md)）に従っているか。

## Definition of Done

- [ ] [`docs/implementation.md`](implementation.md#definition-of-done)の7項目（実装・テスト・ドキュメント・Architecture Contract・ADR・レビュー・CI/CD）をすべて満たしているか。
- [ ] `CODEOWNERS`に基づくレビュー担当者の承認を得ているか。
- [ ] 1つのPRが1つの責務のみを変更しているか（[ADR-0014](adr/0014-development-discipline.md)）。
- [ ] コミットメッセージがConventional Commits（[`CONTRIBUTING.md`](../CONTRIBUTING.md)）に従っているか。

## 関連ドキュメント

- [`docs/implementation.md`](implementation.md) — Implementation Guide（本チェックリストが分解する上位文書）
- [`docs/coding-style.md`](coding-style.md) — Coding Style Guide
- [`docs/testing/test-policy.md`](testing/test-policy.md) — Test Policy
- [`docs/parser-guidelines.md`](parser-guidelines.md) — Parser Development Guidelines
- [`docs/developer-workflow.md`](developer-workflow.md) — Developer Workflow
- [`docs/design-freeze.md`](design-freeze.md) — Design Freeze Review
