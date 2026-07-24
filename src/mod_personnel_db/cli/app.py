"""argparseベースのCLIエントリポイント。

`CLI → Composition Root（bootstrap.py） → JobRunner → Pipeline`という
呼び出し方向のみを守る。本モジュールはコマンドライン引数の解析と
`commands.py`への委譲のみを行い、`repositories/sqlite/`・`knowledge/`・
`learning/`・`review/`・`export/`のいずれも直接importしない。標準ライブラリ
の`argparse`以外のCLIライブラリは導入しない。
"""

import argparse
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import cast

from mod_personnel_db.cli.bootstrap import CompositionSettings, build_settings
from mod_personnel_db.cli.commands import (
    VersionInfo,
    export_all_command,
    export_person_command,
    export_since_command,
    fetch_stage_command,
    init_db_command,
    list_schedule_command,
    review_approve_command,
    review_list_command,
    review_reject_command,
    review_start_command,
    run_job_command,
    run_pending_command,
    run_workflow_command,
    schedule_now_command,
    version_command,
)
from mod_personnel_db.cli.exceptions import CliCommandError
from mod_personnel_db.models import (
    ExportFormat,
    GoldRecord,
    JobId,
    LearningRecord,
    LearningRecordId,
    PdfId,
)
from mod_personnel_db.services import RUN_PENDING_JOB_TYPE, WorkflowResult

_EXPORT_FORMATS = ("csv", "parquet", "json")
_SCHEDULER_JOB_TYPES = (RUN_PENDING_JOB_TYPE,)

COMMANDS = (
    "init-db",
    "run-pending",
    "run-job",
    "version",
    "review",
    "export",
    "fetch-stage",
    "run-workflow",
    "schedule-now",
    "list-schedule",
    "help",
)


def build_parser() -> argparse.ArgumentParser:
    """11コマンド（init-db/run-pending/run-job/version/review/export/
    fetch-stage/run-workflow/schedule-now/list-schedule/help）を持つparserを
    構築する。
    """
    parser = argparse.ArgumentParser(prog="mod-personnel-db")
    parser.add_argument("--db-path", help="SQLiteデータベースファイルのパス")
    parser.add_argument("--knowledge-root", type=Path, help="knowledge/ディレクトリのパス")
    parser.add_argument("--layouts-root", type=Path, help="layouts/ディレクトリのパス")
    parser.add_argument("--parser-code-version", default="v1.0.0", help="解析コードのバージョン")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="DBスキーマを適用する")
    subparsers.add_parser("run-pending", help="未処理PDFを一括処理する")
    run_job_parser = subparsers.add_parser("run-job", help="指定したPDFのみを処理する")
    run_job_parser.add_argument("pdf_id", type=int, help="対象PdfRecordのID")
    subparsers.add_parser("version", help="ParserVersion/KnowledgeSnapshotを表示する")
    _add_review_subparser(subparsers)
    _add_export_subparser(subparsers)
    _add_fetch_stage_subparser(subparsers)
    _add_run_workflow_subparser(subparsers)
    _add_schedule_now_subparser(subparsers)
    subparsers.add_parser(
        "list-schedule", help="登録済み周期実行対象の次回実行予定を表示する（Scheduler経由）"
    )
    subparsers.add_parser("help", help="利用可能コマンド一覧を表示する")
    return parser


def _add_schedule_now_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    schedule_now_parser = subparsers.add_parser(
        "schedule-now", help="指定したjob_typeを即座に実行する（Scheduler経由）"
    )
    schedule_now_parser.add_argument(
        "job_type", choices=_SCHEDULER_JOB_TYPES, help="即座に実行するjob_type"
    )


def _add_fetch_stage_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    fetch_stage_parser = subparsers.add_parser(
        "fetch-stage", help="PDFをURLから取得し保存する（JobOrchestrator経由）"
    )
    fetch_stage_parser.add_argument("url", help="取得元URL")
    fetch_stage_parser.add_argument("destination_path", help="保存先ファイルパス")
    fetch_stage_parser.add_argument("published_date", help="発令日（ISO8601形式、YYYY-MM-DD）")


