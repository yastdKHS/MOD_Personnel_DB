"""Phase7統合Step4（Task17-4）: `schedule-now`/`list-schedule`コマンドの単体テスト。

Task17-3で`services/scheduler.py`に実装された`Scheduler`（`DefaultScheduler`）を、
Task17-4で`cli/bootstrap.py`に追加された`build_scheduler()`経由でのみ取得し、
`cli/commands.py`が`Scheduler`Protocol経由でのみ呼び出すこと、
`cli/app.py`が新規サブコマンド（`schedule-now`/`list-schedule`）を正しく登録・
ディスパッチすることを検証する。`DefaultScheduler`は本テストファイルでも一切
直接インスタンス化しない（`commands._build_scheduler`をFakeで差し替えることで
代替する）。`JobOrchestrator`を`schedule_now_command`/`list_schedule_command`が
直接呼び出さないことも、Fake`Scheduler`の呼び出し記録で確認する。
"""

from dataclasses import dataclass, field

import pytest

from mod_personnel_db.cli import app, commands
from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.models import JobId
from mod_personnel_db.services import RUN_PENDING_JOB_TYPE, NoPendingJobError, UnknownJobTypeError


@dataclass
class _RecordingScheduler:
    """`Scheduler`Protocolを満たすFake実装。呼び出し引数を記録するのみで、
    実際の`JobOrchestrator`呼び出しは一切行わない。
    """

    trigger_now_calls: list[str] = field(default_factory=list)
    list_upcoming_calls: int = 0
    trigger_now_result: JobId | None = JobId(1)
    trigger_now_error: Exception | None = None
    upcoming: tuple[str, ...] = ()

    def trigger_now(self, job_type: str) -> JobId:
        self.trigger_now_calls.append(job_type)
        if self.trigger_now_error is not None:
            raise self.trigger_now_error
        assert self.trigger_now_result is not None
        return self.trigger_now_result

    def list_upcoming(self) -> tuple[str, ...]:
        self.list_upcoming_calls += 1
        return self.upcoming


# --- 「Scheduler呼び出し」: Protocol経由のみで正しい引数が渡ることを確認 ---


