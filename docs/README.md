# docs/

## 責務

コードそのものではなく「なぜこの設計になっているか」「システム全体がどう繋がっているか」「運用時に何をすればよいか」を記録する場所。実装より長生きするドキュメント群。

## 構成

| パス | 内容 |
|---|---|
| [`constitution.md`](constitution.md) | **Project Constitution**（プロジェクト憲法）。ADR・Architecture Contractを含む本ディレクトリ配下のすべての設計文書より上位に位置する統治文書。変更にはプロジェクトオーナーの明示的承認を要する |
| [`architecture.md`](architecture.md) | システム全体のパイプライン設計・コンポーネント間の責務分担 |
| [`configuration.md`](configuration.md) | Configuration Architecture（Environment・Pydantic Settings・Secret管理・Validation Rule・設定Version・Migration・Hot Reload可否） |
| [`architecture/`](architecture/) | Learning Dataset設計、Architecture Contract（分離保証）等の詳細設計 |
| [`data_model.md`](data_model.md) | データモデル（概念設計・ER図相当） |
| [`glossary.md`](glossary.md) | ドメイン用語集（発令・辞令・階級 等） |
| [`adr/`](adr/) | Architecture Decision Record（設計判断の記録） |
| [`api/`](api/) | Interface & Package設計（パッケージ構成・公開API・Repository Pattern・モデル・Pipeline Interface） |
| [`database/`](database/) | SQLite物理スキーマ・公開JSON仕様 |
| [`knowledge/`](knowledge/) | Knowledge Baseスキーマ |
| [`review/`](review/) | Review Domain（ライフサイクル・ドメインモデル・ポリシー・キュー・メトリクス） |
| [`workflow/`](workflow/) | Workflow State Machine（Queued〜Archivedのライフサイクル、Timeout/Retry/Rollback/Checkpoint） |
| [`operations/`](operations/) | 運用手順書（Runbook）、Observability設計 |

## 方針

- 実装と乖離したドキュメントは無価値どころか害になる。コードを変更してドキュメントの前提が崩れたら、同じPRでドキュメントも更新する。
- 「なぜ」を記録すべき決定は `docs/adr/` に、「どう動くか」は `architecture.md` / `data_model.md` に、「どう運用するか」は `operations/` に書く、と役割を分ける。
