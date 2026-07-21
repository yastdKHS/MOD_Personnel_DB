# knowledge/typography/

> `category: typography`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#typography)）に対応するディレクトリ。

## 責務

全角/半角、旧字体/新字体、空白・記号の統一等、**値に依存しない機械的な文字レベルの正規化ルール**を保持する。特定の個人・組織に紐づく表記対応（`alias` / `organization` 等）とは異なり、あらゆる文字列に共通して適用される規則を扱う。

## スキーマ

エントリの目標形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#typography) の `TypographyEntry` 定義（JSON Schema Draft 2020-12）である。ファイル名は `<id>.yaml`（例: `typo-fullwidth-digit.yaml`）とする。

**現在の実データ形式**: 実装済みの読み込みコード（`src/mod_personnel_db/knowledge/loader.py`）は上記のリッチな`TypographyEntry`をまだ解釈できず、より単純なフラット形式（`items:`直下に`item_key`/`canonical_value`/`provenance_source`等を持つリスト）を読み込む。`item_key`が置換対象の文字列、`canonical_value`が置換後の文字列に対応する（`normalizers/normalizer.py`の`_apply_typography`）。`typo-fullwidth-space.yaml`（Phase6 Task14-0で追加）はこのフラット形式の実例である。

## 方針

- Normalizerは、他のカテゴリ（`alias` / `organization` / `position` / `rank`）による名称マッチングより**先に**本カテゴリのルールを適用する（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#normalizervalidatorでの適用順序)）。
- 既存ルールの変更は過去データの再現性に影響し得るため、影響範囲をPR説明に明記する。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#typography) を参照。
