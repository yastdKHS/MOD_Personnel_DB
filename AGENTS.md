# AGENTS.md — AIコーディングエージェント共通運用規約

本ファイルは、Claude Code に限らず、本リポジトリ上で動作する**あらゆるAIコーディングエージェント**（コード生成・自動修正・自動レビュー等を行うツール全般）が従うべき最小限の規約を定義します。特定ツール向けの詳細指示は、そのツール専用のファイル（例: `CLAUDE.md`）を参照してください。

## このリポジトリの性質

- 10年以上の運用を前提とした、公的機関が公表する人事情報を扱うデータ基盤である。
- 「動くコード」より「後から検証・修正・引き継ぎができること」を優先する。実装速度より設計品質を優先する（[ADR-0014](docs/adr/0014-development-discipline.md)）。
- 変更の影響範囲が大きい領域（データモデル・レイアウト定義・ドメイン知識・公開データの範囲）は、通常のコードより慎重に扱う。
- 中核処理パイプライン（Document Analyzer → Layout Detector → Section Parser → Field Extractor → Normalizer → Validator）は[固定](docs/adr/0011-fixed-core-pipeline.md)されている。この構成を変更するコードは、既存設計を破壊するものとして扱い、生成・提案しない。

## データ取り扱いの原則

1. 取り扱ってよいのは、防衛省が**公務として一般公表した**人事発令情報に限る。非公開情報・推測による個人情報の付加・公表範囲を超えるデータの収集は行わない。
2. 個人の識別性を高める追加処理（他データベースとの突合による個人特定の強化等）を、指示なく実装しない。
3. 詳細な方針は [`docs/adr/0008-data-ethics-policy.md`](docs/adr/0008-data-ethics-policy.md) を正とする。

## 変更のガードレール

以下に該当する変更は、**着手前に既存ADRの確認、または新規ADRの提案**を行うこと。無断で仕様を変えない。

- データベーススキーマ / データモデルの変更
- `layouts/` のレイアウト定義フォーマット自体の変更（個別レイアウトの追加は通常のPR運用でよい）
- `knowledge/` のデータ構造（スキーマ）の変更
- 依存ライブラリ・ビルドツール・CI構成の変更
- 中核パイプラインの段階構成（Document Analyzer / Layout Detector / Section Parser / Field Extractor / Normalizer / Validator）の変更。これは通常のADR提案では足りず、必ずユーザーの明示的な承認を要する（[ADR-0011](docs/adr/0011-fixed-core-pipeline.md)）

## 未知パターンへの対応順位

新しい表記ゆれ・組織名・様式・PDFの例外に遭遇した場合、次の優先順位で対応する（[ADR-0012](docs/adr/0012-error-handling-priority-order.md)）。正規表現や `try/except` によるコード側の特殊対応を安易に追加しない。

1. `knowledge/` へのデータ追加
2. `layouts/` へのレイアウト定義追加
3. `src/` 内の例外処理（最後の手段。理由の明記が必須）

検証NGや修正情報は、修正ログではなく `knowledge/learning_dataset/` にLearning Datasetとして記録する（[ADR-0013](docs/adr/0013-learning-dataset-not-correction-log.md)）。

## コードの粒度に関するガードレール

- 大きな関数を作らない（目安: 30文・分岐8・複雑度8・引数5以内、[ADR-0014](docs/adr/0014-development-discipline.md)）。
- 1つのPull Requestは1つの責務のみを変更する。無関係な変更を混ぜない。

## 禁止される操作

- リモートへの `force push`、履歴の書き換え、ブランチ・タグの削除
- pre-commit / CI チェックのバイパス（`--no-verify` 等）
- 実PDF・実データ（サンプル基準を満たさないもの）のコミット
- `knowledge/` の一括自動書き換え（人手レビュー前提のデータのため）
- 明示的な指示のないままの依存関係の追加・アップグレード

## 不明点がある場合

設計判断が曖昧なまま実装を進めない。特に以下は必ず人間に確認する。

- 新しい外部依存を追加してよいか
- 個人情報の取り扱い範囲を広げる変更
- 既存ADRと矛盾する実装方針

## 関連ドキュメント

- [`CLAUDE.md`](CLAUDE.md) — Claude Code固有の追加規約
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 人間の開発者向けガイド
- [`docs/adr/`](docs/adr/) — 設計判断の記録（本ファイルの運用ルールの根拠は [ADR-0009](docs/adr/0009-ai-agent-operating-policy.md)）
