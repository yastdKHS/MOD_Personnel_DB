# Roadmap

> 実装変更を伴わない、将来のメジャーバージョンに向けた設計改善候補を記録する。ADR起票済みの決定事項ではなく、「いつか再評価すべき候補」の一覧である。個々の項目の詳細背景は、対応するADR・[`docs/design-freeze.md`](design-freeze.md)のDeferred Decisions節を正とし、本ドキュメントは一覧性のためのポインタとして扱う。

## 使い方

- 新しい改善候補を追加する際は、`Priority` / `Target` / `Status` を明記し、詳細な背景・理由は対応するADR（または`design-freeze.md`のDeferred Decisions節）に記載する。本ドキュメント自体に長い説明を書かない。
- `Status` は `Deferred`（未着手・再評価待ち）/ `In Progress`（着手済み、対応するADR・PRあり）/ `Done`（完了、対応するADRのステータスがAccepted済み）のいずれかを用いる。
- 本ドキュメントへの追加自体は、実装着手を意味しない。実装に着手する場合は、通常のADRプロセス（[`docs/adr/README.md`](adr/README.md)）に従う。

## Architecture Improvement

| 項目 | Priority | Target | Status | 詳細 |
|---|---|---|---|---|
| `Document.file_path`保持方式の再評価（`DocumentReference` / `Artifact Locator` / Repository経由解決 / Storage Abstraction） | Low | Version 3 | Deferred | [ADR-0035 Future Improvements](adr/0035-layout-detector-owns-pdf-content-access.md#future-improvements), [`docs/design-freeze.md`のDeferred Decisions](design-freeze.md#deferred-decisions) |

## 関連ドキュメント

- [`docs/design-freeze.md`](design-freeze.md) — Design Freeze Review（Deferred Decisions節）
- [`docs/adr/README.md`](adr/README.md) — ADR起票プロセス
