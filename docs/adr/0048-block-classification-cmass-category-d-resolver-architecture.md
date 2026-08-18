# 0048. Block分類基盤とC-MASS/Category D Resolver分離アーキテクチャ

## ステータス
Accepted（将来アーキテクチャとしての決定。**本ADR確定時点で、本ADRが定める`Block`/`BlockKind`/`CMassResolver`/`CategoryDResolver`等は一切実装されていない。** 本ADRは「承認済みの将来設計」を記録するものであり、実装済みであることを意味しない。実装は別Taskで行う。）

## 1. コンテキスト（Context）

[ADR-0011](0011-fixed-core-pipeline.md)が固定する6段階パイプライン（Document Analyzer → Layout Detector → Section Parser → Field Extractor → Normalizer → Validator）のうち、Field Extractor段階には、以下2つの独立した実データ調査で確認された構造的な問題が存在する。

1. **C-MASS**: Sectionの中に、`self_contained`（部署+階級+氏名が1行に揃う）・`post_only_fragment`（部署+階級のみ）・`name_only_fragment`（氏名のみ）という複数種類の行ブロックが混在し、fragment系ブロックはN:M（対応数が不一致）の断片対応関係を持つ。
2. **Category D**（[Task-M起源]、`D_line_wrap_split`、1,808 records）: 1人分の情報が2行（action行+data行）に分裂し、1:1の隣接ペアとして出現する。

この2つは症状レベル（`RawRecord`として区別できない生成物）では区別が難しいが、実データ調査により**C-MASSとCategory Dの重複率は47.9%（Task-E2）→39.2%（Task-E5、Rule E適用後）**であることが判明しており、両者は完全に独立した現象ではなく、部分的に構造を共有するスペクトラムであることが分かっている。

この設計課題は、本リポジトリの複数Task（Task-N、Task-E2、Task-E4〜E13）にわたって段階的に検討されてきたが、**一貫して「設計Task」として実装が禁止されており**、Task-E13完了時点でも未実装のままであった。その後、本セッション内で発生したコンテナ再プロビジョニングによるデータ消失により、これらの設計文書はファイルシステム上から失われたが、Task-E15の調査により、本セッションの生の会話ログ（Write tool呼び出しパラメータ）からTask-E12・Task-E13の全成果物がverbatim（原文のまま）復旧された。本ADRは、この復旧された設計を正式なADRとして固定するものである。

## 2. 問題（Problem Statement）

1. Block単位の構造（C-MASS/Category D双方の基盤となる行の分類）を扱う型が、現行の`FieldExtractionResult`（[ADR-0038](0038-field-extractor-produces-field-extraction-result.md)、`records`/`candidates`/`confidence`の3フィールド）に存在しない。
2. C-MASSとCategory Dをどう責務分離して処理するか（単一Resolverか、分離したResolverか）が未確定である。
3. 同一Blockが両者の候補になりうる重複ケース（39.2%）を、安全に（誤対応付けを不可逆に生成せずに）扱う方式が未確定である。
4. 同一Section内にself_containedブロックとfragmentブロックが混在するHybrid Sectionを、Section単位の二値分類に落とし込むと構造的な誤りを生む。

## 3. 復旧された証拠（Recovered Evidence）

本ADRの設計根拠は、以下Task-E15の復旧資料に基づく。証拠強度の詳細な分類は、Task-E16成果物`provenance_and_evidence.md`（`/tmp/taskE16/`配下、リポジトリ外のTask作業ディレクトリのため本ADRからは直接参照できない）に整理した。恒久的な参照は本ADR本文の記述そのものとする。

- **【Confirmed from recovered design evidence・HIGH】** Task-E13の12成果物（Integration-Option A〜E比較、責務境界定義、C-MASS/Category D相互作用の5区分、Hybrid Section設計）。会話ログのWrite tool呼び出しからverbatim復旧。
- **【Confirmed from recovered design evidence・HIGH】** Task-E12の12成果物（whitespace-collapse発見）。同上。
- **【Confirmed from recovered design evidence・MEDIUM】** Task-E5〜E7の設計内容（BlockKind 4分類、AMBIGUOUS非採用、Rule E式、FieldExtractionResult.blocks非永続方式）。圧縮summary経由の間接証拠であり、原文書のverbatim復旧ではない。
- **【Unverified / excluded evidence】** `2023/0313a.pdf sec9`という具体的組み合わせ。Task-E15が網羅的に調査したが出典を確認できなかった。**本ADRの設計根拠・実証根拠として使用しない。**

