# knowledge/learning_dataset/

## 責務

Validatorでの検証NG、および公開後に判明した誤りを、**Correction Log（単なる修正の追記ログ）ではなく、Learning Dataset（システム改善のための構造化データセット）として**保持する場所。設計判断の背景は [ADR-0013](../../docs/adr/0013-learning-dataset-not-correction-log.md) を参照。

## `knowledge/known_issues/` との違い

| | `known_issues/` | `learning_dataset/` |
|---|---|---|
| 性質 | 定性的な知見（PDFの癖・対応方針） | 個々の誤り事例の構造化データ |
| 単位 | パターン・傾向 | 1件1件の具体的な誤り |
| 主な用途 | 実装者が事前に把握しておくべき注意点 | 誤りの分類集計、Knowledge Base/Layoutの手薄な領域の可視化 |

両者は補完関係にあり、`learning_dataset/` に同種の誤りが繰り返し蓄積された場合、その傾向を `known_issues/` に定性的な知見として記録することもある。

## 想定するエントリの内容

各エントリは最低限、以下の情報を持つ（具体的なファイル形式・スキーマは実装着手時に確定する）。

- 由来する `source_documents`（来歴、[ADR-0006](../../docs/adr/0006-pipeline-provenance.md)）
- 誤りが生じた中核パイプライン段階（Layout Detector / Section Parser / Field Extractor / Normalizer / Validator のいずれか、[ADR-0011](../../docs/adr/0011-fixed-core-pipeline.md)）
- 誤って抽出・正規化された値と、正しい値
- 誤りの分類（未知の表記ゆれ / 未知の様式 / Knowledge Base欠落 / Layout欠落 / 真の例外、[ADR-0012](../../docs/adr/0012-error-handling-priority-order.md) の優先順位分類に対応）
- この修正が `knowledge/`（他ディレクトリ）または `layouts/` への反映につながったか、つながった場合はその参照

## 方針

- Validatorが検証NGを検出した時点、および人手レビューで誤りが確定した時点の両方が、本ディレクトリへの入力になる。
- 「監査のための記録」で終わらせず、蓄積されたエントリを定期的に見直し、Knowledge Base・Layoutの拡充につなげる（未知パターンへの対応優先順位、[ADR-0012](../../docs/adr/0012-error-handling-priority-order.md)）。
- 個人情報の取り扱い範囲は [ADR-0008](../../docs/adr/0008-data-ethics-policy.md) の方針に従う。
