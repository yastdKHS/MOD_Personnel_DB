# 0034. Document Analyzerの実装にpypdfを採用する

## ステータス
Accepted

## コンテキスト

Document Analyzer（[ADR-0032](0032-redefine-document-analyzer-responsibility.md)がVersion 2.0で定めた責務: PDFの存在確認・メタデータ取得・健全性確認・基本統計・警告生成）の実装には、PDFのページ数・暗号化有無・回転情報・破損検知・軽量テキスト長プローブを行う手段が必要である。

[ADR-0026](0026-security-policy.md)は「PDFパースライブラリの選定時（実装着手時）に、既知の脆弱性・実績・メンテナンス状況を選定基準に含める」と定め、選定を実装着手時（本Phase2 Task4）に明示的に先送りしていた。本プロジェクトは`pyproject.toml`の`dependencies`が空であり（[ADR-0001](0001-python-packaging.md)の依存最小化方針）、新規ライブラリの追加は`CLAUDE.md`・`AGENTS.md`が定める「依存ライブラリの新規追加は着手前にユーザー確認」の対象である。

## 決定

**Document Analyzerの実装に`pypdf`（PyPI: `pypdf`）を採用する。** `pyproject.toml`の`dependencies`に`pypdf>=6.0.0`を追加する。

選定理由:
- **純Python実装**: コンパイル済みバイナリ拡張（C/C++）に依存しない。`src/`レイアウト（[ADR-0001](0001-python-packaging.md)）・GitHub Actions実行環境（[ADR-0010](0010-ci-cd-and-publish-strategy.md)）への導入が単純で、クロスプラットフォームの互換性リスクが低い。
- **MITライセンス**: 恒久的に利用可能な許諾条件であり、ライセンス選定が未確定（[`docs/design-freeze.md`](../design-freeze.md)「不足点」#1）の本プロジェクトの将来のライセンス選択を制約しない。
- **活発なメンテナンス**: PyPDF2の後継として現在も継続的にリリースされている（[ADR-0026](0026-security-policy.md)が求める「メンテナンス状況」基準を満たす）。
- **必要十分な機能**: `PdfReader.is_encrypted` / `.pages` / `.pdf_header`、`PageObject.rotation` / `.images` / `.extract_text()`のみで、Document Analyzerが必要とする責務（存在確認・メタデータ・健全性・統計・軽量テキスト長プローブ）をすべて満たす。Layout Detector以降が将来必要とする可能性のある高度なレイアウト解析機能（座標付きテキスト抽出等）は現時点では使用しない。

## 検討した代替案

- **pikepdf**: qpdf（C++）バックエンドを持ち、破損PDFの検知・修復に強いが、コンパイル済み拡張への依存を追加するため、`pypdf`の純Python実装より導入・保守コストが高い。Document Analyzerが必要とする健全性チェックの精度差は、本プロジェクトの用途（防衛省公表PDFという比較的整った入力）では小さいと判断し、より軽量な`pypdf`を優先した。
- **PyMuPDF（fitz）**: 高機能・高速だが、AGPL/商用デュアルライセンスであり、ライセンス未選定（[`docs/design-freeze.md`](../design-freeze.md)不足点#1）の本プロジェクトの将来のライセンス選択（特に永続的公開を前提とする本プロジェクトの性質、[ADR-0008](0008-data-ethics-policy.md)）を不必要に制約するリスクがあるため見送った。
- **pdfminer.six**: テキストレイアウト抽出に強いが、本Task（Document Analyzer）が必要とするメタデータ・健全性・統計取得の機能は`pypdf`と同等かそれ以下であり、`pypdf`より優位な理由がなかった。

## 結果（トレードオフ）

- `document/`パッケージ（`src/mod_personnel_db/document/analyzer.py`）が`pypdf`に依存する。[`docs/api/package-design.md`](../api/package-design.md)の`document/`節が定める「依存先: `models/`, `utils/`のみ」という**自プロジェクト内パッケージ間**の依存禁止ルールには抵触しない（`pypdf`は外部ライブラリであり、パッケージ間依存グラフの対象外）。
- `pypdf`固有の例外（`pypdf.errors.PyPdfError`系）は`document/`パッケージ内で捕捉し、`DocumentAnalyzerError`に変換するか`DocumentWarning`（`BROKEN_PDF`等）に変換する。`pypdf`の例外型を`document/`パッケージの外に漏らさない（Task4禁止事項、[`docs/api/python-contract.md`](../api/python-contract.md#例外設計)の例外設計と整合）。
- Layout Detector以降が将来より高度なPDF処理（座標付きテキスト抽出等）を必要とする場合、`pypdf`で不足するならその時点で別ライブラリの追加を再検討する（本ADRはDocument Analyzerの用途に限定した決定である）。
- 依存脆弱性スキャン（[ADR-0026](0026-security-policy.md)が要求するツール、選定はTBD）の対象に`pypdf`が加わる。

## 関連ADR
- [ADR-0001](0001-python-packaging.md) — Pythonパッケージング・依存最小化方針。
- [ADR-0026](0026-security-policy.md) — セキュリティポリシー。PDFパースライブラリの選定基準（実績・メンテナンス状況）を実装着手時に決定するとした先行決定。
- [ADR-0032](0032-redefine-document-analyzer-responsibility.md) — Document Analyzer責務再定義。本ADRが実装するVersion 2.0責務の根拠。
