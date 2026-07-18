# 0020. ベンチマークデータセット戦略

## ステータス
Accepted

## コンテキスト

[ADR-0007](0007-golden-file-testing.md)のゴールデンファイルテスト（`sample_pdfs`/`sample_outputs`）は、様式ごとに最小限の代表サンプルを用いた**回帰検知**（既存の処理を壊していないかの合否判定）を目的とする。これは「壊れていないか」には答えられるが、「全体としてどの程度正確に抽出できているか」という**量的な品質指標**の継続的な計測には向かない設計である（[`sample_pdfs/README.md`](../../sample_pdfs/README.md)が意図的に件数を絞っているため）。[ADR-0017](0017-learning-dataset-field-expansion.md)のLearning Datasetは個々の誤り事例を蓄積するが、「正しく処理できた件数」を含む分母を持たないため、精度の分母・分子を揃えた品質指標にはならない。この量的な品質計測手段の欠落は[Gap Analysis](gap-analysis.md#benchmark-dataset)で指摘した通りである。

## 決定

- ゴールデンファイルテストとは別に、実運用データから抽出した、より大規模で継続的に更新される**ベンチマークデータセット**を用意する。人手で正解ラベル（gold相当のデータ）を付与し、様式・期間の分布が実運用の実態を代表するよう構成する。
- ベンチマークデータセットの実体（PDFおよび正解ラベル）は、個人情報を含み得る実データであるため、リポジトリ内には置かず、[ADR-0018](0018-pdf-registry-and-retention.md)のPDF実体ストレージと同様の外部データストアに保持する。公開範囲は[ADR-0008](0008-data-ethics-policy.md)に従う。
- 新しい`parser_version`（[ADR-0023](0023-parser-versioning-policy.md)）がリリースされるたびに、ベンチマークデータセット全体に対して評価を実行し、以下を算出する。
  - 様式（`era_id`）別・期間別のValidator通過率
  - Confidenceバンド（[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)）の分布
  - Learning Dataset（[ADR-0017](0017-learning-dataset-field-expansion.md)）の新規発生率
- 算出結果は、実装時に整備する`docs/operations/`のレポートとして記録し、リリースごとの品質推移を追跡可能にする。

## 検討した代替案

- **`sample_pdfs`/`sample_outputs`の件数を単純に増やし、量的指標もそこから算出する**: [ADR-0007](0007-golden-file-testing.md)が意図する「様式ごとに最小限」というリポジトリ肥大化回避の設計方針に反する。目的（回帰検知 vs 量的品質計測）が異なるデータセットとして明確に分離する方針とした。

## 結果（トレードオフ）

- ベンチマークデータセットの構築・維持・匿名化/取り扱いには追加のコストと運用ルールが必要になる。
- 一方で、「動いているように見えて実は精度が徐々に劣化している」という問題を、リリースのたびに定量的に検知できるようになる。
