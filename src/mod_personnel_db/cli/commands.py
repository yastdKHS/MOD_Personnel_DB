"""必要最小限のCLIコマンド。`bootstrap.py`（合成ルート）が構築した`JobRunner`を呼び出す。

引数解析（argparse等）は本タスクの対象外とし、Composition Rootの配線を
確認できる最小限のコマンド関数のみを提供する。
"""

from mod_personnel_db.cli.bootstrap import CompositionSettings, build_job_runner
from mod_personnel_db.pipeline.result import PipelineResult


def run_pending_command(settings: CompositionSettings) -> tuple[PipelineResult, ...]:
    """`run_pending()`相当のCLIコマンド。JobRunnerの生成と呼び出しのみを行う。"""
    job_runner = build_job_runner(settings)
    return job_runner.run_pending()


__all__ = ["run_pending_command"]