## 4. 決定（Decision）

**Integration-Option A（共通Block分類基盤＋CMassResolver/CategoryDResolver分離）を、正式な基本設計として採用する。** 39.2%重複のうち安全に一意化できないケースに限り、Integration-Option C（複数候補保持）を部分適用する。

## 5. アーキテクチャ（Architecture）

Field Extractor段階の内部を、以下6層に分割する。**この分割は[ADR-0011](0011-fixed-core-pipeline.md)が固定する6段階パイプラインの段階構成・名称を変更するものではない。** すべてField Extractor（既存の1段階）の内部設計に閉じる。

```
Layer 1 Extraction        — 変更なし（Option A実装済み、layout/detector.py、Task-E10/E11）
Layer 2 Line Features     — 既存FieldExtractorの拡張（column_count/rank_token/name_tail/action_pattern/completeness）
Layer 3 Block Classification — BlockKind 4分類（新規）
Layer 4 Section Aggregation  — FieldExtractionResult.blocks（新規、非永続）、Hybrid保持
Layer 5 Resolver          — CategoryDResolver / CMassResolver（新規、分離）
Layer 6 RawRecord生成     — 既存契約のまま（変更なし）
```

## 6. Block分類（Block Classification）

```python
BlockKind = Literal["self_contained", "post_only_fragment", "name_only_fragment", "other"]
```

- `self_contained`: 部署+階級+氏名が1行に揃った完結ブロック。
- `post_only_fragment`: 部署+階級のみの断片ブロック。
- `name_only_fragment`: 氏名のみ（または氏名+誤結合テキスト）の断片ブロック。
- `other`: 上記に該当しないもの。

**AMBIGUOUSを5番目のBlockKindとして追加しない。** 曖昧な判定は、単一のconfidence値ではなく`BlockEvidence`（構造化された判定根拠）で表現し、必要に応じてSection-level・Resolver-levelの複数候補保持（後述）で扱う。AMBIGUOUS非採用の詳細な論拠そのものは、Task-E15の調査でも原文書レベルでは復旧できておらず、**この4分類自体が復旧された設計の到達点**として扱う。

`BlockEvidence`は、`has_paren`・`has_rank_token`・`has_name_tail`・`prefix_length`・`column_count`という判定根拠フィールドから構成される（Task-E6/E7設計、MEDIUM confidence — フィールド名は圧縮summaryにverbatim記載されているが、各フィールドの詳細な算出ロジックは未復旧）。

## 7. CMassResolverの責務

| 項目 | 内容 |
|---|---|
| 入力 | `post_only_fragment`/`name_only_fragment` block（N:Mブロック分離構造） |
| 出力 | 統合済みレコード候補、または人手レビューへのフラグ付き候補 |
| 判定ロジック | Rule E（Task-E5起源、後述）による検出結果を前提に、ブロック内の断片行を対応付ける。対応付けの確信度が低い場合は「解決しない」選択肢を持つ |
| 判定閾値 | **未確定**（Task-E13完了時点で既に未確定のまま。実装Task側での実データ検証が前提条件） |

## 8. CategoryDResolverの責務

| 項目 | 内容 |
|---|---|
| 入力 | `self_contained` block内の、隣接する1:1 action↔data行ペア |
| 出力 | 1 data行 → 1 RawRecord候補 |
| 判定ロジック | action行は破棄、data行は単体で完結という既存Category D是正ロジック（Task-L起源の`taskL_mapping_formal_patch.yaml`を踏襲するか別途新規設計するかは未確定、Task-L本体は本ADR時点で復旧できていない） |

## 9. Hybrid Sectionの扱い

同一Section内に`self_contained` blockと`post_only_fragment`/`name_only_fragment` blockが混在するSection（Task-E4実証、34対象Section中6件=17.6%、MEDIUM confidence）を、**Section単位の二値分類（「このSectionはC-MASSかCategory Dか」という単一フラグ）に還元しない。** Section Aggregation（Layer 4）はBlock集合をそのまま`FieldExtractionResult.blocks`として保持し、集約のみを行う。解決（どのResolverがどう処理するか）はLayer 5に委譲する。同一Section内で異なるResolverが異なるBlockに適用されることを、設計上正常な状態として扱う。

