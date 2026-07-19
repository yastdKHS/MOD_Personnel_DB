# tests/

## 責務

`src/` の実装を検証するテストスイート。Phase2 Task1（Repository Skeleton）より`tests/unit/`にテストコードが存在する。テスト種別ごとの方針は[`docs/testing/test-policy.md`](../docs/testing/test-policy.md)を正とする。

## 構成

```
tests/
  unit/
    models/         # ドメインモデルのValidation Rule検証
    repositories/    # Repository Protocol実装（SQLite）の検証
    pipeline/         # Pipeline Framework骨格（Stub Stageのみ）の検証
    document/         # Document Analyzer本実装の検証（合成PDFフィクスチャ、実在PDFは使用しない）
    layout/            # Layout Detector本実装の検証（合成PDF・YAMLフィクスチャ、実在PDFは使用しない）
  integration/       # 複数ステージを跨いだ結合テスト（未整備）
  golden/             # sample_pdfs/ と sample_outputs/ を用いたゴールデンファイルテスト（ADR-0007、未整備）
```

## 方針

- 新機能には対応するテストを追加する（`CONTRIBUTING.md` 参照）。
- パーサー・正規化ロジックの変更には、可能な限り `tests/golden` でのリグレッション確認を伴わせる。
- `sample_outputs/` を用いるゴールデンファイルテストは「正解データとの比較」であり、期待値の変更は無言で行わない（`CLAUDE.md` 参照）。
- テスト実行・カバレッジ設定は `pyproject.toml` の `[tool.pytest.ini_options]` / `[tool.coverage.run]` を参照。
