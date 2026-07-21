# knowledge/organizations/

> `category: organization`（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#organization)）に対応するディレクトリ。

## 責務

部隊・機関などの組織名の名称期間エンティティを保持する。改称・改編の経緯・根拠は `knowledge/historical/` に分離して記録する（[`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#8カテゴリの分離方針)の役割分担）。

## スキーマ

エントリの目標形式は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#organization) の `OrganizationEntry` 定義（JSON Schema Draft 2020-12）である。ファイル名は `<id>.yaml`（例: `org-jgsdf-1st-division-1962.yaml`）とする。

**現在の実データ形式**: 実装済みの読み込みコード（`src/mod_personnel_db/knowledge/loader.py`）は上記のリッチな`OrganizationEntry`をまだ解釈できず、より単純なフラット形式（`items:`直下に`item_key`/`canonical_value`/`provenance_source`等を持つリスト）を読み込む。`org-ground-staff-office.yaml`（Phase6 Task14-0で追加）はこのフラット形式の実例である。

## 方針

- 「現在の名称」だけでなく「いつからいつまでどの名称だったか」を `effective_from` / `effective_to` で時系列に保持し、過去のPDFに記載された旧称も正しく当時の組織実体に紐づけられるようにする。
- 改称時は既存エントリを書き換えず、新しいエンティティ（新しい `id`）を追加し `predecessor_id` / `successor_id` で連結する。
- 更新ルールの詳細は [`docs/knowledge/schema.md`](../../docs/knowledge/schema.md#organization) を参照。
