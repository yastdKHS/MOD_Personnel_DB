# 0024. Knowledgeバージョニング・再処理（Backfill）方針

## ステータス
Accepted

## コンテキスト

[`docs/knowledge/schema.md`](../knowledge/schema.md)はエントリ単位の`VersionInfo`（`version` / `updated_at`）を定義し、`parser_versions.knowledge_snapshot_checksum`（`docs/database/schema.md`）は知識ベース全体のスナップショットをハッシュで再現可能にしている。ここまでは[ADR-0005](0005-knowledge-base-normalization.md)・[ADR-0015](0015-sqlite-schema-finalization.md)でカバー済みである。欠落していたのは、**`knowledge/`が変更されたとき、既に公開済みの過去データ（`gold_records`）をどこまで遡って再処理（バックフィル）するか**という運用ポリシーである（[Gap Analysis](gap-analysis.md#knowledge-versioning)参照）。

## 決定

- `knowledge/`への変更（組織改称の追加等）は、既定では**将来のPDF処理にのみ適用**し、過去に確定済みの`gold_records`を自動的に再処理しない。無制限の自動再処理は、蓄積データ全体を毎回再計算するコストが大きく、また意図しない大量の訂正が突発的に発生するリスクを伴うため。
- 広範囲な誤り（例: ある組織名の誤りが多数のレコードに影響していたと判明した場合）が発覚した場合は、`scripts/`（[ADR-0001](0001-python-packaging.md)のディレクトリ構成）配下の明示的なバックフィルジョブとして、対象範囲（期間・様式・組織等）を人手で指定して実行する。
- バックフィル実行は`jobs`テーブルに`job_type='backfill'`として記録する（`docs/database/schema.md`の`jobs.job_type`列挙に既に含まれる値を使用）。
- バックフィルにより変更された`gold_records`は、通常の訂正と同様に新バージョンとして追加し（[ADR-0015](0015-sqlite-schema-finalization.md)のSCD Type 2設計）、変更理由に「どの`knowledge/`変更に起因するバックフィルか」を記録する。バックフィルの要否判断には、[Learning Dataset](../architecture/learning_dataset.md)の`error_category`別集計（[ADR-0012](0012-error-handling-priority-order.md)の分類）を判断材料として用いる。

## 検討した代替案

- **`knowledge/`変更のたびに全件自動バックフィルする**: 処理コストとリスクが大きく、[ADR-0014](0014-development-discipline.md)の過剰設計回避の精神に反するため見送った。
- **バックフィルを一切行わない（将来分のみ反映）**: 広範囲な誤りが判明した場合に是正手段がなくなるため、明示的な手動トリガーによる手段は残す方針とした。

## 結果（トレードオフ）

- バックフィルの要否判断は人手に委ねられるため、判断基準・実行手順の詳細は`docs/operations/`（実装時整備）に別途まとめる必要がある。
- 「将来分のみ適用」を既定とすることで、過去データの意図しない大量変更を防げる一方、誤りの是正が遅れる可能性がある点はトレードオフとして受け入れる。
