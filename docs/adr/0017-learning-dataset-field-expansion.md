# 0017. Learning Datasetのフィールド拡張・ライフサイクル定義

## ステータス
Accepted

## コンテキスト

[ADR-0013](0013-learning-dataset-not-correction-log.md) は「誤り修正情報をCorrection LogではなくLearning Datasetとして設計する」という方針を決定したが、具体的にどのフィールドを保持し、どのライフサイクルで運用するかは、[`docs/database/schema.md`](../database/schema.md) 初版の `learning_dataset` テーブル（`wrong_value` / `correct_value` / `status`(`open`/`reflected`/`wontfix`) 等の最小構成）にとどまっていた。実運用を見据えると、修正内容の詳細・レビュー担当者の所見・信頼度・再発防止の反映先（コード変更の追跡）・リグレッション検証結果まで一貫して追跡できなければ、[ADR-0013](0013-learning-dataset-not-correction-log.md) が目指す「システム改善のための学習材料」という性質を十分に果たせない。`docs/adr/README.md` の「いつADRを書くか」に定める「データモデルの決定・変更」に該当するため、本ADRを起票する。

## 決定

- Learning Datasetが保持するフィールドとライフサイクルの詳細設計を [`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md) として策定する。本ADRはその内容を正式決定として承認するものであり、個々のフィールド定義・状態遷移の詳細は同ドキュメントを正とする。
- `learning_dataset` テーブルに以下を追加する（非破壊的な列追加が中心）: `field_name` / `correction_summary`（修正内容）、`reviewer_comment`（Reviewerコメント）、`parser_version_id`（Parser Version）、`layout_id`（Layout）、`confidence_score` / `confidence_band`（Confidence）、`git_commit_hash`（Git Commit）、`pull_request_url`（Pull Request）、`regression_status` / `regression_run_at` / `regression_details`（Regression結果）、`improvement_candidate`（改善候補）。既存の `error_category` を「原因分類」に、既存の `reflected_in_*` を「修正内容」の反映先として引き続き用いる。
- `status` の許容値を `open` / `reflected` / `wontfix` の3状態から、`open` / `in_review` / `reflected` / `verified` / `wontfix` の5状態に拡張し、リグレッション検証を経て初めて完結するライフサイクルとして再定義する。
- `correct_value` を `NOT NULL` から任意（nullable）に変更する。`open` 状態（Validator自動検出直後）では正しい値が未確定のため。

## 検討した代替案

- **既存フィールドを変更せず、修正内容等の詳細情報は `review_changes` 側にのみ持たせる**: `review_changes` は人手レビュー全般の変更履歴であり、Learning Dataset特有の分析観点（Parser Version別・様式別の傾向、Confidenceとの相関、リグレッション結果）を表現するには不十分。Learning Dataset側にも必要なフィールドを直接持たせる（一部`parser_version_id`/`layout_id`は分析利便性のための意図的な非正規化）方針とした。
- **`status` を3状態のまま維持し、リグレッション結果を別テーブルで管理する**: シンプルだが、[ADR-0007](0007-golden-file-testing.md)のゴールデンファイルテストとLearning Datasetの結びつきが弱くなり、「反映したが検証していない」状態を追跡できない。5状態への拡張により、この状態を明示的に表現する方針とした。

## 結果（トレードオフ）

- フィールド数の増加により `learning_dataset` テーブルはやや複雑になるが、すべて `NULL` 許容またはデフォルト値ありの非破壊的な追加であり、既存設計（[ADR-0015](0015-sqlite-schema-finalization.md)）との後方互換性は保たれる。
- `layout_id`（発生コンテキスト）と `reflected_in_layout_id`（反映結果）を意図的に別カラムとしたことで、「誤りの発生源」と「対応した箇所」を混同しない設計になる一方、両者の使い分けをドキュメント（[`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md)）で明確に説明する責任が生じる。
