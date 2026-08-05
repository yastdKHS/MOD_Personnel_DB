"""DB監査ツール（Task34 Step3）。

設計・監査SQLの根拠は docs/operations/db_audit.md を参照。

- Read Only: DB接続を `mode=ro` で開き、SQLite自体に書き込みを拒否させる。
- Repository（src/mod_personnel_db/repositories/）を経由せず、sqlite3標準
  ライブラリで監査SQL（SELECT/PRAGMAのみ）を直接実行する。
- 自動修復は行わない。異常検知時の手動修復手順は
  docs/operations/db_repair_procedures.md を参照。

使用例:
    python tools/db_audit.py
    python tools/db_audit.py --db-path DB/personnel.db --json
    python tools/db_audit.py --stale-running-hours 12

終了コード:
    0: 問題なし
    1: Warningのみ検出
    2: Errorを検出（またはDB接続失敗等の実行時エラー）
"""

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = "DB/personnel.db"
DEFAULT_STALE_RUNNING_HOURS = 24


@dataclass(frozen=True)
class AuditCheck:
    check_id: str
    name: str
    severity: str
    description: str
    sql: str


@dataclass(frozen=True)
class AuditResult:
    check: AuditCheck
    rows: list[dict[str, object]]


def build_checks(stale_running_hours: int) -> tuple[AuditCheck, ...]:
    return (
        AuditCheck(
            check_id="Q1",
            name="personnel_sections: 複数parsed存在（PS-1）",
            severity="error",
            description="同一(pdf_id, section_index)にstatus='parsed'が2件以上存在する"
            "（ADR-0047の不変条件違反）。",
            sql="""
                SELECT pdf_id, section_index, COUNT(*) AS parsed_count
                FROM personnel_sections
                WHERE status = 'parsed'
                GROUP BY pdf_id, section_index
                HAVING COUNT(*) > 1
            """,
        ),
        AuditCheck(
            check_id="Q2",
            name="personnel_sections: 新旧逆転（PS-2）",
            severity="warning",
            description="現在parsedな行より新しいparser_versionの行がsupersededのまま残っている。",
            sql="""
                SELECT s_old.id AS parsed_id, s_old.pdf_id, s_old.section_index,
                       pv_old.released_at AS parsed_released_at,
                       s_new.id AS superseded_id, pv_new.released_at AS superseded_released_at
                FROM personnel_sections s_old
                JOIN parser_versions pv_old ON pv_old.id = s_old.parser_version_id
                JOIN personnel_sections s_new
                    ON s_new.pdf_id = s_old.pdf_id
                   AND s_new.section_index = s_old.section_index
                   AND s_new.status = 'superseded'
                JOIN parser_versions pv_new ON pv_new.id = s_new.parser_version_id
                WHERE s_old.status = 'parsed'
                  AND pv_new.released_at > pv_old.released_at
            """,
        ),
        AuditCheck(
            check_id="Q3",
            name="personnel_sections: 孤立superseded（PS-3）",
            severity="error",
            description="supersededだが、同一グループに後継のparsed行が存在しない。",
            sql="""
                SELECT s.id, s.pdf_id, s.section_index, s.parser_version_id
                FROM personnel_sections s
                WHERE s.status = 'superseded'
                  AND NOT EXISTS (
                      SELECT 1 FROM personnel_sections p
                      WHERE p.pdf_id = s.pdf_id
                        AND p.section_index = s.section_index
                        AND p.status = 'parsed'
                  )
            """,
        ),
        AuditCheck(
            check_id="Q4",
            name="personnel_sections: FK整合性（PS-4/PS-5/PS-6）",
            severity="error",
            description="pdf_id/parser_version_id/layout_idの参照先が存在しない。",
            sql="""
                SELECT ps.id, ps.pdf_id, ps.parser_version_id, ps.layout_id
                FROM personnel_sections ps
                LEFT JOIN pdfs p ON p.id = ps.pdf_id
                LEFT JOIN parser_versions pv ON pv.id = ps.parser_version_id
                LEFT JOIN layouts l ON l.id = ps.layout_id
                WHERE p.id IS NULL OR pv.id IS NULL OR l.id IS NULL
            """,
        ),
        AuditCheck(
            check_id="Q5",
            name="candidate_records: section_id存在確認（CR-1）",
            severity="error",
            description="personnel_section_idの参照先が存在しない。",
            sql="""
                SELECT cr.id, cr.personnel_section_id
                FROM candidate_records cr
                LEFT JOIN personnel_sections ps ON ps.id = cr.personnel_section_id
                WHERE ps.id IS NULL
            """,
        ),
        AuditCheck(
            check_id="Q6",
            name="candidate_records: pending取り残され（CR-2）",
            severity="warning",
            description="親personnel_sectionsがsupersededなのに、"
            "validation_status='pending'のまま残っている。",
            sql="""
                SELECT cr.id, cr.personnel_section_id, cr.validation_status,
                       ps.status AS section_status
                FROM candidate_records cr
                JOIN personnel_sections ps ON ps.id = cr.personnel_section_id
                WHERE cr.validation_status = 'pending'
                  AND ps.status = 'superseded'
            """,
        ),
        AuditCheck(
            check_id="Q7",
            name="candidate_records: lineage不整合（CR-3）",
            severity="error",
            description="子レコードのparser_version_idが親Sectionのものと一致しない。",
            sql="""
                SELECT cr.id, cr.parser_version_id AS record_version,
                       ps.parser_version_id AS section_version
                FROM candidate_records cr
                JOIN personnel_sections ps ON ps.id = cr.personnel_section_id
                WHERE cr.parser_version_id != ps.parser_version_id
            """,
        ),
        AuditCheck(
            check_id="Q8",
            name="jobs: dangling running job（J-1）",
            severity="warning",
            description=f"status='running'のまま{stale_running_hours}時間以上経過している。",
            sql=f"""
                SELECT id, job_type, pdf_id, started_at
                FROM jobs
                WHERE status = 'running'
                  AND started_at < STRFTIME(
                      '%Y-%m-%dT%H:%M:%SZ', 'now', '-{stale_running_hours} hours'
                  )
            """,
        ),
        AuditCheck(
            check_id="Q9",
            name="jobs: status/finished_at矛盾（J-2）",
            severity="error",
            description="statusとfinished_atの対応関係が矛盾している。",
            sql="""
                SELECT id, status, finished_at
                FROM jobs
                WHERE (status = 'running' AND finished_at IS NOT NULL)
                   OR (status IN ('succeeded', 'failed') AND finished_at IS NULL)
            """,
        ),
        AuditCheck(
            check_id="Q10",
            name="jobs: FK整合性（J-3）",
            severity="error",
            description="pdf_id/parser_version_idの参照先が存在しない（非NULLの場合）。",
            sql="""
                SELECT j.id, j.pdf_id, j.parser_version_id
                FROM jobs j
                LEFT JOIN pdfs p ON p.id = j.pdf_id
                LEFT JOIN parser_versions pv ON pv.id = j.parser_version_id
                WHERE (j.pdf_id IS NOT NULL AND p.id IS NULL)
                   OR (j.parser_version_id IS NOT NULL AND pv.id IS NULL)
            """,
        ),
        AuditCheck(
            check_id="Q11",
            name="gold_records: is_current重複（O-2）",
            severity="error",
            description="同一(person_key, effective_date)にis_current=1が2件以上存在する。",
            sql="""
                SELECT person_key, effective_date, COUNT(*) AS current_count
                FROM gold_records
                WHERE is_current = 1
                GROUP BY person_key, effective_date
                HAVING COUNT(*) > 1
            """,
        ),
        AuditCheck(
            check_id="Q12",
            name="gold_records: superseded_by循環（O-3）",
            severity="error",
            description="superseded_byの自己参照チェーンが循環している。",
            sql="""
                WITH RECURSIVE chain(start_id, current_id, depth) AS (
                    SELECT id, superseded_by, 1
                    FROM gold_records
                    WHERE superseded_by IS NOT NULL
                    UNION ALL
                    SELECT chain.start_id, gr.superseded_by, chain.depth + 1
                    FROM chain
                    JOIN gold_records gr ON gr.id = chain.current_id
                    WHERE chain.current_id IS NOT NULL AND chain.depth < 1000
                )
                SELECT DISTINCT start_id
                FROM chain
                WHERE current_id = start_id
            """,
        ),
        AuditCheck(
            check_id="Q13",
            name="gold_records: superseded_by先が存在しない（O-4）",
            severity="error",
            description="superseded_byが非NULLだが、参照先のgold_records.idが存在しない。",
            sql="""
                SELECT gr.id, gr.superseded_by
                FROM gold_records gr
                LEFT JOIN gold_records target ON target.id = gr.superseded_by
                WHERE gr.superseded_by IS NOT NULL
                  AND target.id IS NULL
            """,
        ),
        AuditCheck(
            check_id="Q14",
            name="review_changes: target_id整合性（O-5）",
            severity="error",
            description="target_table+target_idの多態的参照が、実際のテーブルに存在しない。",
            sql="""
                SELECT rc.id, rc.target_table, rc.target_id
                FROM review_changes rc
                WHERE (rc.target_table = 'candidate_records'
                       AND NOT EXISTS (
                           SELECT 1 FROM candidate_records cr WHERE cr.id = rc.target_id
                       ))
                   OR (rc.target_table = 'gold_records'
                       AND NOT EXISTS (
                           SELECT 1 FROM gold_records gr WHERE gr.id = rc.target_id
                       ))
            """,
        ),
        AuditCheck(
            check_id="Q15",
            name="全テーブル横断FK整合性（O-1）",
            severity="error",
            description="PRAGMA foreign_key_checkによる網羅的なFK違反検出。",
            sql="PRAGMA foreign_key_check",
        ),
    )


