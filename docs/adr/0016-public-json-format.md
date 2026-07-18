# 0016. 公開JSON形式（JSON Schema Draft 2020-12）の確定

## ステータス
Accepted

## コンテキスト

[ADR-0010](0010-ci-cd-and-publish-strategy.md) で公開（Publish）フローの方針を、[ADR-0015](0015-sqlite-schema-finalization.md) で `exports` テーブルを含む物理スキーマを定めたが、`exports`（`format='json'`）が実際に生成する**外部公開用JSONの中身の契約**は未確定だった。契約が曖昧なままでは、外部の利用者（研究者・報道機関等）がフィールドの意味・安定性を判断できず、また将来の変更が互換性を壊しているかどうかを機械的に検証できない。`docs/adr/README.md` の「いつADRを書くか」に定める「データモデルの決定・変更」「運用・公開ポリシー」に該当するため、本ADRを起票する。

## 決定

- 公開JSONの詳細仕様を [`docs/database/json_schema.md`](../database/json_schema.md) として、JSON Schema Draft 2020-12準拠で策定する。本ADRはその内容を正式決定として承認するものであり、個々のフィールド定義・算出ルールの詳細は同ドキュメントを正とする。
- 公開JSON形式のバージョンは、DBスキーマバージョン（`schema_migrations`）・データ生成バージョン（`parser_versions`）とは独立した第3の軸として、SemVer + `$id` のURIバージョニングで管理する。
- `generated_at`（エクスポート生成日時）、`parser_version` / `source_pdf`（レコードごとの来歴）、`confidence`（レコードごとの信頼度）を必須項目として含める。`confidence` は `gold_records` に専用列を持たず、既存テーブル（`candidate_records.validation_status` / `review_changes` / `learning_dataset`）からPublish段階で導出する計算値とする。
- 公開JSON形式の破壊的変更（フィールド削除・型変更・`required`化等）は、`docs/adr/README.md` の基準に従い新規ADRを要する変更管理の対象とする。後方互換な追加はPRレビューで足りる。

## 検討した代替案

- **`confidence` を `gold_records` の永続列として持つ**: 算出コストの観点では有利だが、現時点でその必要性を裏付ける実運用データがなく、[ADR-0014](0014-development-discipline.md)（過剰設計をしない）の方針に従い、まずは計算値として設計し、必要性が判明した時点で非破壊的な列追加として `docs/database/schema.md` を更新する方針とした。
- **公開JSON形式のバージョンをDBスキーマバージョンと連動させる**: 実装は単純化するが、DBの内部構造変更のたびに外部契約のバージョンが（内容が変わらなくても）上がってしまい、外部利用者に無用な混乱を与える。独立した軸として管理する方針とした。

## 結果（トレードオフ）

- `confidence` を計算値とすることで、算出ロジックの変更が容易になる一方、算出ルール自体の変更（バンドの閾値変更等）がレコードの見え方に影響するため、算出ルールの変更も相応の説明責任を伴う（`docs/database/json_schema.md` の更新、影響が大きい場合はADR）。
- Draft 2020-12を採用することで、`$defs` / `deprecated` 等の現行仕様を活用できる一方、`format` キーワードがデフォルトでは注釈にとどまる点（Format Assertion Vocabularyの明示的な有効化が必要）を実装者が見落とすリスクがあり、`docs/database/json_schema.md` に明記して注意喚起している。
