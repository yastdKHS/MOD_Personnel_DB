"""argparseベースのCLIエントリポイント。

`CLI → Composition Root（bootstrap.py） → JobRunner → Pipeline`という
呼び出し方向のみを守る。本モジュールはコマンドライン引数の解析と
`commands.py`への委譲のみを行い、`repositories/sqlite/`・`knowledge/`・
`learning/`・`review/`・`export/`のいずれも直接importしない。標準ライブラリ
の`argparse`以外のCLIライブラリは導入しない。
"""

import argparse
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from mod_personnel_db.cli.bootstrap import CompositionSettings, build_settings
from mod_personnel_db.cli.commands import (
    VersionInfo,
    export_all_command,
    export_person_command,
    export_since_command,
    init_db_command,
    review_approve_command,
    review_list_command,
    review_reject_command,
    review_start_command,
    run_job_command,
    run_pending_command,
    version_command,
)
from mod_personnel_db.cli.exceptions import CliCommandError
from mod_personnel_db.models import GoldRecord, LearningRecord, LearningRecordId, PdfId

COMMANDS = ("init-db", "run-pending", "run-job", "version", "review", "export", "help")


def build_parser() -> argparse.ArgumentParser:
    """7コマンド（init-db/run-pending/run-job/version/review/export/help）を持つparserを構築する。"""
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
    subparsers.add_parser("help", help="利用可能コマンド一覧を表示する")
    return parser


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


def _dispatch(command: str, args: argparse.Namespace, settings: CompositionSettings) -> str:
    if command == "init-db":
        init_db_command(settings)
        return "database initialized"
    if command == "run-pending":
        results = run_pending_command(settings)
        return f"processed {len(results)} pdf(s)"
    if command == "run-job":
        result = run_job_command(settings, PdfId(args.pdf_id))
        return f"job status: {result.job.status}"
    if command == "version":
        return _format_version(version_command(settings))
    if command == "review":
        return _dispatch_review(args, settings)
    if command == "export":
        return _dispatch_export(args, settings)
    raise CliCommandError(f"unknown command: {command}")


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