def _add_run_workflow_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    run_workflow_parser = subparsers.add_parser(
        "run-workflow",
        help="Pipeline→Review→Exportを一括実行する（JobOrchestrator経由。Fetchフェーズは対象外）",
    )
    run_workflow_parser.add_argument(
        "export_format", choices=_EXPORT_FORMATS, help="エクスポート形式"
    )
    run_workflow_parser.add_argument("export_destination", help="エクスポート先ファイルパス")
    run_workflow_parser.add_argument(
        "--remote-path", default=None, help="指定時はFTPでこのリモートパスへアップロードする"
    )


def _add_review_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    review_parser = subparsers.add_parser("review", help="Learning Datasetのレビューを行う")
    review_subparsers = review_parser.add_subparsers(dest="review_action", required=True)
    review_subparsers.add_parser("list", help="レビュー待ちのLearningRecord一覧を表示する")
    for action, help_text in (
        ("start", "レビューに着手する（open→in_review）"),
        ("approve", "レビューを承認する（in_review→reflected）"),
        ("reject", "レビューを却下する（in_review→wontfix）"),
    ):
        action_parser = review_subparsers.add_parser(action, help=help_text)
        action_parser.add_argument("record_id", type=int, help="対象LearningRecordのID")


def _add_export_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    export_parser = subparsers.add_parser("export", help="Gold Databaseを出力する")
    export_subparsers = export_parser.add_subparsers(dest="export_action", required=True)
    export_subparsers.add_parser("all", help="現在有効なGold Record全件を出力する")
    person_parser = export_subparsers.add_parser("person", help="指定した人物の履歴を出力する")
    person_parser.add_argument("person_key", help="対象person_key")
    since_parser = export_subparsers.add_parser("since", help="指定日時時点のGold Recordを出力する")
    since_parser.add_argument("since", help="ISO8601形式の日時")


def _require_settings(args: argparse.Namespace) -> CompositionSettings:
    missing = [
        name
        for name, value in (
            ("--db-path", args.db_path),
            ("--knowledge-root", args.knowledge_root),
            ("--layouts-root", args.layouts_root),
        )
        if value is None
    ]
    if missing:
        raise CliCommandError(f"missing required option(s): {', '.join(missing)}")
    return build_settings(
        db_path=args.db_path,
        knowledge_root=args.knowledge_root,
        layouts_root=args.layouts_root,
        parser_code_version=args.parser_code_version,
    )


def _format_version(info: VersionInfo) -> str:
    version = info.parser_version
    if version is None:
        version_line = "parser_version: (none recorded)"
    else:
        released_at = version.released_at.isoformat()
        version_line = f"parser_version: {version.code_version} (released_at={released_at})"
    return (
        f"{version_line}\n"
        f"knowledge_snapshot: checksum={info.knowledge_snapshot_checksum} "
        f"items={info.knowledge_item_count} as_of={info.knowledge_as_of.isoformat()}"
    )


def _format_learning_records(records: tuple[LearningRecord, ...]) -> str:
    if not records:
        return "0 pending review item(s)"
    lines = [
        f"{int(r.id)}: status={r.status} field={r.field_name} wrong_value={r.wrong_value!r}"
        for r in records
        if r.id is not None
    ]
    return "\n".join([f"{len(records)} pending review item(s):", *lines])


def _format_gold_records(records: tuple[GoldRecord, ...]) -> str:
    if not records:
        return "0 record(s)"
    lines = [
        f"{int(r.id)}: person_key={r.person_key} effective_date={r.effective_date.isoformat()}"
        for r in records
    ]
    return "\n".join([f"{len(records)} record(s):", *lines])


