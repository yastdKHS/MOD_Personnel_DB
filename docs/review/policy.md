# Review Policy

> Human Reviewが「誰が・何を・どんな条件で」行ってよいかを定める運用ポリシー。[`domain.md`](domain.md)のドメインモデル（`ReviewSession`, `ReviewAssignment`, `ReviewDecision`等）が満たすべき制約として実装時に強制される想定。本ドキュメントに実装はない。

## 目次

1. [誰が承認できるか](#誰が承認できるか)
2. [差戻し](#差戻し)
3. [再レビュー](#再レビュー)
4. [Confidence Override](#confidence-override)
5. [Knowledge追加条件](#knowledge追加条件)
6. [Learning Dataset登録条件](#learning-dataset登録条件)
7. [Gold更新条件](#gold更新条件)

---

## 誰が承認できるか

- **基本原則**: 登録済みのレビュアー（`ReviewAssignment.assigned_to`に指定された担当者）が、自身に割り当てられた候補に対してのみ`ReviewDecision`を発行できる。他者に割り当てられた候補を承認することはできない（[`domain.md`](domain.md#reviewassignment)の一意割当制約）。
- **自己割当の制限**: `knowledge/` / `layouts/`（データ）への変更を自らのPRで行った担当者は、そのデータ変更が直接影響する候補の承認において、単独承認を避けることが望ましい（利益相反の回避）。強制はしないが、[`ReviewComment`](domain.md#reviewcomment)にその旨を記録することを推奨する。
- **Confidence Overrideを伴う承認**（[後述](#confidence-override)）は、通常の承認より慎重な判断を要するため、`reason`の記載を必須とする（[`domain.md`](domain.md#reviewdecision)の`ReviewDecision.reason`）。
- **将来の拡張**: レビュアーの権限段階（例: シニアレビュアーのみがConfidence Overrideを行える）は、本ポリシーの初版では導入しない（レビュアーが少人数である初期運用を想定、[ADR-0021](../adr/0021-review-ui-strategy.md)と同じ判断基準）。レビュアー数が増え、権限分離の必要性が明らかになった時点で改訂する。

## 差戻し

`ReviewDecision.decision == "return"`とする条件。

| 差戻し理由 | 遷移先（[`domain.md`](domain.md#review-lifecycle状態遷移図)） | 説明 |
|---|---|---|
| 元データの読み取り不能・破損 | `Returned` → 人手による原本PDF再確認 | Document Analyzer段階からのやり直しが必要 |
| 未知の様式・レイアウト誤判定 | `Returned` → `layouts/`への追加を経て`Candidate`へ再投入 | [ADR-0012](../adr/0012-error-handling-priority-order.md)の優先順位に従い、まず`layouts/`の追加を検討 |
| Knowledge Base不足で正規化不能 | `Returned` → [Knowledge追加条件](#knowledge追加条件)を満たした上で`Candidate`へ再投入 | |
| レビュアーの判断だけでは確定できない（要追加確認） | `Returned`（保留）、`ReviewComment`に確認事項を記録 | 一定期間後に再度キューへ（[`queue.md`](queue.md)の`reviewer_request`優先度で再登場） |

- **差戻しは`Candidate`状態への回帰であり、`gold_records`には一切影響しない**（[`domain.md`](domain.md#review-lifecycle状態遷移図)の状態遷移図のとおり、`Returned`から`GoldDatabase`への直接遷移は存在しない）。
- 差戻しのたびに、原因分類（[ADR-0012](../adr/0012-error-handling-priority-order.md)の`error_category`）に基づき[Learning Dataset登録条件](#learning-dataset登録条件)を満たすかを確認する。

## 再レビュー

一度`GoldDatabase`に到達した後、事後的に誤りが判明した場合の対応。

- **トリガー条件**: (1) `learning_dataset`（[ADR-0017](../adr/0017-learning-dataset-field-expansion.md)）に、当該`gold_record`の由来となった`candidate_id`を`source_candidate_record_id`とするエントリが新規登録された場合。(2) 同一`person_key`について、後続の発令PDFとの整合性チェック（Validatorの`cross_field_constraint`、[`docs/knowledge/schema.md`](../knowledge/schema.md#validation)）で矛盾が検出された場合。
- **再レビューは新しい`ReviewAssignment`として扱う**（[`domain.md`](domain.md#review-lifecycle状態遷移図)の`ReReview → Assigned`）。元の`ReviewDecision`は不変のまま保持し（[ADR-0006](../adr/0006-pipeline-provenance.md)の来歴管理、削除せず追記する原則）、新しい`ReviewDecision`が追加される。
- 再レビューの結果、`gold_records`の訂正が必要と判断された場合は、[Gold更新条件](#gold更新条件)に従い新バージョンとして追加する（既存バージョンの上書きはしない、[`docs/database/schema.md`](../database/schema.md#5-gold_records)のSCD Type 2設計）。
- 再レビューの優先度は、[`queue.md`](queue.md)における通常の新規候補と同列に扱う（公開済みデータの訂正が後回しにされないよう、`layout_unknown`・`parser_error`に次ぐ優先度を基本とする。具体的な重み付けは[`queue.md`](queue.md#優先度スコアの算出)を参照）。

## Confidence Override

Validator/FeatureStoreが算出した`Confidence`（[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)）を、レビュアーが人手で上書きする機能。

- **上書きが許される場合**: (1) システムが`low`/`medium`と判定したが、レビュアーが原本PDFとの照合により正しいと確認できた場合（`band`を`verified`へ引き上げる）。(2) システムが`high`と判定したが、レビュアーが誤りを発見した場合（`band`を`low`へ引き下げ、修正の上で承認するか、差戻しとする）。
- **上書きの記録**: `ReviewDecision.confidence_override`に新しい`Confidence`値を、`reason`にその根拠を必須で記録する（[`domain.md`](domain.md#reviewdecision)）。上書き後の値が公開JSON（[ADR-0016](../adr/0016-public-json-format.md)）の`confidence`として採用される。
- **上書きしない場合との違い**: `confidence_override`が`None`の`ReviewDecision`は、システム算出値をそのまま採用したことを意味する（レビュアーが確認し、変更の必要を認めなかった）。
- **算出ロジック自体の変更ではない**: Confidence Overrideは個々の候補に対する例外的な補正であり、[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)のバンド判定ルール自体を変更するものではない。Overrideが特定のパターンで頻発する場合、それは算出ルール自体の見直しシグナルとして[`metrics.md`](metrics.md)の観測対象に含める。

## Knowledge追加条件

レビュー中に「この表記ゆれ・組織名は`knowledge/`に追加すべきだ」と判断した場合の条件。[ADR-0012](../adr/0012-error-handling-priority-order.md)の優先順位（Knowledge Base追加を正規表現より優先）をレビュープロセスに落とし込む。

1. **根拠の明示**: 追加する`KnowledgeItem`（[`docs/knowledge/schema.md`](../knowledge/schema.md)）の`provenance.source`に、根拠となる資料（発令PDF自体、制度文書等）を明記できること。レビュアーの推測のみによる追加は行わない。
2. **同一パターンの再現性**: 単発の誤記・OCRエラーは`knowledge/typography/`や`alias`の対象外とし、[Learning Dataset登録条件](#learning-dataset登録条件)のみで扱う。**2件以上の独立した発令PDFで同一パターンが確認された場合**に、`knowledge/`への追加を検討する（一過性のノイズと恒常的な表記ゆれを区別する閾値）。
3. **レビュアーは`knowledge/`ファイルを直接変更しない**: レビュー画面（当面CLI、[ADR-0021](../adr/0021-review-ui-strategy.md)）上での操作は、あくまで`knowledge/`追加の**提案**（`ReviewDecision`または`ReviewComment`への記録、および対応する`LearningRecord.improvement_candidate`への記載）に留める。実際のファイル変更は、通常のPRレビュープロセス（[CONTRIBUTING.md](../../CONTRIBUTING.md)）を経て行う（[`docs/api/package-design.md`](../api/package-design.md)の`review/`パッケージが`knowledge/`パッケージに依存しないという設計、[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)と整合）。

## Learning Dataset登録条件

`review/`が`LearningRepository`へ書き込む（[`docs/api/repositories.md`](../api/repositories.md#learningrepository)）条件。[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md)・[ADR-0017](../adr/0017-learning-dataset-field-expansion.md)の設計を前提とする。

- **必須で登録する場合**: `ReviewItem`（フィールド修正）が1件でも発生した場合、対応する`LearningRecord`を必ず作成する（`wrong_value` / `correct_value` / `field_name`を`ReviewItem`から転記、[`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md#保持するフィールド)）。
- **`reviewer_comment` / `improvement_candidate`の記載**: [Knowledge追加条件](#knowledge追加条件)・[後述のGold更新条件](#gold更新条件)の判断に至った理由は、`LearningRecord.reviewer_comment`と`improvement_candidate`に記録する（`ReviewComment`の内容をここに集約してもよい）。
- **登録しない場合**: レビュアーが確認のみを行い、修正が一切発生しなかった場合（`ReviewDecision.decision == "approve"`かつ`ReviewItem`が0件）は、`LearningRecord`を新規作成しない（Validatorが既に検証NGとして記録済みの場合を除く。二重登録を避ける）。

## Gold更新条件

`ReviewService.promote_to_gold()`（[`docs/api/review.md`](../api/review.md)）が`GoldRepository`へ書き込む条件。**Reviewだけがgold_recordsを更新できる**という設計（[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)の保証、[Task 7](../architecture/architecture-contract.md)参照）の実質的な運用ルールである。

| # | 条件 |
|---|---|
| 1 | 対象候補について`ReviewDecision.decision == "approve"`が存在すること（`Returned`のまま昇格することはない） |
| 2 | `confidence_override`がない場合、システム算出の`Confidence.band`が`"low"`でないこと。`"low"`のまま承認する場合は`confidence_override`による明示的な引き上げと`reason`の記載を必須とする（[Confidence Override](#confidence-override)） |
| 3 | 新規発令（`person_key`+`effective_date`の初出）の場合、`version=1`として`add_version`を呼ぶ。既存`gold_record`の訂正の場合、`supersede`により旧バージョンを無効化した上で新バージョンを追加する（[`docs/api/repositories.md`](../api/repositories.md#goldrepository)のSCD Type 2操作） |
| 4 | 昇格操作自体を`ReviewHistory`（[`domain.md`](domain.md#reviewhistory)）に記録し、いつ・誰の`ReviewDecision`に基づき昇格したかを追跡可能にする |

これらの条件を満たさない昇格リクエストは、`ReviewService`が拒否する（[`docs/api/review.md`](../api/review.md)の例外設計）。
