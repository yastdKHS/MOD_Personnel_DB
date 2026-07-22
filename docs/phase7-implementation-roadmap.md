# Phase7 Implementation Roadmap

> v1.0.0 Release Candidate（[`RELEASE_STATUS.md`](../RELEASE_STATUS.md)）を基準として、未実装4パッケージ（`features/` / `fetch/` / `ftp/` / `services/`）の設計方針・依存方向を確定し（Phase7 Task16-0）、Phase7以降の実装順序を記録する。**本ドキュメントはドキュメントのみの成果物であり、実装着手そのものを許可・指示するものではない**（[`docs/roadmap.md`](roadmap.md)と同じ扱い）。各パッケージの実装に着手する際は、通常のADRプロセス（[`docs/adr/README.md`](adr/README.md)）に従い新規ADRを起票したうえで着手する。

## 対象読者・関連ドキュメントとの関係

- 各パッケージの詳細な責務・依存先・依存禁止は[`docs/api/package-design.md`](api/package-design.md)の該当節（`features/`・`ftp/`・`fetch/`・`services/`）が正である。本ドキュメントはそれらの**要約と実装順序**に特化し、内容を重複記載しない。
- 依存方向のグラフ表現は[`docs/api/dependency-rule.md`](api/dependency-rule.md)の「全体依存グラフ」（Mermaid）が正である。
- [`docs/roadmap.md`](roadmap.md)は「将来のメジャーバージョンに向けた設計改善候補（Low優先度、Version 3ターゲット）」を扱う別の文書であり、本ドキュメントが扱う「次フェーズで実装する既存設計候補（Phase7、優先度が高い）」とは register が異なる。両者は独立して管理する。

## 未実装4パッケージの責務定義（要約）

| パッケージ | 目的 | 責務の要約 | 詳細 |
|---|---|---|---|
| `features/`（FeatureStore） | `Confidence`算出等に用いる派生特徴量（`FeatureVector`）を計算・提供する | `RawRecord`/`NormalizedRecord`等から特徴量を都度計算（on-demand、永続化なし） | [`package-design.md`](api/package-design.md)の`features/`節 |
| `ftp/`（FTPService） | FTP/SFTP経由でのファイル配信・取得 | バイト列・パス文字列のみを扱うプロトコル層。ドメインモデル・`config/`のいずれにも依存しない | [`package-design.md`](api/package-design.md)の`ftp/`節 |
| `fetch/` | 発令PDFを取得する（中核パイプラインの外側） | HTTPまたは`ftp/`経由でPDFを取得し`content_hash`で重複排除、`PDFRepository`へ記録。PDF本文の解析は行わない | [`package-design.md`](api/package-design.md)の`fetch/`節 |
| `services/` | 単一の中核パイプライン実行に閉じない横断的な運用オーケストレーション | `Scheduler`（PDF取得→パイプライン実行→レビュー→エクスポート公開等のワークフロー調整） | [`package-design.md`](api/package-design.md)の`services/`節 |

## 依存方向の明文化

Phase7 Task16-0で確定した依存方向（[`dependency-rule.md`](api/dependency-rule.md)の全体依存グラフに反映済み）を要約する。

```
ftp/       --> utils/
fetch/     --> models/, repositories/(抽象 PDFRepository), ftp/, utils/
features/  --> models/, learning/, utils/
services/  --> pipeline/, review/, export/, fetch/, ftp/, models/, utils/

pipeline/（JobRunner） -.-> features/   （値オブジェクトFeatureVectorの注入のみ。実行ロジック依存ではない）
```

- `fetch/`は`ftp/`に依存する（FTP経由の取得を選択した場合の実装手段として）。したがって**`ftp/`は`fetch/`より先に実装する必要がある**（依存先が未実装のままでは`fetch/`の該当経路を実装できない）。
- `features/`は`fetch/`・`ftp/`のいずれにも依存せず、独立している。既存の実装済みパッケージ（`models/`・`learning/`）のみに依存するため、他の3パッケージと並行して、または任意の順序で着手できる。
- `services/`は4パッケージの中で最も依存が広く（`fetch/`・`ftp/`・既存の`pipeline/`・`review/`・`export/`すべてに依存）、**必ず最後に実装する**。
- 中核パイプライン6段階（`document/`〜`validators/`）は、この4パッケージのいずれからも直接依存されない（`features/`は`JobRunner`経由の値オブジェクト注入のみで6段階から直接参照されず、`fetch/`は6段階への依存を持たない）。この構造は維持されたまま実装される。

## Architecture Contractとの整合確認

[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)が定めるGuarantee 1〜15のうち、4パッケージの設計に関連するものを確認した。中核パイプライン6段階間の相互分離を定めるGuarantee 1〜6・10・12は、6段階の構成・相互依存を変更しないため対象外（無関係）である。

