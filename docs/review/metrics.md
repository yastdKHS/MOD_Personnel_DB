# Review Metrics

> Review Domainの健全性・システム全体の学習効果を継続的に観測するための指標。[`domain.md`](domain.md)の`ReviewStatistics`が保持する値の定義。本ドキュメントに実装はない。

## 指標一覧

| 指標 | 目的 |
|---|---|
| [Review Time](#review-time) | レビュー1件あたりの所要時間（作業負荷・SLAの把握） |
| [Correction Rate](#correction-rate) | パイプライン出力がそのまま承認される割合（自動処理の精度） |
| [Approval Rate](#approval-rate) | 差戻しに対する承認の割合（レビューの通過率） |
| [Knowledge Update Rate](#knowledge-update-rate) | 誤りがKnowledge Baseの改善に繋がっている割合（学習効果） |
| [Layout Update Rate](#layout-update-rate) | 誤りがLayout定義の改善に繋がっている割合（学習効果） |
| [Learning Growth](#learning-growth) | Learning Datasetの新規発生トレンド（システムの成熟度） |

---

## Review Time

**定義**: 候補が`Assigned`になってから、`Approved`または`Returned`の`ReviewDecision`が確定するまでの所要時間。

**算出式**:

```
review_time = ReviewDecision.decided_at - ReviewAssignment.assigned_at
```

**データ源**: `ReviewAssignment.assigned_at`、`ReviewDecision.decided_at`（[`domain.md`](domain.md)）。

**集計**: レビュアー別・優先度要因別（[`queue.md`](queue.md)の`priority_reason`）の平均・中央値・分布（P50/P90）を`ReviewStatistics.review_time_avg_minutes`として保持する。

**用途**: レビュアーの作業負荷の把握、[`queue.md`](queue.md)のAging補正パラメータ（`AGING_BOOST_PER_DAY`）の妥当性検証。P90が極端に長い場合、キューの割当ロジックまたはレビュアーの人員配置を見直すシグナルとする。

## Correction Rate

**定義**: レビュー対象になった候補のうち、1件以上の`ReviewItem`（フィールド修正）が発生した割合。パイプライン（Field Extractor〜Validator）の出力がそのまま承認される精度の裏返しの指標。

**算出式**:

```
correction_rate = (Modified状態を経由した候補数) / (レビュー対象となった候補の総数)
```

**データ源**: `review_changes`（`docs/database/schema.md`）の存在有無を候補ごとに集計。

**用途**: `correction_rate`が高い（多くの候補が修正を要する）場合、[Knowledge Update Rate](#knowledge-update-rate)・[Layout Update Rate](#layout-update-rate)と合わせて、どの段階（Normalizer由来かLayout由来か）の改善が必要かを判断する材料にする。`parser_version`ごとに算出し、新バージョンで`correction_rate`が悪化していないかを[ADR-0023](../adr/0023-parser-versioning-policy.md)のリリース判断に活用する。

## Approval Rate

**定義**: 発行された`ReviewDecision`のうち、`approve`の割合（`return`との対比）。

**算出式**:

```
approval_rate = count(ReviewDecision.decision == "approve") / count(ReviewDecision)
```

**データ源**: `ReviewDecision`（[`domain.md`](domain.md)）。

**用途**: `approval_rate`が低い場合、[`queue.md`](queue.md)の割当ロジックが本来レビュー不要な候補まで多く拾っている（優先度閾値の見直し）、またはパイプライン自体の品質が低下している、のいずれかを示唆する。[Correction Rate](#correction-rate)と併読することで切り分ける（`correction_rate`は高いが`approval_rate`も高い＝修正すれば通る候補が多い、`approval_rate`が低い＝差戻し＝根本的な問題が多い）。

## Knowledge Update Rate

**定義**: 発生した`LearningRecord`（[ADR-0017](../adr/0017-learning-dataset-field-expansion.md)）のうち、`knowledge/`への反映（`reflected_in_knowledge_item_id`が設定される）に至った割合。

**算出式**:

```
knowledge_update_rate = count(LearningRecord.reflected_in_knowledge_item_id IS NOT NULL)
                         / count(LearningRecord WHERE error_category IN ("unknown_alias", "knowledge_gap"))
```

**データ源**: `LearningRepository.list_by_error_category()`（[`docs/api/repositories.md`](../api/repositories.md#learningrepository)）。

**用途**: [ADR-0012](../adr/0012-error-handling-priority-order.md)が定める「Knowledge Base追加を最優先する」方針が、実際に運用として機能しているかを検証する指標。値が低い場合、[`policy.md`](policy.md#knowledge追加条件)の閾値（2件以上の再現）が厳しすぎる、またはレビュアーが`improvement_candidate`を記録する習慣が根付いていない、等の運用課題を示す。

## Layout Update Rate

**定義**: 発生した`LearningRecord`のうち、`layouts/`への反映（`reflected_in_layout_id`が設定される）に至った割合。

**算出式**:

```
layout_update_rate = count(LearningRecord.reflected_in_layout_id IS NOT NULL)
                      / count(LearningRecord WHERE error_category IN ("unknown_layout", "layout_gap"))
```

**データ源**: 同上。

**用途**: [Knowledge Update Rate](#knowledge-update-rate)と対をなす指標。新様式・レイアウトの取りこぼしが、実際に`layouts/`への新規追加として解消されているかを追跡する。[`queue.md`](queue.md)の`layout_unknown`が最優先である設計が、実際に迅速な`layouts/`更新に繋がっているかの検証にも使う。

## Learning Growth

**定義**: 単位期間あたりに新規発生する`LearningRecord`の件数の推移（トレンド）。個々の割合ではなく、**時系列の傾き**を見る指標。

**算出式**:

```
learning_growth(period) = count(LearningRecord WHERE created_at IN period)
```

を月次・週次等の単位期間で算出し、直近N期間の傾き（線形回帰の係数、または単純な前期間比）を「成長率」として扱う。

**データ源**: `LearningRepository`（期間を指定した件数取得）。

**用途・解釈の注意**: 直感に反して、**この指標は「増加が悪化、減少が改善」を必ずしも意味しない**。

- システム運用の初期は、新様式・未知の表記ゆれの発見が続くため`learning_growth`は高い水準で推移するのが自然（Knowledge Base・Layoutが未成熟なため）。
- Knowledge Base・Layoutが成熟するにつれ`learning_growth`は逓減し、ゼロに近づくことが期待される（[Knowledge Update Rate](#knowledge-update-rate) / [Layout Update Rate](#layout-update-rate)が高水準を維持している前提で）。
- **`learning_growth`が高いまま高止まりし、かつ[Knowledge Update Rate](#knowledge-update-rate)が低い場合**は、誤りが発見されても改善に繋がっていないという警告シグナルであり、[`policy.md`](policy.md#knowledge追加条件)の運用の見直しを要する。

`ReviewStatistics.learning_growth`には、直近期間の件数と前期間比の変化率（%）の両方を保持することを想定する。

## スナップショットの運用

`ReviewStatistics`は[`domain.md`](domain.md#reviewstatistics)のとおり既定では都度計算（永続化しない）だが、上記6指標の**長期トレンド**（特に[Learning Growth](#learning-growth)）を追跡するには、定期的なスナップショットが有用である。実装時、`services/`（[`docs/api/package-design.md`](../api/package-design.md)）に、[ADR-0019](../adr/0019-workflow-orchestration.md)のスケジュール実行と同じ仕組みで月次スナップショットを記録するジョブの追加を検討する（本ドキュメントでは方針のみ示し、テーブル設計は行わない）。
