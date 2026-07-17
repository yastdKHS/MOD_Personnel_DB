# src/

## 責務

本体実装（Pythonパッケージ）を置く場所。`src/` レイアウト（[ADR-0001](../docs/adr/0001-python-packaging.md)）を採用しており、パッケージ本体は `src/mod_personnel_db/` に配置する想定。

> 現時点では設計フェーズのため、実装コードは存在しない。以下は今後の実装の指針であり、確定した設計ではない。

## 想定するモジュール構成

`docs/architecture.md` のパイプラインステージに対応させる想定。

```
src/mod_personnel_db/
  fetch/       # PDF取得（取得元・取得日時・ハッシュの記録を含む）
  extract/     # PDFからの生データ抽出
  parse/       # layouts/ の定義を解釈し、フィールドへ分解する汎用エンジン
  normalize/   # knowledge/ の定義を用いた正規化・名寄せ
  validate/    # ドメイン制約に基づく検証
  store/       # SQLiteへの永続化（ADR-0004）
  publish/     # 公開用データのエクスポート
  cli/         # コマンドラインエントリポイント
```

## 設計原則

- レイアウト依存の情報（PDFの座標・見出し文字列等）をハードコードしない。`layouts/` を参照する（[ADR-0003](../docs/adr/0003-layout-definition-strategy.md)）。
- ドメイン知識（階級名・組織名の表記ゆれ等）をハードコードしない。`knowledge/` を参照する（[ADR-0005](../docs/adr/0005-knowledge-base-normalization.md)）。
- 各ステージの出力は、入力元への参照（来歴）を保持する（[ADR-0006](../docs/adr/0006-pipeline-provenance.md)）。
- 新規コードには型ヒントを付与し、`mypy --strict` を通す（[ADR-0002](../docs/adr/0002-lint-format-typecheck-tooling.md)）。

## scripts/ との違い

`src/` はテスト・型チェックの対象となる、安定したパブリックAPI・CLIを提供するパッケージ本体。定型化されていない一回限りの処理・運用作業は `scripts/` に置く（`scripts/README.md` 参照）。
