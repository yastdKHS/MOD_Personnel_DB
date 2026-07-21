"""argparseベースのCLIエントリポイント。

`CLI → Composition Root（bootstrap.py） → JobRunner → Pipeline`という
呼び出し方向のみを守る。本モジュールはコマンドライン引数の解析と
`commands.py`への委譲のみを行い、`repositories/sqlite/`・`knowledge/`・
`learning/`のいずれも直接importしない。標準ライブラリの`argparse`以外の
CLIライブラリは導入しない。
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.cli.commands import (
    VersionInfo,
    init_db_command,
    run_job_command,
    run_pending_command,
    version_command,
)
from mod_personnel_db.cli.exceptions import CliCommandError
from mod_personnel_db.models import PdfId

COMMANDS = ("init-db", "run-pending", "run-job", "version", "help")


def build_parser() -> argparse.ArgumentParser:
    """5コマンド（init-db/run-pending/run-job/version/help）を持つparserを構築する。"""
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
    subparsers.add_parser("help", help="利用可能コマンド一覧を表示する")
    return parser


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
    return CompositionSettings(
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


def _dispatch(command: str, args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    if command == "help":
        return parser.format_help()
    settings = _require_settings(args)
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
    raise CliCommandError(f"unknown command: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    """CLIエントリポイント。戻り値0が成功、1がコマンドレベルのエラーを表す。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        print(_dispatch(args.command, args, parser))
    except CliCommandError as exc:
        print(f"error: {exc}")
        return 1
    return 0


__all__ = ["COMMANDS", "build_parser", "main"]