def _parse_since(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise CliCommandError(f"invalid ISO8601 datetime: {raw!r}") from exc


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise CliCommandError(f"invalid ISO8601 date: {raw!r}") from exc


def _format_fetch_stage_result(pdf_id: PdfId | None) -> str:
    if pdf_id is None:
        return "not staged: content_hash duplicates an existing pdf"
    return f"staged pdf: id={int(pdf_id)}"


def _format_workflow_result(result: WorkflowResult) -> str:
    fetched_ids = ", ".join(str(int(pdf_id)) for pdf_id in result.fetched_pdf_ids)
    fetch_errors = "; ".join(f"{error.url}: {error.message}" for error in result.fetch_errors)
    artifact = result.export_artifact
    fetched_line = f"fetched {len(result.fetched_pdf_ids)} pdf(s)"
    if fetched_ids:
        fetched_line += f" [{fetched_ids}]"
    export_line = (
        f"export: format={artifact.format} "
        f"record_count={artifact.record_count} sha256={artifact.sha256}"
    )
    lines = [
        fetched_line,
        f"processed {len(result.pipeline_results)} pipeline job(s)",
        f"pending_reviews: {result.pending_review_count}",
        export_line,
    ]
    if fetch_errors:
        lines.insert(1, f"fetch_errors: {fetch_errors}")
    return "\n".join(lines)


def _format_schedule_now_result(job_id: JobId) -> str:
    return f"triggered job: id={int(job_id)}"


def _format_list_schedule_result(upcoming: tuple[str, ...]) -> str:
    if not upcoming:
        return "0 upcoming schedule(s)"
    return "\n".join([f"{len(upcoming)} upcoming schedule(s):", *upcoming])


def _dispatch_review(args: argparse.Namespace, settings: CompositionSettings) -> str:
    action = args.review_action
    if action == "list":
        return _format_learning_records(review_list_command(settings))
    record_id = LearningRecordId(args.record_id)
    if action == "start":
        updated = review_start_command(settings, record_id)
    elif action == "approve":
        updated = review_approve_command(settings, record_id)
    elif action == "reject":
        updated = review_reject_command(settings, record_id)
    else:
        raise CliCommandError(f"unknown review action: {action}")
    return f"record {int(record_id)}: status={updated.status}"


def _dispatch_export(args: argparse.Namespace, settings: CompositionSettings) -> str:
    action = args.export_action
    if action == "all":
        records = export_all_command(settings)
    elif action == "person":
        records = export_person_command(settings, args.person_key)
    elif action == "since":
        records = export_since_command(settings, _parse_since(args.since))
    else:
        raise CliCommandError(f"unknown export action: {action}")
    return _format_gold_records(records)


def _dispatch_orchestrator(
    command: str, args: argparse.Namespace, settings: CompositionSettings
) -> str:
    if command == "fetch-stage":
        pdf_id = fetch_stage_command(
            settings, args.url, args.destination_path, _parse_date(args.published_date)
        )
        return _format_fetch_stage_result(pdf_id)
    export_format = cast(ExportFormat, args.export_format)
    workflow_result = run_workflow_command(
        settings, export_format, args.export_destination, remote_path=args.remote_path
    )
    return _format_workflow_result(workflow_result)


def _dispatch_scheduler(
    command: str, args: argparse.Namespace, settings: CompositionSettings
) -> str:
    if command == "schedule-now":
        job_id = schedule_now_command(settings, args.job_type)
        return _format_schedule_now_result(job_id)
    upcoming = list_schedule_command(settings)
    return _format_list_schedule_result(upcoming)


def _dispatch_service(command: str, args: argparse.Namespace, settings: CompositionSettings) -> str:
    """`JobOrchestrator`/`Scheduler`経由のコマンド4種をまとめて振り分ける
    （`_dispatch`の分岐数を規律上の上限内に収めるための集約、
    `_dispatch_orchestrator`/`_dispatch_scheduler`自体の責務は変更しない）。
    """
    if command in ("fetch-stage", "run-workflow"):
        return _dispatch_orchestrator(command, args, settings)
    return _dispatch_scheduler(command, args, settings)


def _dispatch(command: str, args: argparse.Namespace, settings: CompositionSettings) -> str:
    if command == "init-db":
        init_db_command(settings)
        message = "database initialized"
    elif command == "run-pending":
        results = run_pending_command(settings)
        message = f"processed {len(results)} pdf(s)"
    elif command == "run-job":
        result = run_job_command(settings, PdfId(args.pdf_id))
        message = f"job status: {result.job.status}"
    elif command == "version":
        message = _format_version(version_command(settings))
    elif command == "review":
        message = _dispatch_review(args, settings)
    elif command == "export":
        message = _dispatch_export(args, settings)
    elif command in ("fetch-stage", "run-workflow", "schedule-now", "list-schedule"):
        message = _dispatch_service(command, args, settings)
    else:
        raise CliCommandError(f"unknown command: {command}")
    return message


def main(argv: Sequence[str] | None = None) -> int:
    """CLIエントリポイント。戻り値0が成功、1がコマンドレベルのエラーを表す。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "help":
        print(parser.format_help())
        return 0
    try:
        settings = _require_settings(args)
        print(_dispatch(args.command, args, settings))
    except CliCommandError as exc:
        print(f"error: {exc}")
        return 1
    return 0


__all__ = ["COMMANDS", "build_parser", "main"]
