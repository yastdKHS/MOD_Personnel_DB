# .github/workflows/

## 責務

GitHub Actions によるCI（継続的インテグレーション）の定義。

## 現状の方針

`src/` にまだ実装コードが存在しない設計フェーズのため、`ci.yml` の各ジョブは対象ファイルの有無を確認し、存在しない場合はスキップする構成にしている。実装が `src/` および `tests/` に追加され次第、自動的にlint・型チェック・テストの対象になる。

## 今後追加予定のワークフロー

- `release.yml`: データベースのバージョン付き公開（`docs/adr/0010-ci-cd-and-publish-strategy.md` 参照、未実装）
- `layout-validation.yml`: `layouts/` 追加時に `sample_pdfs/` / `sample_outputs/` との整合を検証する専用ジョブ（未実装）
