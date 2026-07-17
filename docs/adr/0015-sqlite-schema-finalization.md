# 0015. SQLiteスキーマの確定

## ステータス
Accepted

## コンテキスト

[ADR-0004](0004-sqlite-as-datastore.md) でSQLiteの採用を決定したが、具体的なテーブル構成・主キー・外部キー・インデックスは未確定だった。中核パイプライン（[ADR-0011](0011-fixed-core-pipeline.md)）、来歴管理（[ADR-0006](0006-pipeline-provenance.md)）、未知パターンへの対応優先順位（[ADR-0012](0012-error-handling-priority-order.md)）、Learning Dataset方針（[ADR-0013](0013-learning-dataset-not-correction-log.md)）を、実装可能な物理データモデルへ落とし込む必要があった。`docs/adr/README.md` の「いつADRを書くか」に定める「データモデルの決定・変更」に該当するため、本ADRを起票する。

## 決定

- 詳細なテーブル定義・ER図・主キー/外部キー/インデックス・バージョン管理・マイグレーション方針を [`docs/database/schema.md`](../database/schema.md) として策定する。本ADRはその内容を正式決定として承認するものであり、個々の設計判断の詳細は同ドキュメントを正とする。
- 最小構成として、以下12の業務テーブルを定める: `pdfs`, `layouts`, `personnel_sections`, `candidate_records`, `gold_records`, `review_sessions`, `review_changes`, `knowledge_items`, `learning_dataset`, `parser_versions`, `exports`, `jobs`。加えて、マイグレーション基盤専用の管理用テーブル `schema_migrations` を設ける。
- スキーマの破壊的変更（テーブルの追加・削除、主キー/外部キーの変更等）は、`docs/adr/README.md` の基準に従い新規ADRを要する変更管理の対象とする。非破壊的変更（列追加、インデックス追加等）は通常のPRレビューで足り、`docs/database/schema.md` の該当箇所の更新のみでよい。
- `docs/data_model.md` は概念設計として維持し、`docs/database/schema.md` を物理設計として位置づける（概念設計と物理設計の分離）。

## 検討した代替案

- **`docs/data_model.md` の概念モデルのみで実装を進める**: PK/FK/Indexの具体的な定義がないままでは、実装者・AIエージェントのセッションごとに解釈がぶれ、[ADR-0011](0011-fixed-core-pipeline.md) が目指す一貫性を損なう。物理設計を別途正式なドキュメントとして確定する方針とした。
- **ORMのマイグレーション機構（Alembic等）に依存したスキーマ管理**: 「枯れた技術を選ぶ」方針（[ADR-0001](0001-python-packaging.md)）と、SQLiteを直接運用するシンプルさ（[ADR-0004](0004-sqlite-as-datastore.md)）を優先し、手書きSQLマイグレーションによる管理を選択した（詳細は [`docs/database/schema.md`](../database/schema.md) の「Migration方針」）。

## 結果（トレードオフ）

- 詳細なスキーマを先に固定することで、実装時の設計判断の揺れを防ぎ、レビューの基準を明確にする。
- 一方で、実装を進める中でスキーマの不備・不足（例: 名寄せ精度不足によるpeopleマスタの必要性）が発覚する可能性があり、その場合は `docs/database/schema.md` の更新と、内容によっては本ADRのSupersedeを行う。