def test_schedule_now_command_calls_scheduler_via_protocol(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_scheduler = _RecordingScheduler(trigger_now_result=JobId(7))
    monkeypatch.setattr(commands, "_build_scheduler", lambda _settings: fake_scheduler)

    result = commands.schedule_now_command(settings, RUN_PENDING_JOB_TYPE)

    assert result == JobId(7)
    assert fake_scheduler.trigger_now_calls == [RUN_PENDING_JOB_TYPE]


def test_schedule_now_command_propagates_no_pending_job_error(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_scheduler = _RecordingScheduler(trigger_now_error=NoPendingJobError("no pending job"))
    monkeypatch.setattr(commands, "_build_scheduler", lambda _settings: fake_scheduler)

    with pytest.raises(NoPendingJobError):
        commands.schedule_now_command(settings, RUN_PENDING_JOB_TYPE)


def test_schedule_now_command_propagates_unknown_job_type_error(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_scheduler = _RecordingScheduler(trigger_now_error=UnknownJobTypeError("unknown"))
    monkeypatch.setattr(commands, "_build_scheduler", lambda _settings: fake_scheduler)

    with pytest.raises(UnknownJobTypeError):
        commands.schedule_now_command(settings, "unknown-job-type")


def test_list_schedule_command_calls_scheduler_via_protocol(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_scheduler = _RecordingScheduler(
        upcoming=(f"{RUN_PENDING_JOB_TYPE} at 2026-01-01T00:00:00+00:00",)
    )
    monkeypatch.setattr(commands, "_build_scheduler", lambda _settings: fake_scheduler)

    result = commands.list_schedule_command(settings)

    assert result == fake_scheduler.upcoming
    assert fake_scheduler.list_upcoming_calls == 1


# --- 「CLI→bootstrap呼び出し」: _build_scheduler()がbootstrap.pyのBuilderのみを
# 期待した引数で呼び出すことを確認 ---


def test_build_scheduler_helper_delegates_to_bootstrap_build_scheduler(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel_orchestrator = object()
    monkeypatch.setattr(
        commands, "_build_job_orchestrator", lambda _settings: sentinel_orchestrator
    )
    captured: dict[str, object] = {}
    sentinel_scheduler = _RecordingScheduler()

    def fake_build_scheduler(orchestrator: object, schedules: object, clock: object) -> object:
        captured["orchestrator"] = orchestrator
        captured["schedules"] = schedules
        captured["clock"] = clock
        return sentinel_scheduler

    monkeypatch.setattr(commands, "build_scheduler", fake_build_scheduler)

    result = commands._build_scheduler(settings)

    assert result is sentinel_scheduler
    assert captured["orchestrator"] is sentinel_orchestrator
    assert captured["schedules"] == ()
    assert callable(captured["clock"])


# --- 「CLIコマンド登録」: app.COMMANDS・argparseサブパーサへの登録を確認 ---


def test_commands_tuple_includes_scheduler_subcommands() -> None:
    assert "schedule-now" in app.COMMANDS
    assert "list-schedule" in app.COMMANDS
    # 既存9コマンド + help を含め、後方互換のため既存コマンドが失われていないことを確認する。
    for existing in (
        "init-db",
        "run-pending",
        "run-job",
        "version",
        "review",
        "export",
        "fetch-stage",
        "run-workflow",
        "help",
    ):
        assert existing in app.COMMANDS


def test_parser_accepts_schedule_now_with_valid_job_type() -> None:
    parser = app.build_parser()
    args = parser.parse_args(
        [
            "--db-path",
            "x.sqlite3",
            "--knowledge-root",
            "knowledge",
            "--layouts-root",
            "layouts",
            "schedule-now",
            RUN_PENDING_JOB_TYPE,
        ]
    )
    assert args.command == "schedule-now"
    assert args.job_type == RUN_PENDING_JOB_TYPE


def test_parser_rejects_schedule_now_with_unknown_job_type() -> None:
    parser = app.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--db-path",
                "x.sqlite3",
                "--knowledge-root",
                "knowledge",
                "--layouts-root",
                "layouts",
                "schedule-now",
                "unknown-job-type",
            ]
        )


def test_parser_accepts_list_schedule() -> None:
    parser = app.build_parser()
    args = parser.parse_args(
        [
            "--db-path",
            "x.sqlite3",
            "--knowledge-root",
            "knowledge",
            "--layouts-root",
            "layouts",
            "list-schedule",
        ]
    )
    assert args.command == "list-schedule"


# --- app.main()経由のディスパッチ（Fakeへ差し替え） ---


def test_main_schedule_now_dispatches_and_formats_result(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_scheduler = _RecordingScheduler(trigger_now_result=JobId(42))
    monkeypatch.setattr(commands, "_build_scheduler", lambda _settings: fake_scheduler)

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "schedule-now",
            RUN_PENDING_JOB_TYPE,
        ]
    )

    assert exit_code == 0
    assert "triggered job: id=42" in capsys.readouterr().out
    assert fake_scheduler.trigger_now_calls == [RUN_PENDING_JOB_TYPE]


def test_main_list_schedule_dispatches_and_formats_empty_result(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_scheduler = _RecordingScheduler(upcoming=())
    monkeypatch.setattr(commands, "_build_scheduler", lambda _settings: fake_scheduler)

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "list-schedule",
        ]
    )

    assert exit_code == 0
    assert "0 upcoming schedule(s)" in capsys.readouterr().out
    assert fake_scheduler.list_upcoming_calls == 1


def test_main_list_schedule_dispatches_and_formats_nonempty_result(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_scheduler = _RecordingScheduler(
        upcoming=(f"{RUN_PENDING_JOB_TYPE} at 2026-01-01T00:00:00+00:00",)
    )
    monkeypatch.setattr(commands, "_build_scheduler", lambda _settings: fake_scheduler)

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "list-schedule",
        ]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "1 upcoming schedule(s):" in out
    assert f"{RUN_PENDING_JOB_TYPE} at 2026-01-01T00:00:00+00:00" in out


# --- 既存CLI回帰: schedule-now/list-schedule追加後も既存コマンドが変わらず動作する ---


def test_existing_version_command_unaffected_by_scheduler_additions(
    settings: CompositionSettings,
) -> None:
    info = commands.version_command(settings)
    assert info.knowledge_item_count == 0


def test_existing_fetch_stage_command_import_unaffected_by_scheduler_additions() -> None:
    assert callable(commands.fetch_stage_command)
    assert callable(commands.run_workflow_command)
