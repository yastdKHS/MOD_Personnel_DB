# ADR Gap Analysis

> 現在のADR群（0001〜0017）とそれに付随する設計文書（`docs/architecture.md`, `docs/database/schema.md`, `docs/database/json_schema.md`, `docs/knowledge/schema.md`, `docs/architecture/learning_dataset.md`）を棚卸しし、10年運用を前提としたときに欠けている設計判断を抽出する。候補は10件（Task指示による例示）とし、それぞれについて「既存ADRでカバー済みか」「真の欠落か」を判定し、欠落と判定したもののみ新規ADR（0018〜0026）を追加する。

## 判定基準

1. 既存のADR・設計文書で実質的に決定済みか（カバー済みなら新規ADR不要）
2. 本プロジェクトの性質（決定的なPDF解析パイプライン、10年運用、公的データの節度ある公開）に照らして本当に必要な決定か（不要な過剰設計を避ける、[ADR-0014](0014-development-discipline.md)の精神）
3. 決定しないまま実装が進むと、後戻りコストの大きい設計のブレが生じるか

## 候補ごとの判定

### PDF Registry

**判定: 欠落 → [ADR-0018](0018-pdf-registry-and-retention.md) を追加**

`docs/database/schema.md` の `pdfs` テーブルは、取得したPDFのメタデータ（ハッシュ・取得元・取得日時）をDB上で管理する設計を持つが、以下は未決定だった。

- 実PDFファイル本体の長期保管場所（DBには`file_path`列があるのみで、その先の実体をどこに・どれだけの期間・どう保持するか）
- 同一内容のPDFを異なるURLから複数回取得した場合の重複排除の運用（`content_hash`のUNIQUE制約はあるが、運用フローとしての扱いは未定義）
- 取得に失敗した場合のリトライ・欠番の扱い

[ADR-0006](0006-pipeline-provenance.md)は「来歴を追跡できること」を要求するが、追跡**対象の実体をどこにどう置くか**までは決めていない。ADR-0006の"上位方針"を具体化する形で、ADR-0018を追加する。

### Feature Store

**判定: 不採用（対象外）**

Feature Storeは機械学習における特徴量の管理基盤（学習・推論間での特徴量の一貫性担保、オンライン/オフライン特徴量ストアの同期等）を指す概念である。本プロジェクトの中核パイプライン（[ADR-0011](0011-fixed-core-pipeline.md)）は決定的（deterministic）なルールベース処理であり、機械学習モデルの学習・推論を行わない（[ADR-0003](0003-layout-definition-strategy.md)の「PDFレイアウトを都度LLMに解釈させる」代替案を明示的に見送った判断とも整合する）。Learning Dataset（[ADR-0013](0013-learning-dataset-not-correction-log.md)）は名称にDatasetを含むが、これは「人間が改善のために参照する構造化データ」であり、機械学習の特徴量管理とは異なる。将来、抽出精度向上のために機械学習的手法を導入する場合は、その時点で新規ADRとして技術選定から検討すべきであり、現時点でFeature Store関連のADRを先回りして作ることは過剰設計と判断した。

