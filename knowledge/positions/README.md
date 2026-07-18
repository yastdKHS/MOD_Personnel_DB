# knowledge/positions/

> `category: position`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#position)）に対応するディレクトリ。

## 責務

官職・補職名（例: 師団長、第1課長等）の名称エンティティと、その表記ゆれ・改称履歴を保持する。`rank`（階級）とは異なる概念であり、両者を混同しない（階級は自衛官の身分上の等級、官職・補職は具体的な役職・ポスト）。

## スキーマ

エントリの形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#position) の `PositionEntry` 定義（JSON Schema Draft 2020-12）に従う。ファイル名は `<id>.yaml`（例: `pos-division-commander.yaml`）とする。

## 方針

- 官職名がいつからいつまで正式だったかは、エントリの `effective_from` / `effective_to` で表現する。改称時は新エンティティを追加し `predecessor_id` / `successor_id` で連結する。
- 改称の経緯・根拠は `knowledge/historical/` に別途記録する。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#position) を参照。
