# 0027. Review Domainの中核化

## ステータス
Accepted

## コンテキスト

[ADR-0021](0021-review-ui-strategy.md)は、人手レビューのインターフェースをCLIとする方針を決定したが、レビューという業務そのものの**ドメインモデル**（何が状態としてあり、誰がどう遷移させるか）は未定義のままだった。`docs/database/schema.md`の`review_sessions` / `review_changes`は最小限のスキーマにとどまり、割当（誰にいつ割り当てるか）・決定（承認/差戻しの単位）・優先順位付け・メトリクスといった、レビューを継続的に回すための仕組みが欠けていた。

一方で、[ADR-0010](0010-ci-cd-and-publish-strategy.md)の「人手ゲート」原則と[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)の保証8（Reviewはgold_recordsだけ更新できる）が示すとおり、Human Reviewは本プロジェクトの品質保証における要である。GUIの有無に関わらず独立して設計されるべき**ドメイン**として、レビューを一級市民に引き上げる必要があった。

## 決定

- Human Reviewを「Review Domain」として設計する。UIの実装形態（CLI/Web）とは独立したドメインモデル・ポリシー・優先順位付け・メトリクスを、[`docs/review/`](../review/)配下に定義する。
  - [`docs/review/domain.md`](../review/domain.md): Review Lifecycle（状態遷移図）、`ReviewSession` / `ReviewAssignment` / `ReviewDecision` / `ReviewComment` / `ReviewHistory` / `ReviewStatistics`
  - [`docs/review/policy.md`](../review/policy.md): 承認権限、差戻し、再レビュー、Confidence Override、Knowledge/Learning Dataset登録条件、Gold更新条件
  - [`docs/review/queue.md`](../review/queue.md): 優先順位のスコアリング
  - [`docs/review/metrics.md`](../review/metrics.md): Review Time等6指標
  - [`docs/api/review.md`](../api/review.md): 上記を実装可能な契約に落とし込んだAPI
- `docs/architecture/architecture-contract.md`に保証9（Reviewだけがgold_recordsを書き換えられる）を追加し、保証8（Reviewはgold_recordsだけ更新できる）と対にして、`GoldRepository`への書き込み経路の排他性を明文化する。
- `ReviewAssignment` / `ReviewDecision` / `ReviewComment`は`docs/database/schema.md`にまだ存在しない新設概念であり、本ADRの時点ではドメインモデルの設計に留める。DDLへの反映（`review_assignments`等のテーブル追加）は実装着手時に非破壊的な変更として行い、必要であれば別途ADRを起票する。

## 検討した代替案

- **レビューをCLIツールの実装詳細として扱い、独立したドメインモデルを作らない**: [ADR-0021](0021-review-ui-strategy.md)のCLI決定だけで十分という案も検討したが、優先順位付け（[`queue.md`](../review/queue.md)）やメトリクス（[`metrics.md`](../review/metrics.md)）はUIの実装とは独立した関心事であり、CLIの実装詳細に埋め込むと、将来Web UIへ移行する際にロジックの再実装が必要になる。ドメインとUIを分離する方針とした。
- **既存の`review_sessions` / `review_changes`のみで割当・決定を表現する**: `review_changes`は個々のフィールド修正の記録であり、「この候補は誰に割り当てられ、最終的にどう決定したか」という粒度の異なる情報を無理に押し込めると、クエリ・監査が複雑になる。`ReviewAssignment` / `ReviewDecision`として明示的に分離する方針とした。

## 結果（トレードオフ）

- 新設概念（`ReviewAssignment`, `ReviewDecision`, `ReviewComment`）は、実装時に対応するテーブル追加を要する。既存12テーブルに対する非破壊的な追加ではあるが、設計と実装の間にギャップが生じている状態を一時的に許容する（本ADRおよび[`docs/review/domain.md`](../review/domain.md#既存スキーマとの関係)に明記済み）。
- Review Domainをドメイン層として独立させたことで、[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)の保証9（`review/`のみが`GoldRepository`に書き込む）が、単なる申し合わせではなくパッケージ依存関係として検証可能になる。
