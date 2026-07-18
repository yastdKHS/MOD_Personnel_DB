# knowledge/historical/

> `category: historical`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#historical)）に対応するディレクトリ。

## 責務

組織改称・階級制度改正・官職名変更等、`organization` / `position` / `rank` にまたがる「いつ・何が・なぜ変わったか」という変更イベントそのものを記録する。各カテゴリのエンティティが「ある時点での正式名称」という**状態**を保持するのに対し、本ディレクトリは変更の**経緯・根拠**を保持するという役割分担である（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#8カテゴリの分離方針)参照）。

## スキーマ

エントリの形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#historical) の `HistoricalEntry` 定義（JSON Schema Draft 2020-12）に従う。ファイル名は `<id>.yaml`（例: `hist-2024-001.yaml`）とする。

## 方針

- `organization` / `position` / `rank` 側で改称・改編を反映するPRには、対応する本カテゴリのエントリ追加を必須とする。
- 一度記録したイベントの内容は、誤記修正以外では変更しない（イベントログ的性質）。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#historical) を参照。
