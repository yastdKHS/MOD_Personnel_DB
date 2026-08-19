# Gate 1-B Final: Ground Truth Storage(方向性のみ承認)

Status: APPROVED（方向性のみ。副次的設計は別Task）
Approved-by: USER
Approved-at: 2026-08-19
Approved-in-task: E30

> 本文書はTask-E29の[`ground-truth-storage-decision.md`](ground-truth-storage-decision.md)を
> 上書きしない。Task-E30で作成した正式化レビュー(`/tmp/taskE30/gate_1_b_final.md`)の内容を、
> ユーザー承認を反映した形でリポジトリへ格納したものである。

## 承認された内容

Ground Truthの保存方式として、**「実データはGit外で管理し、Gitにはmanifestおよび
構造的判定情報を管理する」方式2の方向性**を承認する。

- Gitに保存するもの: manifest(PDF識別子・Section識別子・Block範囲等の位置参照)、
  構造的判定ラベル(BlockKind・Hybrid判定・adjacency分類等、Gate 1-Aの承認内容と対応)。
- Git外に保存するもの: 1643 PDF実ファイル自体(既存の`.gitignore`の`/data/`パターンに従う、
  新規の保存方式ではなく既存corpusの扱いをそのまま踏襲)。

## 既存ルールとの整合性(承認済み根拠、変更なし)

| 確認先 | 整合性 |
|---|---|
| CLAUDE.md | 抵触なし |
| AGENTS.md | 抵触なし |
| ADR-0008 | 抵触なし |
| `docs/database/schema.md`(`pdfs.file_path`) | 整合(既存の外部参照設計と一致) |
| `.gitignore`(`/data/`パターン) | 整合(既存の先例と一致) |

## 未承認のまま別Taskで設計する事項

以下は、**方向性としては承認されたが、具体的な設計は未確定**であり、別Taskで検討する。

| 項目 | 状態 |
|---|---|
| Git外ストレージの永続性 | **未確定**(別Task) |
| バックアップ | **未確定**(別Task) |
| アクセス管理 | **未確定**(別Task) |
| 再現性(実データ側) | **未確定**(別Task) |
| 実データの具体的な保存先(`/data/`の再利用か新規ロケーションか) | **未確定**(別Task) |
| ID体系・checksum/hash・versioning・manifest詳細スキーマ | **未確定**(別Task) |

## 引き続きGround Truth実データを作成しないことの確認

本文書はGate 1-Bの**格納方式の方向性**を承認したものであり、Ground Truth実データの
作成・実際のストレージ構築を承認するものではない。上記「未承認のまま別Taskで設計する
事項」がすべて解決するまで、実データ構築には着手しない。