## 10. 複数候補保持（Multiple-candidate handling）

39.2%重複のうち、以下の区分4・区分5に該当するケースに限り、CMassResolver候補とCategoryDResolver候補の**両方**を生成し、後段（将来のReview層、または人間判断）に委ねる（Integration-Option Cの部分適用）。

- **区分4**: 両方のresolverが関与する可能性があるもの（ブロック分離構造の中に一見完全な形の行が混在する。代表例`2022/0801a.pdf sec20`、HIGH confidence — Task-E13 verbatim復旧）。
- **区分5**: 現時点では安全に自動分類できないもの（Task-E2が指摘した254 Section、未個別検証）。

区分1（同じ構造を共有しているだけ）・区分2（C-MASSとして処理すべき）・区分3（Category Dとして処理すべき）は、単一Resolverへの通常の振り分けで扱う。**重複率をゼロにすることを目標としない。** 区分1・4は共通のBlock Classification基盤を採用する限り原理的にゼロにならず、無理に判定基準を狭めると区分2/3の見逃し（false negative）を生む。

後段（複数候補をどう最終的に一意化するか）の主体（自動選択ロジックかHuman Review Queueか）は**未確定**であり、実装Taskでの判断事項とする。

## 11. 既存RawRecord / FieldExtractionResultとの関係

- `RawRecord`（`section_ref`/`layout_id`/`record_index`/`raw_fields`/`extracted_at`）: **スキーマ変更なし。** Resolverが生成した候補を、既存契約にそのまま落とし込む。
- `FieldExtractionResult`（[ADR-0038](0038-field-extractor-produces-field-extraction-result.md)）: `records`/`candidates`/`confidence`の既存3フィールドは変更しない。**`blocks: tuple[Block, ...] = ()`という非永続フィールドを追加する。** これはADR-0038の決定を覆すものではなく、既存の`.candidates`（JobRunnerから一度も参照されない評価時中間表現、という既存の前例パターン）と同様の追加的拡張である。

## 12. 永続化方針（Persistence Policy）

`Block`/`BlockKind`/`BlockEvidence`/Resolver候補は、**すべて非永続。** DBには一切保存しない。既存の`FieldExtractionResult.candidates`が確立した「評価時のみ存在し、JobRunnerが消費しない中間表現」というパターンをそのまま踏襲する。

## 13. DB影響

**なし。** マイグレーション不要。

## 14. Knowledge影響

**なし。** 本設計はKnowledge（`knowledge/`）データに依存しない。Category D是正ロジック（Task-L起源）が将来的にKnowledgeへ配置される可能性はあるが、それ自体は本ADRの対象外であり、別途ADRを要する。

## 15. LayoutDetector / FieldExtractorとの関係

- **LayoutDetector**: Option A（2段階抽出方式、[layout/detector.py]、Task-E10/E11実装済み）は**無変更**。本ADRの設計はField Extractor段階の内部にのみ関わる。
- **FieldExtractor**: 既存の`_lines`/`_split_columns`/`_evaluate_line`/`_build_records`/`_COLUMN_SPLIT_PATTERN`（`\s{2,}`）は**無変更のまま、追加関数として**Layer 2〜Layer 6を実装する（Task-E7設計の踏襲）。

## 16. 検討した代替案（Rejected Alternatives）

### Integration-Option B: 単一Section resolverでC-MASS/Category Dを統合判定 — 却下

単一の`SectionResolver`がBlock Classification出力を受け取り、内部でC-MASS的かCategory D的かを判定しつつ解決まで行う（Resolverを分離しない）。**却下理由**: 検出基盤共有・解決ロジック分離という責務分離要件に反する。誤対応付けリスクが中〜高、片方の誤判定がもう片方の解決結果に波及しやすい。説明可能性が中〜低に低下し、将来のresolver追加のたびに巨大な単一Resolverを変更する必要が生じる。

### Integration-Option D: 既存Category Dロジックを維持し、C-MASSのみ追加 — 却下

