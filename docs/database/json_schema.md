# 公開JSON仕様（JSON Schema Draft 2020-12）

> **位置づけ**: 本ドキュメントは、[`docs/database/schema.md`](schema.md) で定義した `exports`（`format='json'`）が生成する、**外部公開用JSONの契約（インターフェース仕様）**を定義します。[ADR-0016](../adr/0016-public-json-format.md) により正式決定として承認されています。
>
> **`tests/golden` / `sample_outputs/*.json` との違い**: `sample_outputs/` のJSONは、パイプライン内部（Field Extractor〜Normalizer）の期待出力を検証するための**内部テスト用フィクスチャ**であり（[ADR-0007](../adr/0007-golden-file-testing.md)）、本ドキュメントが定義する**外部公開契約**とは目的も安定性の要求水準も異なる。両者を混同しないこと。
>
> **コードはまだ実装していません。** 本ドキュメントのJSON Schemaは設計仕様です。実装着手時に、下記の[実装時の配置](#実装時の配置想定)に記載するパスへ、本ドキュメントと同一内容のスキーマファイルを配置します。

## 目次

1. [要求仕様との対応](#要求仕様との対応)
2. [バージョン管理](#バージョン管理)
3. [JSON Schema本体](#json-schema本体)
4. [フィールド仕様の解説](#フィールド仕様の解説)
5. [confidenceの算出ルール](#confidenceの算出ルール)
6. [サンプルインスタンス](#サンプルインスタンス)
7. [Draft 2020-12に関する留意事項](#draft-2020-12に関する留意事項)
8. [公開範囲・データ倫理上の制約](#公開範囲データ倫理上の制約)
9. [互換性・進化ポリシー](#互換性進化ポリシー)
10. [実装時の配置（想定）](#実装時の配置想定)
11. [関連ADR](#関連adr)

---

## 要求仕様との対応

| 要求項目 | スキーマ上の位置 | 対応する内部テーブル（[`schema.md`](schema.md)） |
|---|---|---|
| Version管理 | ルート `schema_version`（この形式自体のSemVer）+ `$id` のURIバージョニング | — （本ドキュメント固有の管理対象） |
| `generated_at` | ルート直下 `generated_at` | `exports.created_at` |
| `parser_version` | `records[].provenance.parser_version` | `parser_versions.code_version` |
| `source_pdf` | `records[].provenance.source_pdf` | `pdfs`（`content_hash` / `source_url` / `published_date`） |
| `confidence` | `records[].confidence`（`score` + `band`） | `candidate_records.validation_status` / `review_changes` / `learning_dataset` から算出（[confidenceの算出ルール](#confidenceの算出ルール)参照） |

`parser_version` と `source_pdf` はレコードごとに異なり得る（同一エクスポートファイルに、異なる時期・異なるコードバージョンで生成されたレコードが混在するため）ため、ルート直下ではなく各レコードの `provenance` 配下に配置する。`generated_at` はエクスポート実行という単一の事象を表すため、ルート直下に1つだけ持つ。

---

## バージョン管理

本プロジェクトでは「バージョン」を3層に分けて管理する（[`schema.md`](schema.md#バージョン管理) の2層に、本ドキュメントで公開JSON形式のバージョンを追加する）。

| 層 | 対象 | 管理方法 |
|---|---|---|
| 1. DBスキーマバージョン | SQLiteの表構造そのもの | `schema_migrations` テーブル + `PRAGMA user_version`（[`schema.md`](schema.md#バージョン管理)） |
| 2. データ生成バージョン | どのコード・知識ベースでデータが生成されたか | `parser_versions.code_version`（[`schema.md`](schema.md#10-parser_versions)） |
| 3. **公開JSON形式バージョン**（本ドキュメント） | 外部公開インターフェースの契約そのもの | 本セクションで定義 |

この3層は互いに独立して変化する。例えば、DBに列を1つ追加してもスキーマバージョンは上がるが、それを公開JSONに含めるかは別の意思決定であり、公開JSON形式バージョンは自動連動しない。

### 管理方法

- **SemVer**: 公開JSON形式は `MAJOR.MINOR.PATCH` で管理し、生成される各エクスポートの `schema_version` フィールドに埋め込む（例: `"1.0.0"`）。
  - **MAJOR**: 後方互換性を壊す変更（フィールド削除・名称変更・型変更・`required` への追加等）。[ADR-0016](../adr/0016-public-json-format.md) に準じ、新規ADRを要する。
  - **MINOR**: 後方互換な追加（任意フィールドの追加等）。通常のPRレビューで足りる。
  - **PATCH**: 説明文の修正等、契約内容に影響しない変更。
- **`$id` のURIバージョニング**: JSON SchemaファイルURL自体にメジャーバージョンを埋め込む（例: `.../personnel-export/v1/schema.json`）。MAJORバージョンが上がった場合のみ `$id` のパスを更新し（`v1` → `v2`）、旧バージョンのスキーマファイルは削除せず残す（過去に発行したエクスポートが、発行時点のスキーマに対して恒久的に検証可能であるようにするため。[ADR-0006](../adr/0006-pipeline-provenance.md) の「削除せず追記する」思想と整合）。
- **`deprecated` キーワード**: Draft 2020-12のメタデータ語彙に含まれる `deprecated: true` を用いて、廃止予定フィールドを次のMAJORバージョンまでの移行期間中は残しつつ明示する（[互換性・進化ポリシー](#互換性進化ポリシー)）。

---

## JSON Schema本体

以下は `jsonschema`（Python、Draft 2020-12実装）でメタスキーマ検証済みである。

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.mod-personnel-db.example/personnel-export/v1/schema.json",
  "title": "MOD Personnel DB Public Export",
  "description": "防衛省人事発令データベースの公開JSONエクスポート形式。exports(format='json')の生成物が満たすべき契約。",
  "type": "object",
  "required": ["schema_version", "generated_at", "export_id", "record_count", "records"],
  "additionalProperties": false,
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "この公開JSON形式自体のSemVerバージョン(MAJOR.MINOR.PATCH)。DBスキーマバージョンやparser_versionとは独立に管理される。"
    },
    "generated_at": {
      "type": "string",
      "format": "date-time",
      "description": "このエクスポートファイルが生成された日時(RFC3339)。exports.created_atに対応する。"
    },
    "as_of": {
      "type": "string",
      "format": "date-time",
      "description": "gold_recordsのどの時点のスナップショットを対象にしたか。exports.as_ofに対応する(任意項目)。"
    },
    "export_id": {
      "type": "string",
      "description": "このエクスポート実行の識別子。exports.idに対応する。"
    },
    "record_count": {
      "type": "integer",
      "minimum": 0,
      "description": "recordsに含まれるレコード件数。exports.record_countと一致する。"
    },
    "checksum": {
      "type": "string",
      "description": "エクスポート内容全体のハッシュ値(再現性検証用)。exports.checksumに対応する(任意項目)。"
    },
    "records": {
      "type": "array",
      "description": "公開対象の発令レコード一覧。",
      "items": { "$ref": "#/$defs/PersonnelRecord" }
    }
  },
  "$defs": {
    "PersonnelRecord": {
      "type": "object",
      "title": "PersonnelRecord",
      "description": "1件の発令情報。gold_recordsの1行に対応する。",
      "required": [
        "id",
        "person",
        "rank",
        "organization",
        "position",
        "appointment_type",
        "effective_date",
        "version",
        "is_current",
        "provenance",
        "confidence"
      ],
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string",
          "description": "公開識別子。gold_records.idに基づく安定的な文字列(例: 'gold-00012345')。"
        },
        "person": { "$ref": "#/$defs/NormalizedValue", "description": "氏名(正規化後/原文)。" },
        "rank": { "$ref": "#/$defs/NormalizedValue", "description": "階級(正規化後/原文)。" },
        "organization": { "$ref": "#/$defs/NormalizedValue", "description": "組織・部隊名(正規化後/原文)。" },
        "position": { "$ref": "#/$defs/NormalizedValue", "description": "官職・補職内容(正規化後/原文)。" },
        "appointment_type": {
          "type": "string",
          "enum": ["assignment", "transfer", "concurrent_post", "other"],
          "description": "発令区分(補職/異動/併任/その他)。内部の自由記述からのマッピングはknowledge/で管理する。"
        },
        "effective_date": {
          "type": "string",
          "format": "date",
          "description": "発令日。gold_records.effective_dateに対応する。"
        },
        "version": {
          "type": "integer",
          "minimum": 1,
          "description": "訂正履歴上のバージョン番号。gold_records.versionに対応する。"
        },
        "is_current": {
          "type": "boolean",
          "description": "現在有効なバージョンか。gold_records.is_currentに対応する。"
        },
        "superseded_by": {
          "type": ["string", "null"],
          "description": "このレコードが訂正され無効化された場合、後続バージョンの公開識別子。現行バージョンの場合はnull(任意項目)。"
        },
        "provenance": { "$ref": "#/$defs/Provenance", "description": "来歴情報。source_pdf・parser_versionを含む。" },
        "confidence": { "$ref": "#/$defs/Confidence", "description": "このレコードの信頼度。" }
      }
    },
    "NormalizedValue": {
      "type": "object",
      "title": "NormalizedValue",
      "description": "正規化後の値と、根拠となるPDF原文の組。",
      "required": ["value"],
      "additionalProperties": false,
      "properties": {
        "value": {
          "type": "string",
          "description": "knowledge/による正規化後の値(canonical value)。"
        },
        "raw": {
          "type": "string",
          "description": "PDF記載の原文(監査用、任意項目)。"
        }
      }
    },
    "Provenance": {
      "type": "object",
      "title": "Provenance",
      "description": "このレコードがどのPDF・どのコードバージョンから生成されたかを示す来歴情報(ADR-0006)。",
      "required": ["source_pdf", "parser_version"],
      "additionalProperties": false,
      "properties": {
        "source_pdf": { "$ref": "#/$defs/SourcePdf" },
        "parser_version": {
          "type": "string",
          "description": "このレコードを生成したコードバージョン。parser_versions.code_versionに対応する。"
        },
        "layout_era_id": {
          "type": "string",
          "description": "適用されたレイアウト定義のera_id。layouts.era_idに対応する(任意項目)。"
        }
      }
    },
    "SourcePdf": {
      "type": "object",
      "title": "SourcePdf",
      "description": "根拠となった発令PDFの情報。pdfsテーブルに対応する。",
      "required": ["content_hash", "source_url", "published_date"],
      "additionalProperties": false,
      "properties": {
        "content_hash": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$",
          "description": "PDFのSHA-256ハッシュ。pdfs.content_hashに対応する。"
        },
        "source_url": {
          "type": "string",
          "format": "uri",
          "description": "取得元URL。pdfs.source_urlに対応する。"
        },
        "published_date": {
          "type": "string",
          "format": "date",
          "description": "PDFの公表日。pdfs.published_dateに対応する。"
        }
      }
    },
    "Confidence": {
      "type": "object",
      "title": "Confidence",
      "description": "このレコードの抽出・正規化に対する信頼度。算出ルールはjson_schema.mdの「confidenceの算出ルール」を参照。",
      "required": ["score", "band"],
      "additionalProperties": false,
      "properties": {
        "score": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "0.0(低)〜1.0(検証済み)の信頼度スコア。"
        },
        "band": {
          "type": "string",
          "enum": ["verified", "high", "medium", "low"],
          "description": "スコアを人間可読なバンドに分類したもの。"
        }
      }
    }
  }
}
```

---

## フィールド仕様の解説

### ルート（`PersonnelExport`）

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `schema_version` | string（SemVer） | ✓ | 本形式のバージョン。[バージョン管理](#バージョン管理)参照 |
| `generated_at` | string（date-time） | ✓ | エクスポート生成日時。`exports.created_at` |
| `as_of` | string（date-time） | — | 対象スナップショット時点。`exports.as_of` |
| `export_id` | string | ✓ | エクスポート識別子。`exports.id` |
| `record_count` | integer | ✓ | レコード件数。`exports.record_count` |
| `checksum` | string | — | 内容ハッシュ。`exports.checksum` |
| `records` | array | ✓ | `PersonnelRecord` の配列 |

### `PersonnelRecord`

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `id` | string | ✓ | 公開識別子（`gold_records.id` 由来） |
| `person` / `rank` / `organization` / `position` | `NormalizedValue` | ✓ | 正規化済みの氏名・階級・組織・官職（原文つき） |
| `appointment_type` | enum | ✓ | `assignment`(補職) / `transfer`(異動) / `concurrent_post`(併任) / `other` |
| `effective_date` | string（date） | ✓ | 発令日。`gold_records.effective_date` |
| `version` | integer | ✓ | 訂正バージョン。`gold_records.version` |
| `is_current` | boolean | ✓ | 現行バージョンか。`gold_records.is_current` |
| `superseded_by` | string \| null | — | 後続バージョンの公開識別子 |
| `provenance` | `Provenance` | ✓ | 来歴（`source_pdf` + `parser_version`） |
| `confidence` | `Confidence` | ✓ | 信頼度（`score` + `band`） |

### `NormalizedValue`

`value`（正規化後、必須）と `raw`（PDF原文、任意）の組。`knowledge/` によるマッピング適用結果と原文の両方を残すことで、公開後に誤りが判明した際の追跡を可能にする（[ADR-0005](../adr/0005-knowledge-base-normalization.md)）。

### `Provenance`

`source_pdf`（`SourcePdf`）と `parser_version`（コードバージョン文字列）を必須とし、`layout_era_id` を任意項目とする。来歴管理方針（[ADR-0006](../adr/0006-pipeline-provenance.md)）に基づき、レコード単位で「どのPDFの記載か」「どのコードで生成されたか」を常に遡れるようにする。

### `SourcePdf`

`content_hash`（SHA-256、64桁16進文字列を `pattern` で強制）、`source_url`（`format: uri`）、`published_date`（`format: date`）の3つを必須とする。`pdfs` テーブルの列と1対1に対応する。

---

## confidenceの算出ルール

`confidence` はDBに直接保存された列ではなく、**Publish段階で既存テーブルから導出する計算値**とする（現時点で `gold_records` に専用列を追加していないため）。将来、算出コストや監査要件から永続化が必要と判断された場合は、`gold_records` への列追加（非破壊的変更）として [`schema.md`](schema.md) を更新する。

| `band` | `score`の目安 | 条件 |
|---|---|---|
| `verified` | `1.0` | 当該 `gold_record` の由来である `candidate_record` に対し、`review_changes` による人手レビューが行われ、内容が確定している |
| `high` | `0.85`以上 | `candidate_records.validation_status = 'passed'` かつ、対応する `learning_dataset` エントリが存在しない（自動処理のみで問題なく確定） |
| `medium` | `0.5`以上`0.85`未満 | `validation_status = 'passed'` だが、正規化に `knowledge_items`（`category='known_issue'` 等、曖昧さを伴う既知パターン）が適用されている |
| `low` | `0.5`未満 | `learning_dataset` に `status='open'`（未解決）のエントリが存在する状態で、暫定的にpublishされた場合（通常の公開フローでは稀。プレビュー公開等の限定用途を想定） |

この算出ルールは、[ADR-0012](../adr/0012-error-handling-priority-order.md) の誤り分類・[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md) のLearning Dataset設計と整合させている。

---

## サンプルインスタンス

上記スキーマに対し検証済みのサンプル。

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-07-18T09:00:00Z",
  "as_of": "2026-07-17T00:00:00Z",
  "export_id": "export-2026-07-18-001",
  "record_count": 1,
  "checksum": "sha256:abc123",
  "records": [
    {
      "id": "gold-00012345",
      "person": { "value": "山田太郎", "raw": "山田太郎" },
      "rank": { "value": "1等陸尉", "raw": "1尉" },
      "organization": { "value": "陸上自衛隊第1師団", "raw": "陸自第1師団" },
      "position": { "value": "第1課長", "raw": "第1課長" },
      "appointment_type": "assignment",
      "effective_date": "2026-04-01",
      "version": 1,
      "is_current": true,
      "superseded_by": null,
      "provenance": {
        "source_pdf": {
          "content_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "source_url": "https://www.mod.go.jp/example/appointment.pdf",
          "published_date": "2026-03-25"
        },
        "parser_version": "v1.2.0",
        "layout_era_id": "2024_format_a"
      },
      "confidence": { "score": 0.95, "band": "high" }
    }
  ]
}
```

氏名・階級・組織・PDF URL等はすべて説明用の架空の値であり、実在の人物・PDFを示すものではない。

---

## Draft 2020-12に関する留意事項

- **`$defs`**: Draft-07以前の `definitions` は用いず、2019-09以降の標準である `$defs` を使用する。参照は `#/$defs/<Name>` のJSON Pointer形式に統一する。
- **`format` はデフォルトでアノテーション（注釈）扱い**: Draft 2020-12の仕様上、`format`（`date-time` / `date` / `uri` 等）はVocabularyとして"Format-Assertion"を明示的に有効化しない限り、検証器は値の妥当性を強制しない（注釈情報としてのみ扱われる）。実装時は、`ajv`（`formats` プラグイン）や Python `jsonschema` の `format_checker=draft202012_format_checker` のように、format-assertionを明示的に有効化したバリデータ設定を用いること。本ドキュメントの検証（[サンプルインスタンス](#サンプルインスタンス)）もこの前提で実施している。
- **`deprecated`**: メタデータ語彙の一部として利用可能（[互換性・進化ポリシー](#互換性進化ポリシー)参照）。
- **`additionalProperties: false`**: 全オブジェクトで意図的に厳格化している。これは外部利用者に対する制約ではなく、**自分たちのPublish段階が仕様外のフィールドを誤って出力していないかを検知するための、生成時の品質ゲート**である（[CLAUDE.md](../../CLAUDE.md)の「正しさより先に、間違いに気づける設計」に対応）。外部の利用者がJSONを緩く解釈する（未知フィールドを無視する）こと自体は妨げない。
- **`unevaluatedProperties` は不使用**: `allOf` 等による合成を行っていないため、本スキーマの範囲では `additionalProperties: false` で十分であり、`unevaluatedProperties` は導入していない。将来 `allOf` によるバリアント定義（例: 廃止予定フィールドを持つv1.xの拡張）が必要になった場合に再検討する。

---

## 公開範囲・データ倫理上の制約

[ADR-0008](../adr/0008-data-ethics-policy.md) の方針に従い、公開JSONに含めるフィールドは発令PDFに記載された職務遂行に関する情報に限定する。

- **含める**: 氏名、階級、所属組織、官職・補職内容、発令区分、発令日、来歴（出典PDF情報）、信頼度
- **含めない**: 住所・連絡先等の私生活上の情報、発令PDFに記載のない推測情報、他データベースとの突合による個人特定を強化する情報

`additionalProperties: false` により、上記制約を超えるフィールドが将来誤って追加された場合も、スキーマ検証で機械的に検知できる。

---

## 互換性・進化ポリシー

| 変更の種類 | 例 | バージョン影響 | 承認プロセス |
|---|---|---|---|
| 破壊的変更 | フィールド削除、型変更、`required`への追加、enum値の削除 | MAJOR（`$id`のパスも更新） | 新規ADR必須 |
| 後方互換な追加 | 任意フィールドの追加、enum値の追加 | MINOR | 通常のPRレビュー |
| 非機能的変更 | `description`の修正、誤字修正 | PATCH | 通常のPRレビュー |
| フィールド廃止予定化 | 次期MAJORで削除予定のフィールドに`deprecated: true`を付与 | MINOR | 通常のPRレビュー（ただし削除自体は別途MAJORで実施） |

- 旧バージョンのスキーマファイル（例: `v1/schema.json`）はMAJORバージョンが上がった後も削除しない。過去に発行済みのエクスポートファイルが、発行当時のスキーマに対して恒久的に検証可能であることを保証するため（[ADR-0006](../adr/0006-pipeline-provenance.md)）。
- 破壊的変更を要する提案は、[`docs/adr/README.md`](../adr/README.md)の基準に従い新規ADRを起票すること。

---

## 実装時の配置（想定）

- **正のスキーマファイル**: `src/mod_personnel_db/publish/schemas/personnel_export.v1.schema.json`（実装着手時に作成。内容は本ドキュメントの[JSON Schema本体](#json-schema本体)と同一に保つ）。
- **検証の実施箇所**: Publish段階（`src/mod_personnel_db/publish/`）が、生成したエクスポートJSONを書き出す前に本スキーマで検証し、不合格の場合は `exports.status='failed'` として記録する（[`schema.md`](schema.md#12-jobs) の `jobs` / `exports` と連携）。
- 本ドキュメントとスキーマファイルの内容が乖離した場合、スキーマファイルを正とし、本ドキュメントを追随して更新する（`layouts/` のファイルと `layouts/README.md` の関係と同様の役割分担）。

---

## 関連ADR

- [ADR-0005](../adr/0005-knowledge-base-normalization.md): `NormalizedValue`（`value`/`raw`）の設計根拠
- [ADR-0006](../adr/0006-pipeline-provenance.md): `Provenance` / `SourcePdf` の設計根拠、旧スキーマを残す方針の根拠
- [ADR-0008](../adr/0008-data-ethics-policy.md): 公開範囲の制約
- [ADR-0010](../adr/0010-ci-cd-and-publish-strategy.md): 公開（Publish）フロー全体の方針
- [ADR-0012](../adr/0012-error-handling-priority-order.md): `confidence`算出ルールの誤り分類との対応
- [ADR-0013](../adr/0013-learning-dataset-not-correction-log.md): `confidence`算出ルールの根拠
- [ADR-0016](../adr/0016-public-json-format.md): 本ドキュメントを正式なスキーマ決定として承認