**追記（Interface & Package Design、[`docs/api/interfaces.md`](../api/interfaces.md)）**: 後続のインターフェース設計タスクで、`features/`パッケージ・`FeatureStore`インターフェース・`FeatureVector`モデルを設計した。これは本判定を覆すものではない。ここでの`FeatureStore`は機械学習モデルの学習・推論基盤ではなく、Validatorの[Confidence算出](../database/json_schema.md#confidenceの算出ルール)を補助する**決定的な特徴量計算ユーティリティ**（OCR品質シグナル・レイアウト判定信頼度・過去の誤り発生率等）であり、永続ストレージも持たない（[`docs/api/package-design.md`](../api/package-design.md)の`features/`節参照）。「機械学習の学習・推論基盤としてのFeature Store」を導入したい場合は、引き続き本判定のとおり新規ADRを要する。

### Workflow Engine

**判定: 欠落 → [ADR-0019](0019-workflow-orchestration.md) を追加**

[ADR-0010](0010-ci-cd-and-publish-strategy.md)はCIと公開判断のガバナンス（人手ゲート、forward-only）を定めるが、「取得（Fetch）から中核パイプライン、公開（Publish）までの一連の処理を、実運用でいつ・どうやって実行するか」（定期実行のトリガー、失敗時のリトライ、実行環境）は未決定だった。`jobs`テーブル（`docs/database/schema.md`）は実行結果の記録先として設計済みだが、その実行を起動する仕組み（cron、GitHub Actions scheduled workflow、外部ワークフローエンジン等）の選定は行っていない。10年運用において、この選定は「枯れた技術を選ぶ」（[ADR-0001](0001-python-packaging.md)）方針を適用すべき重要な技術選定であり、ADR-0019として追加する。

### Benchmark Dataset

**判定: 欠落 → [ADR-0020](0020-benchmark-dataset.md) を追加**

[ADR-0007](0007-golden-file-testing.md)の`sample_pdfs`/`sample_outputs`は、**様式ごとの代表例に対する回帰（regression）テスト**であり、「様式ごとに最低1件」という最小構成を意図的に取っている（[`sample_pdfs/README.md`](../../sample_pdfs/README.md)）。これは「壊れていないか」を検知する目的には十分だが、「どの程度正確に抽出できているか」という**量的な品質指標**（例: 全体の抽出精度、様式別の信頼度分布の推移）を継続的に計測する目的には向かない。[ADR-0017](0017-learning-dataset-field-expansion.md)のLearning Datasetは個々の誤り事例を蓄積するが、「正しく処理できた件数」を含めた分母を持つ品質指標ではない。ゴールデンファイルテスト（少数・厳密な回帰検知）とは別に、**継続的な品質計測のためのベンチマークデータセット**の設計判断が欠落していると判定し、ADR-0020を追加する。

### Review UI

**判定: 欠落 → [ADR-0021](0021-review-ui-strategy.md) を追加**

`review_sessions`/`review_changes`テーブル（`docs/database/schema.md`）は、人手レビューの**記録先**を定義しているが、レビュー担当者が実際に「どうやって検証NGの一覧を見て、値を修正するか」というインターフェース（CLIツール、Webアプリ、スプレッドシート連携等）は未決定だった。10年運用で複数の担当者が交代することを前提とすると（[AGENTS.md](../../AGENTS.md)）、属人化しない形でこの作業ツールを設計する必要があり、ADR-0021を追加する。

### Export Policy

**判定: 部分的に欠落 → [ADR-0022](0022-export-policy.md) を追加**

[ADR-0010](0010-ci-cd-and-publish-strategy.md)は公開フロー全体のガバナンス（人手ゲート）を、[ADR-0016](0016-public-json-format.md)はJSON形式の詳細契約を定めているが、`exports.format`は`csv`/`parquet`/`json`の3形式を許容しながら、**CSV・Parquetの形式仕様・スキーマバージョニング**はJSON同様の厳密さで定義されていない。また、公開の頻度（cadence）・過去エクスポートの提供期間・アクセス方法（配布先）といった運用面のポリシーも未決定である。JSON契約の詳細は[ADR-0016](0016-public-json-format.md)がカバー済みのため重複させず、ADR-0022では**形式横断の運用ポリシー**（頻度・CSV/Parquetの最小契約・提供方法）に限定して追加する。

### Parser Versioning

**判定: 欠落 → [ADR-0023](0023-parser-versioning-policy.md) を追加**

`parser_versions`テーブル（`docs/database/schema.md`）と、公開JSON形式の3層バージョン管理（[`docs/database/json_schema.md`](../database/json_schema.md#バージョン管理)、DBスキーマバージョン／データ生成バージョン／公開JSON形式バージョン）は既に設計済みである。しかし、**データ生成バージョン（`parser_versions.code_version`）自体がどう採番されるか**（コミットハッシュか、SemVerタグか）、**いつ新しい`parser_versions`行が作られるか**（マージのたびか、リリースのたびか）は未決定だった。この決定が曖昧なままだと、来歴追跡（[ADR-0006](0006-pipeline-provenance.md)）の粒度が実装者ごとにブレる。ADR-0023として、独立した「第4のバージョン軸」を明確化する。

### Knowledge Versioning

**判定: 部分的に欠落 → [ADR-0024](0024-knowledge-versioning-and-backfill.md) を追加**

`docs/knowledge/schema.md`はエントリ単位の`VersionInfo`（`version`/`updated_at`）を定義済みであり、`parser_versions.knowledge_snapshot_checksum`（`docs/database/schema.md`）により知識ベース全体のスナップショットはハッシュで再現可能である。ここまでは既存ADR（[ADR-0005](0005-knowledge-base-normalization.md), [ADR-0015](0015-sqlite-schema-finalization.md)）でカバー済み。欠落しているのは、**`knowledge/`が変更されたとき、既に公開済みの過去データ（`gold_records`）をどこまで遡って再処理（バックフィル）するか**という運用ポリシーである。例えば組織改称エントリを追加した場合、過去に誤って正規化された全レコードを再処理すべきか、今後の新規PDFのみに適用するかは、データの一貫性と処理コストのトレードオフを伴う重要な決定であり、ADR-0024として追加する。

### Deployment Strategy

**判定: 欠落 → [ADR-0025](0025-deployment-strategy.md) を追加**

[ADR-0004](0004-sqlite-as-datastore.md)はデータストアの選定を、[ADR-0010](0010-ci-cd-and-publish-strategy.md)はCI/CDのガバナンスを定めるが、**本番運用のシステムがどこで・どのように稼働するか**（ローカルバッチ実行、コンテナ、サーバーレス、常時稼働サーバー等）という実行環境そのものの選定は未決定だった。SQLite（単一ファイルDB）という選定はデプロイ形態の選択肢を狭める（例えば複数プロセスからの同時書き込みが必要な構成とは相性が悪い）ため、デプロイ戦略はADR-0004と整合させる形で明示的に決定する必要があり、ADR-0025を追加する。

### Security Policy

**判定: 欠落 → [ADR-0026](0026-security-policy.md) を追加**

[ADR-0008](0008-data-ethics-policy.md)は個人情報・データ倫理（収集範囲の限定）を定めるが、これは「データの取り扱い」の方針であり、システムとしての**セキュリティ**（秘匿情報管理、依存ライブラリの脆弱性対応、外部由来のPDFファイルを解析することに伴うリスク——PDFパーサーの既知の脆弱性、圧縮爆弾、リソース枯渇攻撃等——への対策方針）は別の関心事として未決定だった。`.pre-commit-config.yaml`にgitleaks（秘密情報の誤コミット検知）は既に組み込まれているが、これは実装上の一施策であり、包括的な方針を定めるADRは存在しなかったため、ADR-0026を追加する。

## まとめ

| 候補 | 判定 | 追加ADR |
|---|---|---|
| PDF Registry | 欠落 | 0018 |
| Feature Store | 対象外 | — |
| Workflow Engine | 欠落 | 0019 |
| Benchmark Dataset | 欠落 | 0020 |
| Review UI | 欠落 | 0021 |
| Export Policy | 部分的に欠落 | 0022 |
| Parser Versioning | 欠落 | 0023 |
| Knowledge Versioning | 部分的に欠落 | 0024 |
| Deployment Strategy | 欠落 | 0025 |
| Security Policy | 欠落 | 0026 |

9件を新規ADRとして追加し、1件（Feature Store）は本プロジェクトの性質と合致しないため見送った。既存ADR（0001〜0017）は一切変更していない。
