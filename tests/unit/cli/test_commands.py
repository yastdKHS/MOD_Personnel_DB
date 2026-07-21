import pytest

from mod_personnel_db.cli import commands
from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.pipeline.job_runner import JobRunner
from mod_personnel_db.pipeline.result import PipelineResult


class _StubJobRunner:
    """`run_pending_command`がJobRunner.run_pending()を呼ぶことを確認するためのStub。"""

    def __init__(self) -> None:
        self.run_pending_called = False

    def run_pending(self) -> tuple[PipelineResult, ...]:
        self.run_pending_called = True
        return ()


def test_run_pending_command_invokes_job_runner_run_pending(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    stub = _StubJobRunner()

    def fake_build_job_runner(settings_arg: CompositionSettings) -> JobRunner:
        del settings_arg
        return stub  # type: ignore[return-value]

    monkeypatch.setattr(commands, "build_job_runner", fake_build_job_runner)

    result = commands.run_pending_command(settings)

    assert stub.run_pending_called is True
    assert result == ()


def test_run_pending_command_end_to_end_with_no_pending_pdfs(
    settings: CompositionSettings,
) -> None:
    result = commands.run_pending_command(settings)

    assert result == ()
