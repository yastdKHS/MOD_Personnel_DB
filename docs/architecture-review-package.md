# Architecture Review Package

> Task 1〜9（リポジトリ全体設計・ADR統治基盤・Interface & Package設計・Review Domain設計）の成果物のうち、Architecture Reviewに提出する範囲を以下に限定してまとめる。**本文を複製せず**、各ファイルへのリンクと一行要約のみを示す（実体は各リンク先を正とする、単一情報源の原則）。ADR一覧は番号・タイトル・Status・依存ADRのみとし、本文は含めない（指示どおり）。
>
> 対象範囲外（本パッケージに含まれないもの）: `docs/database/`（SQLite物理スキーマ・公開JSON仕様）, `docs/api/package-design.md` / `python-contract.md`, `docs/architecture.md` / `docs/architecture/learning_dataset.md`, `docs/data_model.md`, ADR本文, `README.md`系。これらは提出範囲外のため本パッケージには載せない。

## 提出物サマリ

| 区分 | 件数 |
|---|---|
| Review Domain（`docs/review/`） | 4 |
| Interface & Package API（`docs/api/`） | 7 |
| Architecture Contract（`docs/architecture/`） | 1 |
| Knowledge Schema（`docs/knowledge/`） | 1 |
| ADR | 27（0001〜0027、一覧のみ） |

---

## 1. `docs/review/`

| ファイル | 要約 |
|---|---|
| [`domain.md`](review/domain.md) | Review Lifecycle状態遷移図（Mermaid、Candidate→Assigned→InReview→Modified→Approved→GoldDatabase→JSONExport→FTP、差戻し・再レビュー分岐込み）と6ドメインモデル（`ReviewSession`, `ReviewAssignment`, `ReviewDecision`, `ReviewComment`, `ReviewHistory`, `ReviewStatistics`） |
| [`policy.md`](review/policy.md) | 承認権限、差戻し、再レビュー、Confidence Override、Knowledge追加条件、Learning Dataset登録条件、Gold更新条件（4条件）の7ポリシー |
| [`queue.md`](review/queue.md) | レビューキューの優先順位を固定順序でなく連続スコアで算出する式（`layout_unknown` / `parser_error` / `confidence` / `knowledge_missing` / `reviewer_request` + 経過時間補正） |
| [`metrics.md`](review/metrics.md) | Review Time / Correction Rate / Approval Rate / Knowledge Update Rate / Layout Update Rate / Learning Growth の定義・算出式・データ源 |

## 2. `docs/api/`

| ファイル | 要約 |
|---|---|
| [`review.md`](api/review.md) | `ReviewService` / `ReviewRepository`（拡張）/ `ReviewEvent` / `ReviewDecision` / `ReviewNotification`の公開API型シグネチャ |
| [`interfaces.md`](api/interfaces.md) | 中核パイプライン6段階（`run()`のみ公開）+ 9サービス、計15コンポーネントの公開API |
| [`pipeline.md`](api/pipeline.md) | `PipelineContext` / `PipelineStage` / `PipelineResult` / `PipelineEvent` / `PipelineException` / `PipelineMetrics` |
| [`repositories.md`](api/repositories.md) | 8 Repository（`CandidateRepository`等）+ `UnitOfWork`。SQLite非依存・PostgreSQL移行可能な設計原則 |
| [`models.md`](api/models.md) | `Document`等13ドメインモデルの属性・不変条件・Validation Rule |
| [`dependency-rule.md`](api/dependency-rule.md) | 全21パッケージのMermaid依存関係図、禁止/許可パターン、合成ルート（Composition Root）の設計 |
| [`import-graph.md`](api/import-graph.md) | 21パッケージ・47エッジのimportグラフと、循環参照が存在しないことの検証（DFS彩色法+Kahnのアルゴリズムの二重チェック、発見・修正した循環参照バグの記録を含む） |

## 3. `docs/architecture/`

| ファイル | 要約 |
|---|---|
| [`architecture-contract.md`](architecture/architecture-contract.md) | 9つの分離保証（Document Analyzerはlayoutを知らない／Layout Detectorはfieldを知らない／Section Parserはknowledgeを知らない／Field ExtractorはDBを知らない／Normalizerは正規表現を持たない／Validatorは修正しない／RepositoryはSQLiteを隠蔽する／Reviewはgold_recordsだけ更新できる／Reviewだけがgold_recordsを書き換えられる）とその実現方法・検証方法 |

