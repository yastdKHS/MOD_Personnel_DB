"""CLI全体のE2E統合テスト（Phase4 Task12-4）。

`app.main()`（CLIの公開エントリポイント）のみを駆動し、Composition Root
（`bootstrap.build_application()`/`build_job_runner()`）の生成からコマンド
終了までを、実際のSQLiteファイル（`tmp_path`）を用いてend-to-endで確認する。
`commands.build_application`/`build_job_runner`のmonkeypatchは一切行わない
（Task12-3までの単体テストとは異なり、Composition Root自体を実際に動かす）。
"""

import sqlite3

import pytest

from mod_personnel_db.cli import app
from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.models import LearningStatus

from ._fixtures import insert_gold_record, insert_learning_record
from .conftest import base_argv


def test_init_db_creates_database_schema(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = app.main([*base_argv(settings), "init-db"])

    assert exit_code == 0
    assert "initialized" in capsys.readouterr().out
    connection = sqlite3.connect(settings.db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        connection.close()
    assert {"pdfs", "jobs", "learning_dataset", "gold_records", "candidate_records"}.issubset(
        tables
    )


def test_run_pending_with_no_pending_pdfs_succeeds(
    initialized_settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = app.main([*base_argv(initialized_settings), "run-pending"])

    assert exit_code == 0
    assert "processed 0 pdf(s)" in capsys.readouterr().out


def test_review_list_shows_pending_item(
    initialized_settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record_id = insert_learning_record(initialized_settings)

    exit_code = app.main([*base_argv(initialized_settings), "review", "list"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 pending review item(s):" in output
    assert str(int(record_id)) in output


def test_review_start_transitions_to_in_review(
    initialized_settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record_id = insert_learning_record(initialized_settings)

    exit_code = app.main([*base_argv(initialized_settings), "review", "start", str(int(record_id))])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"record {int(record_id)}: status={LearningStatus.IN_REVIEW}" in output


def test_review_approve_transitions_to_reflected(
    initialized_settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record_id = insert_learning_record(initialized_settings)
    argv = base_argv(initialized_settings)
    assert app.main([*argv, "review", "start", str(int(record_id))]) == 0
    capsys.readouterr()

    exit_code = app.main([*argv, "review", "approve", str(int(record_id))])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"record {int(record_id)}: status={LearningStatus.REFLECTED}" in output


def test_review_reject_transitions_to_wontfix(
    initialized_settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record_id = insert_learning_record(initialized_settings)
    argv = base_argv(initialized_settings)
    assert app.main([*argv, "review", "start", str(int(record_id))]) == 0
    capsys.readouterr()

    exit_code = app.main([*argv, "review", "reject", str(int(record_id))])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"record {int(record_id)}: status={LearningStatus.WONTFIX}" in output


def test_export_all_lists_current_gold_records(
    initialized_settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record = insert_gold_record(initialized_settings, "person-1")

    exit_code = app.main([*base_argv(initialized_settings), "export", "all"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 record(s):" in output
    assert str(int(record.id)) in output
    assert "person-1" in output


def test_export_person_filters_by_person_key(
    initialized_settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    insert_gold_record(initialized_settings, "person-a")
    insert_gold_record(initialized_settings, "person-b")

    exit_code = app.main([*base_argv(initialized_settings), "export", "person", "person-a"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 record(s):" in output
    assert "person-a" in output
    assert "person-b" not in output


def test_export_since_parses_iso8601_and_returns_records(
    initialized_settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    insert_gold_record(initialized_settings, "person-1")

    exit_code = app.main(
        [*base_argv(initialized_settings), "export", "since", "2099-01-01T00:00:00+00:00"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 record(s):" in output
    assert "person-1" in output
