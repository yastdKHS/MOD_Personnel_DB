# docs/

## 責務

コードそのものではなく「なぜこの設計になっているか」「システム全体がどう繋がっているか」「運用時に何をすればよいか」を記録する場所。実装より長生きするドキュメント群。

## 構成

| パス | 内容 |
|---|---|
| [`constitution.md`](constitution.md) | **Project Constitution**（プロジェクト憲法）。ADR・Architecture Contractを含む本ディレクトリ配下のすべての設計文書より上位に位置する統治文書。変更にはプロジェクトオーナーの明示的承認を要する |
| [`design-freeze.md`](design-freeze.md) | **Design Freeze Review**。全設計領域（Architecture/ADR/Review/Workflow/Knowledge/Repository/Interface/Security/Observability/Configuration/Release）の横断レビュー、不足点・改善点・リスク・TODO一覧、設計完了宣言 |
| [`implementation.md`](implementation.md) | **Implementation Guide**。実装フェーズの最上位ガイドライン（Constitution → ADR → Architecture Contract → Implementation Guideの順で従う）。Repository First等の実装哲学、Version Rule、Definition of Done等27項目 |
| [`coding-style.md`](coding-style.md) | Coding Style Guide（命名規則、関数/クラス/ファイル長、コメント・Docstring方針、型ヒント方針、構文選択、Import順序、禁止事項） |
| [`testing/`](testing/) | Test Policy（Unit/Integration/Golden/Regression/Performance/Acceptance/Benchmark/Mutation Testの目的・実行タイミング・成功条件・Coverage目標） |
| [`parser-guidelines.md`](parser-guidelines.md) | Parser Development Guidelines（本プロジェクト専用のParser開発規約。Knowledge優先順位、Section単位処理、依存禁止、Version/廃止/性能評価） |
| [`implementation-checklist.md`](implementation-checklist.md) | Implementation Checklist（Architecture/ADR/Repository/Knowledge/Review/Workflow/Configuration/Security/Logging/Testing/Observability/CI/CD/Documentation/Definition of Doneのチェック項目） |
| [`developer-workflow.md`](developer-workflow.md) | Developer Workflow（Issue作成〜Deploymentの一連の流れ、Mermaid可視化） |
| [`architecture.md`](architecture.md) | システム全体のパイプライン設計・コンポーネント間の責務分担 |
| [`configuration.md`](configuration.md) | Configuration Architecture（Environment・Pydantic Settings・Secret管理・Validation Rule・設定Version・Migration・Hot Reload可否） |
| [`security.md`](security.md) | Security Architecture（Threat Model・Secret・Supply Chain・GitHub Actions・Dependency・JSON改ざん・FTP・Checksum/Hash・署名・Audit Log・最小権限・Security Review） |
| [`architecture/`](architecture/) | Learning Dataset設計、Architecture Contract（分離保証）等の詳細設計 |
| [`data_model.md`](data_model.md) | データモデル（概念設計・ER図相当） |
| [`glossary.md`](glossary.md) | ドメイン用語集（発令・辞令・階級 等） |
| [`adr/`](adr/) | Architecture Decision Record（設計判断の記録） |
| [`api/`](api/) | Interface & Package設計（パッケージ構成・公開API・Repository Pattern・モデル・Pipeline Interface） |
| [`database/`](database/) | SQLite物理スキーマ・公開JSON仕様 |
| [`knowledge/`](knowledge/) | Knowledge Baseスキーマ |
| [`review/`](review/) | Review Domain（ライフサイクル・ドメインモデル・ポリシー・キュー・メトリクス） |
| [`workflow/`](workflow/) | Workflow State Machine（Queued〜Archivedのライフサイクル、Timeout/Retry/Rollback/Checkpoint） |
| [`operations/`](operations/) | 運用手順書（Runbook）、Observability設計、Release/Rollback/Backup/Disaster Recovery設計 |

## 方針

- 実装と乖離したドキュメントは無価値どころか害になる。コードを変更してドキュメントの前提が崩れたら、同じPRでドキュメントも更新する。
- 「なぜ」を記録すべき決定は `docs/adr/` に、「どう動くか」は `architecture.md` / `data_model.md` に、「どう運用するか」は `operations/` に書く、と役割を分ける。
