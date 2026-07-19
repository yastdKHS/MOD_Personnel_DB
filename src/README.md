# src/

## 責務

本体実装（Pythonパッケージ）を置く場所。`src/` レイアウト（[ADR-0001](../docs/adr/0001-python-packaging.md)）を採用しており、パッケージ本体は `src/mod_personnel_db/` に配置する。

> Phase2 Task1（Repository Skeleton）・Task2（Domain Model Implementation）・Task3（Pipeline Skeleton Implementation）・Task4（Document Analyzer Implementation）より実装着手。`utils/`, `models/`（[`docs/api/models.md`](../docs/api/models.md)の13モデル全種。`Document`はVersion 2.0（[ADR-0032](../docs/adr/0032-redefine-document-analyzer-responsibility.md)）、Version 1は`DocumentV1`/`PageV1`として引き続き提供）, `repositories/`（Protocol）, `repositories/sqlite/`（SQLite実装、7種）, `pipeline/`（Pipeline Framework骨格）, `document/`（Document Analyzer本実装。DocumentAnalyzer/DocumentAnalyzerError、PDF解析ライブラリは`pypdf`（[ADR-0034](../docs/adr/0034-pypdf-for-document-analyzer.md)）。中核パイプライン段階2以降＝`layout/`〜`validators/`は未実装のまま）が実装済み。`config/`、`layout/`〜`validators/`（中核パイプライン段階2〜6）, `learning/`, `features/`, `review/`（Domain Service）, `export/`, `ftp/`, `fetch/`, `services/`, `cli/` は未実装。

## 想定するパッケージ構成

詳細なパッケージ構成（各パッケージの目的・責務・依存先・依存禁止）は [`docs/api/package-design.md`](../docs/api/package-design.md) を正とする。本セクションは概要のみを示す。

```
src/mod_personnel_db/
  config/       utils/       models/               # 基盤
  repositories/ (+ sqlite/)                          # 永続化（SQLite非依存、docs/api/repositories.md）
  document/     layout/      sections/               # 中核パイプライン 1〜3/6
  extractors/   normalizers/ validators/             # 中核パイプライン 4〜6/6
  knowledge/    learning/    features/                # 横断サービス
  review/       export/      ftp/    fetch/           # 中核パイプライン外側
  pipeline/     services/    cli/                     # オーケストレーション
```

中核パイプライン6段階（`document/` 〜 `validators/`）は、統合・分割・順序変更を行わない（[ADR-0011](../docs/adr/0011-fixed-core-pipeline.md)）。各段階は`run()`のみを公開する（[`docs/api/pipeline.md`](../docs/api/pipeline.md)）。パッケージ間の依存関係の許可/禁止ルールは [`docs/api/dependency-rule.md`](../docs/api/dependency-rule.md)、公開APIの型シグネチャは [`docs/api/interfaces.md`](../docs/api/interfaces.md)、8段階の分離保証（例: 「Field ExtractorはDBを知らない」）は [`docs/architecture/architecture-contract.md`](../docs/architecture/architecture-contract.md) を参照。

## 設計原則

- 中核パイプライン（`document/` 〜 `validators/`）の段階構成・順序を変更しない（[ADR-0011](../docs/adr/0011-fixed-core-pipeline.md)）。各段階は`repositories/`にすら依存しない純粋な変換として実装する（[`docs/architecture/architecture-contract.md`](../docs/architecture/architecture-contract.md)）。
- レイアウト依存の情報（PDFの座標・見出し文字列等）をハードコードしない。`layouts/` を参照する（[ADR-0003](../docs/adr/0003-layout-definition-strategy.md)）。
- ドメイン知識（階級名・組織名の表記ゆれ等）をハードコードしない。`knowledge/` を参照する（[ADR-0005](../docs/adr/0005-knowledge-base-normalization.md)）。
- 未知パターンへの対応は、Knowledge Base追加 > Layout追加 > 例外処理、の優先順位に従う。安易に `try/except` や正規表現の特殊対応を追加しない（[ADR-0012](../docs/adr/0012-error-handling-priority-order.md)）。
- 各段階の出力は、入力元への参照（来歴）を保持する（[ADR-0006](../docs/adr/0006-pipeline-provenance.md)）。検証NGはCorrection LogではなくLearning Datasetとして `knowledge/learning_dataset/` に記録する（[ADR-0013](../docs/adr/0013-learning-dataset-not-correction-log.md)）。
- 新規コードには型ヒントを付与し、`mypy --strict` を通す（[ADR-0002](../docs/adr/0002-lint-format-typecheck-tooling.md)）。
- 大きな関数を作らない（目安: 1関数30文・分岐8・循環的複雑度8・引数5以内）。`pyproject.toml` のlintルールで機械的に検出する（[ADR-0014](../docs/adr/0014-development-discipline.md)）。
- 1つのPRは1つの責務のみを変更する（[ADR-0014](../docs/adr/0014-development-discipline.md)）。

## scripts/ との違い

`src/` はテスト・型チェックの対象となる、安定したパブリックAPI・CLIを提供するパッケージ本体。定型化されていない一回限りの処理・運用作業は `scripts/` に置く（`scripts/README.md` 参照）。