Category Dの解決ロジックをそのまま維持し、C-MASS対応のみを新規Block基盤で追加する（Category D側はBlock Classificationを経由しない）。**却下理由**: `2022/0801a.pdf sec20`のような、C-MASS的ブロック分離構造の中に一見完全なcol3/col4行が存在するケースを、既存Category Dロジック（列数ベース）が誤って「安全」と判定してしまうリスクが残る。列数のみでの分類は安全に成立しないというTask-N/Task-E2の既存結論と矛盾する。

### Integration-Option Cの全面採用（全Blockに複数候補付与） — 部分採用にとどめる

Integration-Option Cを39.2%重複ケース（区分4/5）に限らず全Blockに適用する案も検討したが、後段の選択ロジック主体が未確定であることに加え、区分1〜3（安全に一意化できるケース）にまで複数候補を強制すると、実装・レビューの複雑性が不必要に増大するため、**部分適用にとどめる。**

## 17. 既知の限界（Known Limitations）

1. CMassResolver/CategoryDResolverの具体的な判定閾値は未確定（Task-E13完了時点から一貫して未確定のまま）。
2. Rule E（後述）の詳細仕様（99-section ground truthの構築方法等）はTask-E5原文書が復旧できていないため未確定。
3. `2023/0313a.pdf sec9`は出典不明として設計根拠から除外した。実PDFと出典が将来確認できた場合のみ、別途known caseとして再評価可能とする。

## 18. スコープ外の課題（Out-of-scope Issues）

以下は本ADRの対象外とし、別Taskで扱う。

- **whitespace-collapse問題**（Task-E12発見）: layout mode抽出時に列間空白が縮小し、FieldExtractorの`\s{2,}`閾値による列分割が成立しなくなる現象。Category D/C-MASSとは独立したメカニズムであり、本ADRの中心設計に統合しない。
- **232 PDF（14.1%）のLayout confidence gap**（Task-E14発見）: LayoutDetectorがlayout_idを確信度不足でNoneと判定し、SectionParserが0件のSectionを返す問題。pipeline上流の独立問題。
- **11 PDFのCID font encoding crash**（Task-E14発見、`LookupError: unknown encoding: /90msp-RKSJ-H`）: pypdf側の制約。

## 19. 証拠強度・出典分類（Evidence Strength / Provenance Classification）

詳細は本Task成果物`evidence_status_matrix.csv`を参照。要旨: Task-E12・E13由来の設計はHIGH（verbatim復旧）、Task-E5〜E7由来の設計はMEDIUM（圧縮summary経由）、`2023/0313a.pdf sec9`はUNVERIFIED（設計根拠として不使用）。

## 20. 将来の実装要求（Future Implementation Requirements）

詳細は本Task成果物`implementation_requirements.md`を参照。要旨: `extractors/extractor.py`への追加関数実装、`models/extraction.py`への`Block`/`BlockKind`/`BlockEvidence`型追加・`FieldExtractionResult.blocks`フィールド追加、新規Resolverモジュール、対応するテスト。**いずれも本ADR確定時点では未着手。**

## 21. 結果（トレードオフ、Consequences）

**得られるもの**: C-MASSとCategory Dを、単一の複雑なロジックに混在させず、共通基盤（Block Classification）と分離された解決ロジック（Resolver）に整理できる。誤対応付けリスクを最小化し（複数候補保持）、Hybrid Sectionを構造的に正しく表現できる。既存の`RawRecord`/`NormalizedRecord`/`CandidateRecord`/DB/Knowledgeへの影響がない。

**失うもの・将来への影響**: 判定閾値・後段の候補選択主体が未確定のまま設計を固定するため、実装Task側で追加の実データ検証（1643 PDF corpusを用いた閾値決定）が前提条件として残る。複数候補保持を選んだBlockについては、最終的な一意化のタイミング・主体を別途設計する必要がある。

## 関連ADR

- [ADR-0011](0011-fixed-core-pipeline.md) — 本ADRはこの6段階パイプライン構成を変更しない。Field Extractor段階内部の設計としてのみ位置づける。
- [ADR-0038](0038-field-extractor-produces-field-extraction-result.md) — `FieldExtractionResult`への`.blocks`フィールド追加は、この既存決定（records/candidates/confidence）を変更せず拡張するものである。
