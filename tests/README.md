# tests/

## 責務

`src/` の実装を検証するテストスイート。設計フェーズの現時点ではテストコードは存在しない。

## 想定する構成

```
tests/
  unit/          # 個々の関数・クラス単位のテスト
  integration/   # 複数ステージを跨いだ結合テスト（例: extract→parse→normalize）
  golden/        # sample_pdfs/ と sample_outputs/ を用いたゴールデンファイルテスト（ADR-0007）
```

## 方針

- 新機能には対応するテストを追加する（`CONTRIBUTING.md` 参照）。
- パーサー・正規化ロジックの変更には、可能な限り `tests/golden` でのリグレッション確認を伴わせる。
- `sample_outputs/` を用いるゴールデンファイルテストは「正解データとの比較」であり、期待値の変更は無言で行わない（`CLAUDE.md` 参照）。
- テスト実行・カバレッジ設定は `pyproject.toml` の `[tool.pytest.ini_options]` / `[tool.coverage.run]` を参照。