| Guarantee | 確認結果 |
|---|---|
| G7（Repositoryが具体DB技術を隠蔽） | `fetch/`は`repositories/`（抽象、`PDFRepository`）のみに依存し、`repositories/sqlite/`（具象）には依存しない設計を維持する。矛盾なし。 |
| G8/G9（gold_recordsの書き換えはReviewのみ） | `features/`・`fetch/`・`ftp/`・`services/`のいずれも`GoldRepository.add_version()`/`supersede()`を呼び出さない設計であり、`gold_records`書き込み経路は`review/`の`_promote_to_gold()`に一本化されたままである。矛盾なし。 |
| G11（Layout DetectorだけがPDF本文にアクセスできる） | `fetch/`はPDFバイト列の取得・汎用ファイルハッシュ（`content_hash`）の計算のみを行い、PDF本文の解析・読み取りは行わない設計として明文化した（[`package-design.md`](api/package-design.md)の`fetch/`節「PDF本文へのアクセスに関する制約」）。矛盾なし。 |
| G13（PipelineRunnerはRepository・Knowledge・Learning・Review・Exportを知らない） | `features/`の`JobRunner`経由注入パターンは`PipelineRunner`を経由しない（`JobRunner`のみが`features/`を呼び出す）。`PipelineRunner`が新たに知ることになる外部サービスは存在しない。矛盾なし。 |
| G14（PipelineRunnerは集約Artifactを展開しない） | 4パッケージいずれも`PipelineRunner`の内部実装・Artifact展開ロジックに影響しない。矛盾なし。 |
| G15（依存生成責務はComposition Root（`cli/`）に一本化される） | `features/`・`fetch/`・`ftp/`・`services/`のいずれも自らの具象実装や他パッケージの具象実装を生成しない設計として明文化した。将来これらが実装された場合も、具象実装の生成・配線は引き続き`cli/`（または`cli/`から権限委譲された`services/`が、既に構築済みのインスタンスを受け取って調整するのみ）が担う。矛盾なし。 |

**結論**: 4パッケージの確定した設計方針は、Architecture Contractの15 Guaranteeのいずれとも矛盾しない。Architecture Contract本文（[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)）自体の変更は不要であり、本タスクでは変更していない。

## 実装順序ロードマップ（Phase7以降）

依存方向（上記）に基づき、以下の順序を推奨する。各Phase7.xの実装着手には、当該パッケージの設計を正式決定する新規ADRの起票が前提となる（CLAUDE.mdの「大きな設計変更を行う場合は、先にADRを追加してから実装する」規律）。

| Sub-Phase | パッケージ | 前提（先に必要なもの） | 着手時に起票するADR（想定） | 備考 |
|---|---|---|---|---|
| Phase7.1 | `ftp/` | なし（`utils/`のみに依存、実装済み） | FTPプロトコル層の設計を確定するADR（認証情報を呼び出し側からプレーン引数で受け取る方式の正式決定を含む） | 依存が最小のため最初に着手できる。`fetch/`より先に完了させる必要がある。 |
| Phase7.1′ | `features/` | なし（`models/`・`learning/`に依存、いずれも実装済み） | ADR-0040/ADR-0041に準じ、`Normalizer`/`Validator`のコンストラクタへの`FeatureVector`注入を正式決定するADR | `ftp/`・`fetch/`とは独立しており、Phase7.1と並行して着手できる。 |
| Phase7.2 | `fetch/` | Phase7.1（`ftp/`）完了 | PDF取得ワークフロー・`content_hash`による重複排除方式を確定するADR（[ADR-0006](adr/0006-pipeline-provenance.md)との関係を明記） | `ftp/`経由の取得経路を実装するため、`ftp/`の完了が前提。HTTP経由の取得のみを先行実装する場合は`ftp/`と並行できる余地もあるが、設計上は`ftp/`完了後を基本順序とする。 |
| Phase7.3 | `services/` | Phase7.1・Phase7.1′・Phase7.2（`ftp/`・`features/`・`fetch/`）およびPhase4までに実装済みの`pipeline/`・`review/`・`export/` | [ADR-0019](adr/0019-workflow-orchestration.md)を実装レベルで具体化するADR（`Scheduler`の実行トリガー方式、`cli/bootstrap.py`の`services/`層への置き換え方針を含む） | 4パッケージの中で依存が最も広いため最後に着手する。 |

**並行実装についての注記**: `features/`（Phase7.1′）は`ftp/`・`fetch/`の実装状況に関わらず着手可能であり、必ずしも表の番号順に厳密に従う必要はない。`services/`（Phase7.3）のみ、他3パッケージすべての完了を前提とする。

## 実装時の共通ルール

- 各パッケージの実装は、CLAUDE.mdの表記ゆれ・例外処理の優先順位（`knowledge/` → `layouts/` → `src/`の例外処理）とは別の設計判断であり、この4パッケージは中核パイプライン6段階に該当しないため、[ADR-0012](adr/0012-error-handling-priority-order.md)の優先順位ルールの直接の対象ではない。ただし`fetch/`が将来PDF内のメタデータ由来の表記ゆれを扱う場合は、同様の優先順位思想（データ側優先）を踏襲することが望ましい。
- 1つのPull Requestでは1パッケージ（1責務）のみを実装する（CLAUDE.mdの「1つのPull Requestでは1つの責務のみを変更する」規律）。表の4行はそれぞれ独立したPRとする想定。
- 各パッケージの実装後は、[`docs/api/package-design.md`](api/package-design.md)・[`docs/api/dependency-rule.md`](api/dependency-rule.md)の「未実装」表記を「実装済み」に更新し、`RELEASE_STATUS.md`のKnown Limitationsから該当項目を除去する（Task15-1・Task15-4で確立した既存の更新手順を踏襲する）。

## 関連ドキュメント

- [`docs/api/package-design.md`](api/package-design.md) — 各パッケージの詳細な責務・依存先・依存禁止（Package Design）
- [`docs/api/dependency-rule.md`](api/dependency-rule.md) — 全体依存グラフ（Dependency Rule）
- [`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md) — Architecture Contract（15 Guarantee）
- [`docs/roadmap.md`](roadmap.md) — 将来のメジャーバージョンに向けた設計改善候補（本ドキュメントとは別register）
- [`RELEASE_STATUS.md`](../RELEASE_STATUS.md) — v1.0.0 Release Candidateのリリース判定・Known Limitations
- [`docs/adr/README.md`](adr/README.md) — ADR起票プロセス
