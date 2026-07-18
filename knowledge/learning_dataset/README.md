# knowledge/learning_dataset/

## 責務

Validatorでの検証NG、および公開後に判明した誤りを、**Correction Log（単なる修正の追記ログ）ではなく、Learning Dataset（システム改善のための構造化データセット）として**保持する場所。設計方針は [ADR-0013](../../docs/adr/0013-learning-dataset-not-correction-log.md)、保持フィールド・ライフサイクルの詳細仕様は [`docs/architecture/learning_dataset.md`](../../docs/architecture/learning_dataset.md)（[ADR-0017](../../docs/adr/0017-learning-dataset-field-expansion.md)）を参照。

実データは主に `learning_dataset` DBテーブル（[`docs/database/schema.md`](../../docs/database/schema.md#9-learning_dataset)）として保持する。本ディレクトリはその設計思想・エントリ内容の説明を置く場所であり、`knowledge/` の他8カテゴリ（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md)）のようなYAMLファイル群としては管理しない（誤り修正情報はパイプラインが生成する運用データであり、人手で参照・追加する定義データとは性質が異なるため）。

## `knowledge/layout_notes/` との違い

| | `layout_notes/` | `learning_dataset/` |
|---|---|---|
| 性質 | 定性的な知見（PDFの癖・対応方針） | 個々の誤り事例の構造化データ |
| 単位 | パターン・傾向 | 1件1件の具体的な誤り |
| 主な用途 | 実装者が事前に把握しておくべき注意点 | 誤りの分類集計、Knowledge Base/Layoutの手薄な領域の可視化 |

両者は補完関係にあり、`learning_dataset/`（DB上の `learning_dataset` テーブル）に同種の誤りが繰り返し蓄積された場合、その傾向を `layout_notes/` に定性的な知見として記録することもある。

## 保持する情報

詳細は [`docs/architecture/learning_dataset.md`](../../docs/architecture/learning_dataset.md#保持するフィールド) を参照。概要:

- 修正内容（対象フィールド・誤った値・正しい値・要約）、Reviewerコメント、改善候補
- 由来（`source_candidate_record_id` 等、来歴 [ADR-0006](../../docs/adr/0006-pipeline-provenance.md)）、Parser Version、Layout（`era_id`）
- 誤りが生じた中核パイプライン段階（[ADR-0011](../../docs/adr/0011-fixed-core-pipeline.md)）、原因分類（[ADR-0012](../../docs/adr/0012-error-handling-priority-order.md)）
- Confidence（信頼度スコア・バンド）
- 反映先（Git Commit・Pull Request・`knowledge/`/`layouts/`への参照）、Regression結果

## 方針

- Validatorが検証NGを検出した時点、および人手レビューで誤りが確定した時点の両方が入力になる。
- 「監査のための記録」で終わらせず、蓄積されたエントリを定期的に見直し、Knowledge Base・Layoutの拡充につなげる（未知パターンへの対応優先順位、[ADR-0012](../../docs/adr/0012-error-handling-priority-order.md)）。
- 反映（`knowledge/`/`layouts/`への変更）は、対応するGit Commit・Pull Requestまで追跡し、リグレッションテスト（[ADR-0007](../../docs/adr/0007-golden-file-testing.md)）による検証をもって完結とする（[`docs/architecture/learning_dataset.md`](../../docs/architecture/learning_dataset.md#ライフサイクル)のライフサイクル参照）。
- 個人情報の取り扱い範囲は [ADR-0008](../../docs/adr/0008-data-ethics-policy.md) の方針に従う。
