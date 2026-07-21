# knowledge/positions/

> `category: position`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#position)）に対応するディレクトリ。

## 責務

官職・補職名（例: 師団長、第1課長等）の名称エンティティと、その表記ゆれ・改称履歴を保持する。`rank`（階級）とは異なる概念であり、両者を混同しない（階級は自衛官の身分上の等級、官職・補職は具体的な役職・ポスト）。

## スキーマ

エントリの目標形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#position) の `PositionEntry` 定義（JSON Schema Draft 2020-12）である。ファイル名は `<id>.yaml`（例: `pos-division-commander.yaml`）とする。

**現在の実データ形式**: 実装済みの読み込みコード（`src/mod_personnel_db/knowledge/loader.py`）は上記のリッチな`PositionEntry`をまだ解釈できず、より単純なフラット形式（`items:`直下に`item_key`/`canonical_value`/`provenance_source`等を持つリスト）を読み込む。`pos-division-commander.yaml`（Phase6 Task14-0で追加）はこのフラット形式の実例である。

## 方針

- 官職名がいつからいつまで正式だったかは、エントリの `effective_from` / `effective_to` で表現する。改称時は新エンティティを追加し `predecessor_id` / `successor_id` で連結する。
- 改称の経緯・根拠は `knowledge/historical/` に別途記録する。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#position) を参照。