def open_readonly_connection(db_path: str) -> sqlite3.Connection:
    resolved = Path(db_path)
    if not resolved.exists():
        raise FileNotFoundError(f"DBファイルが見つかりません: {db_path}")
    uri = f"file:{resolved.resolve()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def run_check(conn: sqlite3.Connection, check: AuditCheck) -> list[dict[str, object]]:
    cursor = conn.execute(check.sql)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def run_audit(conn: sqlite3.Connection, checks: tuple[AuditCheck, ...]) -> list[AuditResult]:
    return [AuditResult(check=check, rows=run_check(conn, check)) for check in checks]


def determine_exit_code(results: list[AuditResult]) -> int:
    findings = [result for result in results if result.rows]
    if any(result.check.severity == "error" for result in findings):
        return 2
    if findings:
        return 1
    return 0


def format_text(results: list[AuditResult]) -> str:
    findings = [result for result in results if result.rows]
    lines = ["DB監査結果", "=" * 40]
    if not findings:
        lines.append("問題は検出されませんでした。")
        return "\n".join(lines)

    for result in findings:
        header = f"[{result.check.severity.upper()}] {result.check.check_id}: {result.check.name}"
        lines.append(header)
        lines.append(f"  {result.check.description}")
        lines.append(f"  該当件数: {len(result.rows)}")
        for row in result.rows[:10]:
            lines.append(f"    {row}")
        if len(result.rows) > 10:
            lines.append(f"    ...他 {len(result.rows) - 10} 件")
        lines.append("")

    error_count = sum(1 for result in findings if result.check.severity == "error")
    warning_count = sum(1 for result in findings if result.check.severity == "warning")
    lines.append(f"検出項目数: Error={error_count} Warning={warning_count}")
    return "\n".join(lines)


def format_json(results: list[AuditResult]) -> str:
    findings = [result for result in results if result.rows]
    payload = {
        "exit_code": determine_exit_code(results),
        "checks": [
            {
                "id": result.check.check_id,
                "name": result.check.name,
                "severity": result.check.severity,
                "count": len(result.rows),
                "rows": result.rows,
            }
            for result in findings
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MOD_Personnel_DB DB監査ツール（Read Only）")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="監査対象DBファイルのパス")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力する")
    parser.add_argument(
        "--stale-running-hours",
        type=int,
        default=DEFAULT_STALE_RUNNING_HOURS,
        help="jobs.status='running'を異常とみなす経過時間（時間単位、既定24）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    checks = build_checks(args.stale_running_hours)

    try:
        conn = open_readonly_connection(args.db_path)
    except (FileNotFoundError, sqlite3.OperationalError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2

    try:
        results = run_audit(conn, checks)
    finally:
        conn.close()

    print(format_json(results) if args.json else format_text(results))
    return determine_exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