## 4. `docs/knowledge/`

| ファイル | 要約 |
|---|---|
| [`schema.md`](knowledge/schema.md) | `knowledge/`8カテゴリ（organization/position/rank/alias/historical/typography/layout/validation）のYAML Schema（JSON Schema Draft 2020-12）、カテゴリごとのVersion管理・Validation Rule・更新ルール |

---

## 5. ADR一覧（番号・タイトル・Status・依存ADR）

| # | タイトル | Status | 依存ADR |
|---|---|---|---|
| 0001 | Pythonパッケージング・ビルドバックエンドの選定 | Accepted | — |
| 0002 | Lint / Format / 型チェックツールの選定 | Accepted | — |
| 0003 | PDFレイアウトの外部データ定義化 | Accepted | 0007, 0011, 0012 |
| 0004 | データストアとしてのSQLite採用 | Accepted | — |
| 0005 | ドメイン知識ベースによる名寄せ・正規化戦略 | Accepted | 0003, 0012, 0013 |
| 0006 | パイプライン段階分割と来歴（Provenance）管理 | Accepted | 0011, 0013 |
| 0007 | ゴールデンファイルテスト戦略 | Accepted | — |
| 0008 | 個人情報・データ倫理方針 | Accepted | — |
| 0009 | AIコーディングエージェント運用方針 | Accepted | 0008 |
| 0010 | CI/CDと公開戦略 | Accepted | 0006 |
| 0011 | 中核処理パイプラインの固定化 | Accepted（変更に高いハードル。Supersedeにはプロジェクトオーナーの明示的承認を要する） | 0003, 0005, 0006, 0012, 0014 |
| 0012 | 未知パターンへの対応優先順位（Knowledge Base > Layout > 例外処理） | Accepted | 0003, 0005, 0011 |
| 0013 | 誤り修正情報を Correction Log ではなく Learning Dataset として設計する | Accepted | 0006, 0011, 0012, 0017 |
| 0014 | 開発規律（設計品質優先・1PR1責務・関数サイズ制限） | Accepted | 0002, 0003, 0005, 0011 |
| 0015 | SQLiteスキーマの確定 | Accepted | 0001, 0004, 0006, 0011, 0012, 0013 |
| 0016 | 公開JSON形式（JSON Schema Draft 2020-12）の確定 | Accepted | 0010, 0014, 0015 |
| 0017 | Learning Datasetのフィールド拡張・ライフサイクル定義 | Accepted | 0007, 0013, 0015 |
| 0018 | PDF Registry・長期保管方針 | Accepted | 0004, 0006, 0007 |
| 0019 | 実行オーケストレーション（Workflow）戦略 | Accepted | 0010, 0011, 0025 |
| 0020 | ベンチマークデータセット戦略 | Accepted | 0007, 0008, 0017, 0018, 0023 |
| 0021 | レビュー用インターフェース（Review UI）戦略 | Accepted | 0001, 0017 |
| 0022 | エクスポート運用方針（Export Policy） | Accepted | 0001, 0007, 0010, 0015, 0016 |
| 0023 | Parserバージョニング方針 | Accepted | 0006, 0010, 0011 |
| 0024 | Knowledgeバージョニング・再処理（Backfill）方針 | Accepted | 0001, 0005, 0012, 0014, 0015 |
| 0025 | デプロイメント戦略 | Accepted | 0001, 0004, 0010, 0018, 0019, 0022 |
| 0026 | セキュリティポリシー | Accepted | 0001, 0008, 0010, 0011, 0019, 0025 |
| 0027 | Review Domainの中核化 | Accepted | 0010, 0021 |

全27件、Statusはすべて`Accepted`（`Proposed`/`Superseded`/`Deprecated`のものはない）。ADR本体・コンテキスト・検討した代替案等の詳細は`docs/adr/`配下の各ファイル、およびメタデータ台帳[`docs/adr/index.md`](adr/index.md)を参照（本パッケージの提出範囲外）。
