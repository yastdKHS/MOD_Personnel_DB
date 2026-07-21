# tests/golden/

## 責務

パーサー・正規化ロジックが「実際のPDFを最後まで正しく処理できるか」を検証するための、ゴールデンファイルテスト用の入力・期待結果を保持する場所（[ADR-0007](../../docs/adr/0007-golden-file-testing.md)、[`docs/testing/test-policy.md`](../../docs/testing/test-policy.md)のGolden Test節）。

## 構成

```
tests/golden/
  sample_pdfs/       # テスト用の入力PDF
  sample_outputs/    # 対応する期待結果（JSON）
```

## トップレベル `sample_pdfs/` / `sample_outputs/` との違い

リポジトリ直下の[`sample_pdfs/`](../../sample_pdfs/README.md)・[`sample_outputs/`](../../sample_outputs/README.md)は、**防衛省が公務として一般公表した実在のPDF**のみを収録する場所と定義されている（同READMEの「収録基準」）。本ディレクトリ（`tests/golden/`配下）はそれとは別に、テストで安定して再現可能な**合成（fabricated）フィクスチャ**を置く場所である。

- `tests/golden/sample_pdfs/`・`tests/golden/sample_outputs/`に収録するPDF・期待結果は、実在の人事発令PDFではなく、パイプラインの動作検証のために作成した合成データである（[`tests/README.md`](../README.md)が`tests/unit/document/`・`tests/unit/layout/`について既に定めている「合成PDFフィクスチャ、実在PDFは使用しない」という方針を、Golden Testにも同様に適用したもの）。
- 実在の公表PDFを用いたGolden Testを追加する場合は、トップレベルの`sample_pdfs/`・`sample_outputs/`（[ADR-0008](../../docs/adr/0008-data-ethics-policy.md)の基準を満たすもの）を用いる。トップレベルの両ディレクトリは本Task（Phase6 Task14-0）時点ではREADMEのみで実データは未投入のままである。

## 収録済みフィクスチャ

| PDF | 対応する期待結果 | era_id | 内容 |
|---|---|---|---|
| [`sample_pdfs/2026_format_sample_20260701_synthetic.pdf`](sample_pdfs/2026_format_sample_20260701_synthetic.pdf) | [`sample_outputs/2026_format_sample_20260701_synthetic.json`](sample_outputs/2026_format_sample_20260701_synthetic.json) | `2026_format_sample`（[`layouts/2026_format_sample/manifest.yaml`](../../layouts/2026_format_sample/manifest.yaml)） | 見出し・1名分の人事異動レコード（氏名・階級・組織・発令日）・末尾行のみを持つ最小構成の合成PDF |

PDFは`pypdf`で生成した、標準14フォントを使わない自前構成のPDFである（環境にLibreOffice等のオーサリングツールが使えなかったため、`ToUnicode` CMapで文字コード→Unicodeの対応を明示する簡易フォントを直接組み立てた）。日本語テキスト（`髙橋一郎`・`三等陸佐`・`陸上幕僚監部`・`令和八年七月一日`等）は`pypdf.PdfReader.extract_text()`で正しく抽出できることを確認済みである（`layout/detector.py`が使うのと同じ`pypdf`ライブラリ・同じ`extract_text()`呼び出し経路で検証した）。

## 期待結果の作成方法

`sample_outputs/*.json`は、対応する`layouts/`・`knowledge/`のデータを用いて、`src/mod_personnel_db`（変更なし）のDocument Analyzer→Layout Detector→Section Parser→Field Extractor→Normalizer→Validatorを実際に実行し、その出力をそのまま記録したものである。手計算・推測による作成は行っていない。`docs/database/json_schema.md`が定める公開JSON形式（`PersonnelRecord`相当、未実装、[`docs/reports/phase5-final-audit.md`](../../docs/reports/phase5-final-audit.md)参照）とは異なる、パイプライン中間結果（`RawRecord`→`NormalizedRecord`→`ValidationResult`）の記録である点に注意する。

## 現時点で未整備のもの

- **自動比較テストコード**: `sample_pdfs/`を実際にパイプラインへ通し`sample_outputs/`と一致することを機械的に検証する`pytest`テストは、本Task（Phase6 Task14-0）の対象外であり、まだ存在しない（`tests/unit/`・`tests/integration/`は本Taskで変更していない）。追加は別Taskで行う。
- 上記フィクスチャは`era_id`1件分のみであり、[`sample_pdfs/README.md`](../../sample_pdfs/README.md)が求める「`layouts/`の各`era_id`に対して最低1件」という網羅は、トップレベル`layouts/`に他の`era_id`が追加された時点で別途対応する。

## 更新ルール

トップレベル[`sample_outputs/README.md`](../../sample_outputs/README.md)と同じ方針に従う。

- ゴールデンファイルの更新は「テストを通すための機械的な作業」ではなく「何が正しい抽出結果かを再定義する行為」である。
- 更新する場合は、なぜ期待値が変わったのか（レイアウト定義の修正、knowledge追加、正規化ロジックの改善等）をPR説明に明記する。
- 無言でのゴールデンファイル書き換えは`CLAUDE.md`/`AGENTS.md`で禁止事項として扱う。
