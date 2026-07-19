"""パイプライン実行1回分の横断的な実行情報。docs/api/pipeline.md#pipelinecontext に対応する。"""

from dataclasses import dataclass
from datetime import datetime

from mod_personnel_db.models import JobId, ParserVersionId


@dataclass(frozen=True, slots=True)
class PipelineContext:
    """1回のパイプライン実行（1PDF分）につき1つ生成され、全Stage呼び出しに使い回される。

    Repositoryへの参照は含まない（各Stageがrepositoryにアクセスできてしまうことを防ぐため、
    docs/api/pipeline.md#pipelinecontext）。
    """

    job_id: JobId
    parser_version_id: ParserVersionId
    correlation_id: str
    started_at: datetime
