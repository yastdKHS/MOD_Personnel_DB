"""Pipeline Framework公開窓口。docs/api/pipeline.md に対応する（Phase2 Task3: 骨格のみ）。

中核パイプライン6段階（Document Analyzer→Layout Detector→Section Parser→
Field Extractor→Normalizer→Validator、ADR-0011）の各Stage実装はここには含まない。
"""

from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.events import PipelineEvent, PipelineEventType
from mod_personnel_db.pipeline.exceptions import PipelineException, PipelineFrameworkError
from mod_personnel_db.pipeline.factory import PipelineFactory
from mod_personnel_db.pipeline.metrics import PipelineMetrics
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.pipeline.runner import NamedStage, PipelineRunner
from mod_personnel_db.pipeline.stage import PipelineStage

# job_runnerはここでは再エクスポートしない。中核パイプライン6段階
# （document/〜validators/）が本モジュールからPipelineContextをimportするため
# （各Stageの実装）、job_runner（6段階をimportする）を本ファイルで読み込むと
# 循環参照になる。JobRunnerは`mod_personnel_db.pipeline.job_runner`から直接importする。

__all__ = [
    "NamedStage",
    "PipelineBuilder",
    "PipelineContext",
    "PipelineEvent",
    "PipelineEventType",
    "PipelineException",
    "PipelineFactory",
    "PipelineFrameworkError",
    "PipelineMetrics",
    "PipelineResult",
    "PipelineRunner",
    "PipelineStage",
]
