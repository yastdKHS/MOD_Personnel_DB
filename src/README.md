# src/

## 責務

本体実装（Pythonパッケージ）を置く場所。`src/` レイアウト（[ADR-0001](../docs/adr/0001-python-packaging.md)）を採用しており、パッケージ本体は `src/mod_personnel_db/` に配置する想定。

> 現時点では設計フェーズのため、実装コードは存在しない。以下は今後の実装の指針であり、確定した設計ではない。

## 想定するモジュール構成

`docs/architecture.md` の中核パイプライン（[ADR-0011](../docs/adr/0011-fixed-core-pipeline.md) で固定）に1対1で対応させる。中核パイプラインの6モジュールは、統合・分割・順序変更を行わない。

```
src/mod_personnel_db/
  fetch/              # 中核パイプラインの外側。PDF取得（取得元・取得日時・ハッシュの記録を含む）
  document_analyzer/  # 中核 1/6: PDFを解析可能な内部表現に変換する
  layout_detector/    # 中核 2/6: layouts/ を参照し、該当する様式（era_id）を判定する
  section_parser/     # 中核 3/6: レイアウト定義に従い対象セクションを切り出す
  field_extractor/    # 中核 4/6: レイアウト定義に従いフィールドを抽出する（正規化前）
  normalizer/         # 中核 5/6: knowledge/ の定義を用いた正規化・名寄せ
  validator/          # 中核 6/6: ドメイン制約に基づく検証。検証NGは knowledge/learning_dataset/ へ
  store/              # 中核パイプラインの外側。SQLiteへの永続化（ADR-0004）
  publish/            # 中核パイプラインの外側。公開用データのエクスポート
  cli/                # コマンドラインエントリポイント
```

## 設計原則

- 中核パイプライン（`document_analyzer/` 〜 `validator/`）の段階構成・順序を変更しない（[ADR-0011](../docs/adr/0011-fixed-core-pipeline.md)）。
- レイアウト依存の情報（PDFの座標・見出し文字列等）をハードコードしない。`layouts/` を参照する（[ADR-0003](../docs/adr/0003-layout-definition-strategy.md)）。
- ドメイン知識（階級名・組織名の表記ゆれ等）をハードコードしない。`knowledge/` を参照する（[ADR-0005](../docs/adr/0005-knowledge-base-normalization.md)）。
- 未知パターンへの対応は、Knowledge Base追加 > Layout追加 > 例外処理、の優先順位に従う。安易に `try/except` や正規表現の特殊対応を追加しない（[ADR-0012](../docs/adr/0012-error-handling-priority-order.md)）。
- 各段階の出力は、入力元への参照（来歴）を保持する（[ADR-0006](../docs/adr/0006-pipeline-provenance.md)）。検証NGはCorrection LogではなくLearning Datasetとして `knowledge/learning_dataset/` に記録する（[ADR-0013](../docs/adr/0013-learning-dataset-not-correction-log.md)）。
- 新規コードには型ヒントを付与し、`mypy --strict` を通す（[ADR-0002](../docs/adr/0002-lint-format-typecheck-tooling.md)）。
- 大きな関数を作らない（目安: 1関数30文・分岐8・循環的複雑度8・引数5以内）。`pyproject.toml` のlintルールで機械的に検出する（[ADR-0014](../docs/adr/0014-development-discipline.md)）。
- 1つのPRは1つの責務のみを変更する（[ADR-0014](../docs/adr/0014-development-discipline.md)）。

## scripts/ との違い

`src/` はテスト・型チェックの対象となる、安定したパブリックAPI・CLIを提供するパッケージ本体。定型化されていない一回限りの処理・運用作業は `scripts/` に置く（`scripts/README.md` 参照）。
