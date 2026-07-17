# docs/

## 責務

コードそのものではなく「なぜこの設計になっているか」「システム全体がどう繋がっているか」「運用時に何をすればよいか」を記録する場所。実装より長生きするドキュメント群。

## 構成

| パス | 内容 |
|---|---|
| [`architecture.md`](architecture.md) | システム全体のパイプライン設計・コンポーネント間の責務分担 |
| [`data_model.md`](data_model.md) | データモデル（概念設計・ER図相当） |
| [`glossary.md`](glossary.md) | ドメイン用語集（発令・辞令・階級 等） |
| [`adr/`](adr/) | Architecture Decision Record（設計判断の記録） |
| [`operations/`](operations/) | 運用手順書（Runbook） |

## 方針

- 実装と乖離したドキュメントは無価値どころか害になる。コードを変更してドキュメントの前提が崩れたら、同じPRでドキュメントも更新する。
- 「なぜ」を記録すべき決定は `docs/adr/` に、「どう動くか」は `architecture.md` / `data_model.md` に、「どう運用するか」は `operations/` に書く、と役割を分ける。
