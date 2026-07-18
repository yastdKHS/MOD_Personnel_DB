# knowledge/validation/

> `category: validation`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#validation)）に対応するディレクトリ。

## 責務

Validator（[ADR-0011](../../docs/adr/0011-fixed-core-pipeline.md)）が参照する、許容値・制約ルールを保持する。「何があり得る値か」という判定基準そのものを `src/` のコードではなくデータとして表現する（[ADR-0012](../../docs/adr/0012-error-handling-priority-order.md)の優先順位方針をValidatorにも適用したもの）。

## スキーマ

エントリの形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#validation) の `ValidationEntry` 定義（JSON Schema Draft 2020-12）に従う。ファイル名は `<id>.yaml`（例: `val-rank-allowed-values-ground.yaml`）とする。

## 方針

- `severity: error` の違反は `candidate_records.validation_status = 'failed'` の根拠になり、`severity: warning` は `learning_dataset` への記録対象とする（[`docs/database/schema.md`](../../docs/database/schema.md)参照）。
- `rank` 等、他カテゴリのエンティティ追加と連動する制約（許容値集合等）は、対応するエンティティ追加と同一PRで更新する。
- `warning` から `error` への変更は既存データへの影響があるため、影響件数の見積もりをPR説明に含める。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#validation) を参照。
