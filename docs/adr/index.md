# ADR Inventory

> ADR一覧の詳細メタデータ台帳。プロセス・命名規則・レビュー手順等は [`README.md`](README.md) を参照。依存関係の可視化は [`dependency-map.md`](dependency-map.md)、不足トピックの分析は [`gap-analysis.md`](gap-analysis.md) を参照。
>
> 作成日・最終更新日は `git log --follow`（作成: 最古のコミット、最終更新: 最新のコミット）に基づく事実。本表は自動生成ではなく、ADR追加・変更のたびに手動更新する（更新手順は[README.mdのレビュー手順](README.md#レビュー手順)参照）。

| # | タイトル | ステータス | 作成日 | 最終更新日 | 関連ADR | 関連ドキュメント |
|---|---|---|---|---|---|---|
| [0001](0001-python-packaging.md) | Pythonパッケージング・ビルドバックエンドの選定 | Accepted | 2026-07-17 | 2026-07-17 | — | README.md, src/README.md, database/schema.md |
| [0002](0002-lint-format-typecheck-tooling.md) | Lint / Format / 型チェックツールの選定 | Accepted | 2026-07-17 | 2026-07-17 | — | src/README.md, 0014 |
| [0003](0003-layout-definition-strategy.md) | PDFレイアウトの外部データ定義化 | Accepted | 2026-07-17 | 2026-07-17 | 0007, 0011, 0012 | CLAUDE.md, README.md, layouts/README.md, knowledge/layout_notes/README.md, database/schema.md, knowledge/schema.md, src/README.md |
| [0004](0004-sqlite-as-datastore.md) | データストアとしてのSQLite採用 | Accepted | 2026-07-17 | 2026-07-17 | — | README.md, architecture.md, database/schema.md, src/README.md |
| [0005](0005-knowledge-base-normalization.md) | ドメイン知識ベースによる名寄せ・正規化戦略 | Accepted | 2026-07-17 | 2026-07-17 | 0003, 0012, 0013 | knowledge/README.md, database/schema.md, database/json_schema.md, knowledge/schema.md, src/README.md |
| [0006](0006-pipeline-provenance.md) | パイプライン段階分割と来歴（Provenance）管理 | Accepted | 2026-07-17 | 2026-07-17 | 0011, 0013 | architecture.md, architecture/learning_dataset.md, data_model.md, database/schema.md, database/json_schema.md, knowledge/learning_dataset/README.md, src/README.md |
| [0007](0007-golden-file-testing.md) | ゴールデンファイルテスト戦略 | Accepted | 2026-07-17 | 2026-07-17 | — | database/schema.md, database/json_schema.md, architecture/learning_dataset.md, sample_outputs/README.md, tests/README.md |
| [0008](0008-data-ethics-policy.md) | 個人情報・データ倫理方針 | Accepted | 2026-07-17 | 2026-07-17 | — | README.md, database/schema.md, database/json_schema.md, knowledge/schema.md, knowledge/aliases/README.md, sample_pdfs/README.md, logs/README.md |
| [0009](0009-ai-agent-operating-policy.md) | AIコーディングエージェント運用方針 | Accepted | 2026-07-17 | 2026-07-17 | — | CLAUDE.md, AGENTS.md（[品質チェック](quality-check.md#孤立したadr)で検出・修正） |
| [0010](0010-ci-cd-and-publish-strategy.md) | CI/CDと公開戦略 | Accepted | 2026-07-17 | 2026-07-17 | 0006 | database/schema.md, database/json_schema.md |
| [0011](0011-fixed-core-pipeline.md) | 中核処理パイプラインの固定化 | Accepted（変更に高いハードル） | 2026-07-17 | 2026-07-17 | 0003, 0005, 0006, 0012, 0014 | AGENTS.md, CLAUDE.md, README.md, architecture.md, architecture/learning_dataset.md, database/schema.md, knowledge/schema.md, src/README.md |
| [0012](0012-error-handling-priority-order.md) | 未知パターンへの対応優先順位 | Accepted | 2026-07-17 | 2026-07-17 | 0003, 0005, 0011 | AGENTS.md, CLAUDE.md, CONTRIBUTING.md, README.md, architecture.md, database/schema.md, knowledge/README.md, src/README.md |
| [0013](0013-learning-dataset-not-correction-log.md) | Learning Dataset設計方針 | Accepted | 2026-07-17 | 2026-07-18 | 0006, 0011, 0012, 0017 | AGENTS.md, CLAUDE.md, CONTRIBUTING.md, README.md, architecture.md, architecture/learning_dataset.md, database/schema.md, knowledge/README.md, src/README.md |
| [0014](0014-development-discipline.md) | 開発規律 | Accepted | 2026-07-17 | 2026-07-17 | 0002, 0003, 0005, 0011 | AGENTS.md, CLAUDE.md, CONTRIBUTING.md, README.md, architecture.md, knowledge/schema.md, src/README.md |
| [0015](0015-sqlite-schema-finalization.md) | SQLiteスキーマの確定 | Accepted | 2026-07-17 | 2026-07-17 | 0001, 0004, 0006, 0011, 0012, 0013 | data_model.md, database/schema.md |
| [0016](0016-public-json-format.md) | 公開JSON形式の確定 | Accepted | 2026-07-18 | 2026-07-18 | 0010, 0014, 0015 | database/schema.md, database/json_schema.md |
| [0017](0017-learning-dataset-field-expansion.md) | Learning Datasetのフィールド拡張・ライフサイクル定義 | Accepted | 2026-07-18 | 2026-07-18 | 0007, 0013, 0015 | architecture.md, architecture/learning_dataset.md, database/schema.md, knowledge/learning_dataset/README.md |

## 新規追加ADR（Gap Analysis対応、[`gap-analysis.md`](gap-analysis.md)参照）

| # | タイトル | ステータス | 作成日 | 最終更新日 | 関連ADR | 関連ドキュメント |
|---|---|---|---|---|---|---|
| [0018](0018-pdf-registry-and-retention.md) | PDF Registry・長期保管方針 | Accepted | 2026-07-18 | 2026-07-18 | 0006, 0008 | database/schema.md |
| [0019](0019-workflow-orchestration.md) | 実行オーケストレーション（Workflow）戦略 | Accepted | 2026-07-18 | 2026-07-18 | 0006, 0010, 0011 | database/schema.md |
| [0020](0020-benchmark-dataset.md) | ベンチマークデータセット戦略 | Accepted | 2026-07-18 | 2026-07-18 | 0007, 0017 | — |
| [0021](0021-review-ui-strategy.md) | レビュー用インターフェース（Review UI）戦略 | Accepted | 2026-07-18 | 2026-07-18 | 0006, 0013, 0017 | database/schema.md |
| [0022](0022-export-policy.md) | エクスポート運用方針（Export Policy） | Accepted | 2026-07-18 | 2026-07-18 | 0010, 0016 | database/schema.md |
| [0023](0023-parser-versioning-policy.md) | Parserバージョニング方針 | Accepted | 2026-07-18 | 2026-07-18 | 0006, 0015 | database/schema.md |
| [0024](0024-knowledge-versioning-and-backfill.md) | Knowledgeバージョニング・再処理（Backfill）方針 | Accepted | 2026-07-18 | 2026-07-18 | 0005, 0012, 0013 | knowledge/schema.md |
| [0025](0025-deployment-strategy.md) | デプロイメント戦略 | Accepted | 2026-07-18 | 2026-07-18 | 0004, 0010, 0019 | — |
| [0026](0026-security-policy.md) | セキュリティポリシー | Accepted | 2026-07-18 | 2026-07-18 | 0008, 0025 | — |

## Review Domainの中核化に伴い追加したADR

| # | タイトル | ステータス | 作成日 | 最終更新日 | 関連ADR | 関連ドキュメント |
|---|---|---|---|---|---|---|
| [0027](0027-review-domain-elevation.md) | Review Domainの中核化 | Accepted | 2026-07-18 | 2026-07-18 | 0010, 0021 | docs/review/, api/review.md, architecture/architecture-contract.md |
| [0028](0028-pydantic-settings-for-configuration.md) | 設定管理へのPydantic Settings採用 | Accepted | 2026-07-18 | 2026-07-18 | 0001, 0002, 0026 | configuration.md, api/python-contract.md, api/package-design.md |

## 検討したが採用しなかった候補

`Feature Store` は本プロジェクトの性質（決定的なPDF解析パイプラインであり、機械学習の特徴量管理を必要としない）と合致しないため、ADRを起票しなかった。判断理由の詳細は [`gap-analysis.md`](gap-analysis.md#feature-store) を参照。
