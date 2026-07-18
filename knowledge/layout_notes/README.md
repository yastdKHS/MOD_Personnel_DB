# knowledge/layout_notes/

> `category: layout`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#layout)）に対応するディレクトリ。旧 `knowledge/known_issues/` を改称したもの（トップレベルの [`layouts/`](../../layouts/README.md) との名称衝突を避けるため）。

## 責務

特定のレイアウト（`era_id`）に固有の、既知の例外・補足知識を記録する。トップレベルの `layouts/`（[ADR-0003](../../docs/adr/0003-layout-definition-strategy.md)）が様式の**構造定義**（列位置・見出しパターン等）を保持するのに対し、本ディレクトリはその構造定義だけでは表現しきれない、特定 `era_id` 内で発生する例外（誤記、代替日付表記、OCR起因の癖等）を保持する。

## スキーマ

エントリの形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#layout) の `LayoutEntry` 定義（JSON Schema Draft 2020-12）に従う。ファイル名は `<id>.yaml`（例: `layoutnote-2022-format-b-date-typo.yaml`）とする。

## 方針

- 「バグトラッカー」ではなく、再発しうる一般的な知見の蓄積場所である。個別の実装タスクの進捗管理はGitHub Issuesで行う。
- 構造そのものを変えたい場合（列位置が根本的に違う等）は、本ディレクトリではなくトップレベル `layouts/` への新規様式追加で対応する（[ADR-0012](../../docs/adr/0012-error-handling-priority-order.md)）。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#layout) を参照。
