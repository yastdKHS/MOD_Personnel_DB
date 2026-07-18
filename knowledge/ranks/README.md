# knowledge/ranks/

> `category: rank`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#rank)）に対応するディレクトリ。

## 責務

自衛官の階級呼称の名称期間エンティティと、その序列（`rank_order`）を保持する。官職・補職（`knowledge/positions/`）とは異なる概念であり、混同しない。

## スキーマ

エントリの形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#rank) の `RankEntry` 定義（JSON Schema Draft 2020-12）に従う。ファイル名は `<id>.yaml`（例: `rank-1st-lieutenant-ground.yaml`）とする。

## 方針

- PDF上の表記ゆれ（全角/半角、送り仮名の違い等の機械的な差異は `knowledge/typography/` で先に吸収した上で）を `aliases` で吸収し、正規化後の統一表現へマッピングするための参照データとして使う。
- `service_branch`（陸/海/空/統合）ごとに `rank_order` で序列を持ち、Validator（`knowledge/validation/`）が「あり得る階級か」を判定する際の基礎データとする。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#rank) を参照。
