# layouts/

## 責務

防衛省人事発令PDFの**様式（レイアウト）ごとの構造定義**を、コードではなくデータとして保持する場所。設計判断の背景は [ADR-0003](../docs/adr/0003-layout-definition-strategy.md) を参照。

パース処理本体（`src/`）はレイアウト定義を解釈する汎用エンジンとして実装され、様式固有のロジックを持たない。新しい様式への対応は、原則としてこのディレクトリへの追加のみで完結させることを目標とする。

## 想定する構成

```
layouts/
  <era_id>/              # 例: 2019_format_a, 2022_format_b など、様式を一意に識別するID
    manifest.yaml         # 適用期間、様式の識別方法、対応フィールド定義 等
```

- `era_id` は様式を一意に識別する名前とする（西暦年＋様式名等、命名規則は実装時に確定）。
- `manifest.yaml`（形式は仮）には、その様式が適用される期間、PDF内でその様式であると判定する方法、各フィールド（氏名・階級・補職・発令日等）をどう抽出するかの定義を持たせる想定。

## 新しい様式の追加手順（概要）

詳細は `CONTRIBUTING.md` の「新しいPDFレイアウトへの対応手順」、および `.github/ISSUE_TEMPLATE/pdf_format_change.md` を参照。

1. 代表サンプルを `sample_pdfs/` に追加する。
2. このディレクトリに新しい `<era_id>/` を追加する。
3. 期待される抽出結果を `sample_outputs/` に追加し、ゴールデンファイルテストで検証する。

## 変更ルール

- 既存の `era_id` の定義を安易に上書きしない。過去のPDFの再現性に影響するため、変更が必要な場合はその影響範囲（過去データへの再処理要否）を確認した上で行う。
- レイアウト定義フォーマット自体（`manifest.yaml` のスキーマ）を変更する場合は、`AGENTS.md` の規定によりADRの起票を検討する。

## `knowledge/layout_notes/` との違い

本ディレクトリは様式の**構造定義**（列位置・見出しパターン等）を保持する正データである。構造定義だけでは表現しきれない、特定 `era_id` 内で発生する既知の例外・補足知識（誤記、代替日付表記等）は [`knowledge/layout_notes/`](../knowledge/layout_notes/README.md)（`category: layout`、[`docs/knowledge/schema.md`](../docs/knowledge/schema.md#layout)）に記録する。構造そのものを変える場合は本ディレクトリを、構造は変えず例外的な扱いを追記する場合は `knowledge/layout_notes/` を更新する。
