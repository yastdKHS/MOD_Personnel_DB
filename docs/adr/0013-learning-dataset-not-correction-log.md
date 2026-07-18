# 0013. 誤り修正情報を Correction Log ではなく Learning Dataset として設計する

## ステータス
Accepted

## コンテキスト

[ADR-0006](0006-pipeline-provenance.md) は、Validatorで検証NGとなったデータを「サイレントに破棄せず、要確認キューとして保持する」と定めた。この「検証NG・人手修正の記録」をどう設計するかについて、素朴な実装は「修正ログ（Correction Log）」——すなわち「いつ・誰が・どの値をどう直したか」を追記するだけの監査ログ——になりがちである。

Correction Logは監査目的には十分だが、10年運用のプロジェクトとしては機会損失が大きい。修正のたびに同種の誤りが繰り返されるなら、その修正情報は本来 `layouts/` や `knowledge/` の改善に還元されるべき資産である。単なるログでは、この「システムを改善するための学習材料」という性質が失われる。

## 決定

誤り修正情報は、**Correction Log（監査用の追記ログ）としてではなく、Learning Dataset（システム改善のための構造化データセット）として設計する**。

Learning Datasetの各エントリは、最低限以下を保持する（具体的なスキーマは実装時に確定するが、この情報粒度を満たすこと）。

- どの `source_documents` のどの記載に由来するか（来歴、[ADR-0006](0006-pipeline-provenance.md)）
- どの中核パイプライン段階（[ADR-0011](0011-fixed-core-pipeline.md)）で誤りが生じたか（Layout Detector / Section Parser / Field Extractor / Normalizer / Validator のいずれか）
- 誤って抽出・正規化された値と、正しい値
- 誤りの分類（例: 未知の表記ゆれ、未知の様式、Knowledge Baseの欠落、Layoutの欠落、真の例外 等）— [ADR-0012](0012-error-handling-priority-order.md) の優先順位分類と対応させる
- この修正が、`knowledge/` または `layouts/` への反映（Knowledge Base追加、Layout追加）につながったかどうか、つながった場合はその参照

- Validatorが検証NGを検出した時点、および人手レビューで誤りが確定した時点の両方が、Learning Datasetへの入力になる。
- Learning Datasetは「過去に何を直したかの記録」であると同時に、「次に似た誤りが起きたときに、優先すべき対応（Knowledge Base追加かLayout追加か）を導出するための入力」として設計する。

## 検討した代替案

- **単純な修正ログ（誰が・いつ・何を・どう直したか、のみを記録するテーブル）**: 実装は容易だが、蓄積された修正情報がシステム改善に活用されず、同じ分類の誤りが何度も個別対応されるリスクが残る。監査要件は満たすが、10年運用における学習・改善の資産にならないため見送った。

## 結果（トレードオフ）

- Learning Datasetは、単純なログより設計・実装コストが高い（誤りの分類、Knowledge Base/Layoutへの反映有無の追跡等が必要）。
- 一方で、蓄積されたエントリを定期的に見直すことで、「どの分類の誤りが多いか」「Knowledge Baseが手薄な領域はどこか」を可視化でき、[ADR-0012](0012-error-handling-priority-order.md) の優先順位ルールを実効あるものにする。
- 保管場所は `knowledge/learning_dataset/`（実データは `learning_dataset` DBテーブル）とする（`knowledge/layout_notes/`(旧`known_issues/`) が「既知のPDFの癖」という定性的な知見であるのに対し、Learning Datasetは個々の誤り事例の構造化データという違いがある）。

## 関連ADR

- [ADR-0017](0017-learning-dataset-field-expansion.md): 本ADRの方針を、具体的な保持フィールド・ライフサイクルまで詳細化した決定（[`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md)）
