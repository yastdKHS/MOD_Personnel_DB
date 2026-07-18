# knowledge/aliases/

> `category: alias`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#alias)）に対応するディレクトリ。

## 責務

氏名表記の異体字・旧字体・新字体等、**特定の個人に紐づく**表記バリエーションを、同一人物として名寄せするための対応データとして保持する。値に依存しない機械的な文字レベルの変換規則は `knowledge/typography/` に分離する（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#8カテゴリの分離方針)の役割分担）。

## スキーマ

エントリの形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#alias) の `AliasEntry` 定義（JSON Schema Draft 2020-12）に従う。ファイル名は `<id>.yaml`（例: `alias-example-person-001.yaml`）とする。

## 方針

- 名寄せは誤ると別人を同一視する重大な誤りにつながるため、機械的な類似度判定のみに頼らず、根拠（`provenance.source`）を明示できるデータとして管理する。
- 個人情報の取り扱い範囲は [ADR-0008](../../docs/adr/0008-data-ethics-policy.md) の方針に従う。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#alias) を参照。
